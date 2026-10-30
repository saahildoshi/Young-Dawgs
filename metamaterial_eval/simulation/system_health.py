"""System-health safeguards; solver RSS is measured, never a health threshold."""
from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil


@dataclass(frozen=True)
class HealthPolicy:
    available_reserve_bytes: int = 6 * 1024**3
    reserve_seconds: float = 30
    critical_available_bytes: int = 1024**3
    critical_seconds: float = 3
    commit_fraction: float = .98
    commit_seconds: float = 15
    page_reads_per_second: float = 10000
    paging_seconds: float = 60
    no_output_growth_seconds: float = 90
    notification_seconds: float = 10


class HealthGuard:
    def __init__(self, policy):
        self.policy = policy
        self.since = {}

    def evaluate(self, sample):
        p = self.policy
        available = sample['available_RAM_bytes']
        commit = sample.get('commit_fraction')
        paging = sample.get('page_reads_per_second')
        signals = [
            ('SYSTEM_MEMORY_CRITICAL', available < p.critical_available_bytes, p.critical_seconds),
            ('SYSTEM_MEMORY_PRESSURE_SUSTAINED', available < p.available_reserve_bytes, p.reserve_seconds),
            ('SYSTEM_COMMIT_PRESSURE_SUSTAINED', commit is not None and commit >= p.commit_fraction
             and available < p.available_reserve_bytes, p.commit_seconds),
            ('WINDOWS_LOW_MEMORY_SUSTAINED', sample.get('windows_low_memory') is True
             and available < p.available_reserve_bytes, p.notification_seconds),
            ('SEVERE_PAGING_WITHOUT_OUTPUT_PROGRESS', paging is not None and paging >= p.page_reads_per_second
             and sample.get('seconds_without_output_growth', 0) >= p.no_output_growth_seconds, p.paging_seconds),
        ]
        for name, active, duration in signals:
            if not active:
                self.since.pop(name, None)
            else:
                self.since.setdefault(name, sample['elapsed_seconds'])
                if sample['elapsed_seconds'] - self.since[name] >= duration:
                    return name
        return None


class WindowsSignals:
    """Native commit, low-memory notification and system hard-fault I/O proxy.

    Page Reads/sec includes disk reads servicing hard faults, not exclusively
    pagefile reads. psutil's Windows swap sin/sout zeros are not paging evidence.
    Missing counters remain None with explicit availability diagnostics.
    """
    def __init__(self):
        self.query = None
        self.notification = None
        self.counters = {}
        self.errors = []
        if os.name != 'nt':
            self.errors.append('Windows native signals unavailable on this platform')
            return
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMemoryResourceNotification.argtypes = [ctypes.c_int]
        self.kernel.CreateMemoryResourceNotification.restype = wintypes.HANDLE
        self.kernel.QueryMemoryResourceNotification.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.notification = self.kernel.CreateMemoryResourceNotification(0)
        self.psapi = ctypes.WinDLL('psapi', use_last_error=True)
        class PerformanceInfo(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in
                ['CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable',
                 'SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize']] + [
                (n, wintypes.DWORD) for n in ['HandleCount','ProcessCount','ThreadCount']]
        self.performance_type = PerformanceInfo
        self.psapi.GetPerformanceInfo.argtypes = [ctypes.POINTER(PerformanceInfo), wintypes.DWORD]
        self.pdh = ctypes.WinDLL('pdh', use_last_error=True)
        self.pdh.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(wintypes.HANDLE)]
        self.pdh.PdhAddEnglishCounterW.argtypes = [wintypes.HANDLE,wintypes.LPCWSTR,ctypes.c_size_t,ctypes.POINTER(wintypes.HANDLE)]
        self.pdh.PdhCollectQueryData.argtypes = [wintypes.HANDLE]
        self.pdh.PdhGetFormattedCounterValue.argtypes = [wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p]
        self.pdh.PdhCloseQuery.argtypes = [wintypes.HANDLE]
        handle = wintypes.HANDLE()
        status = self.pdh.PdhOpenQueryW(None, 0, ctypes.byref(handle))
        if status:
            self.errors.append('PdhOpenQueryW failed: '+str(status))
            return
        self.query = handle
        for key, path in [('page_reads_per_second',r'\Memory\Page Reads/sec'),
                          ('pages_input_per_second',r'\Memory\Pages Input/sec'),
                          ('page_writes_per_second',r'\Memory\Page Writes/sec'),
                          ('pagefile_usage_percent',r'\Paging File(_Total)\% Usage')]:
            counter = wintypes.HANDLE()
            status = self.pdh.PdhAddEnglishCounterW(handle,path,0,ctypes.byref(counter))
            if not status:self.counters[key] = counter
            else:self.errors.append('Counter unavailable '+key+': '+str(status))
        self.pdh.PdhCollectQueryData(handle)

    def sample(self):
        result = dict.fromkeys(['commit_used_bytes','commit_limit_bytes','commit_fraction','windows_low_memory',
                               'page_reads_per_second','pages_input_per_second','page_writes_per_second','pagefile_usage_percent'])
        if os.name != 'nt':return result
        info = self.performance_type();info.cb = ctypes.sizeof(info)
        if self.psapi.GetPerformanceInfo(ctypes.byref(info),info.cb):
            result.update(commit_used_bytes=info.CommitTotal*info.PageSize,commit_limit_bytes=info.CommitLimit*info.PageSize,
                          commit_fraction=info.CommitTotal/info.CommitLimit if info.CommitLimit else None)
        if self.notification:
            low = wintypes.BOOL()
            if self.kernel.QueryMemoryResourceNotification(self.notification,ctypes.byref(low)):
                result['windows_low_memory'] = bool(low.value)
        if self.query:
            class CounterValue(ctypes.Structure):
                _fields_ = [('CStatus',wintypes.DWORD),('doubleValue',ctypes.c_double)]
            self.pdh.PdhCollectQueryData(self.query)
            for key, counter in self.counters.items():
                value = CounterValue()
                status = self.pdh.PdhGetFormattedCounterValue(counter,0x200,None,ctypes.byref(value))
                if not status and value.CStatus in [0,1]:result[key] = value.doubleValue
        return result

    def close(self):
        if self.query:self.pdh.PdhCloseQuery(self.query);self.query = None
        if self.notification:self.kernel.CloseHandle(self.notification);self.notification = None


class SystemSampler:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.native = WindowsSignals()
        self.previous_sizes = {}
        self.last_growth = 0

    def sample(self, elapsed, rss=None, tree=()):
        import psutil
        vm = psutil.virtual_memory()
        sizes = {}
        for path in self.directory.iterdir():
            try:
                if path.is_file():sizes[path.name] = path.stat().st_size
            except FileNotFoundError:pass
        if any(size > self.previous_sizes.get(name,0) for name,size in sizes.items()):self.last_growth = elapsed
        self.previous_sizes = sizes
        children = []
        for process in tree:
            try:children.append({'pid':process.pid,'name':process.name(),'status':process.status()})
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        return {'elapsed_seconds':elapsed,'tree_rss_bytes':rss,'physical_RAM_bytes':vm.total,
                'available_RAM_bytes':vm.available,'system_memory_percent':vm.percent,
                'disk_free_bytes':shutil.disk_usage(self.directory).free,
                'output_file_bytes':sizes,'seconds_without_output_growth':elapsed-self.last_growth,
                'owned_processes':children,**self.native.sample()}

    def close(self):self.native.close()
