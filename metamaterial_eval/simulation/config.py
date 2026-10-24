"""Explicit demonstration units and validated modeling choices."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class CompressionConfig:
    width: float = 10.24
    height: float = 10.24
    thickness: float = 1.0
    young_modulus: float = 1000.0
    poisson_ratio: float = 0.3
    mode: str = 'plane_stress'
    boundary_size: float = 0.01 / 3
    bulk_size: float = 0.04
    strains: tuple = (0.005, 0.01, 0.02)
    units: str = 'mm-N-MPa'

    def __post_init__(self):
        for key in ('width', 'height', 'thickness', 'young_modulus', 'boundary_size', 'bulk_size'):
            if not math.isfinite(getattr(self, key)) or getattr(self, key) <= 0:
                raise ValueError(f'{key} must be finite and positive')
        if not math.isfinite(self.poisson_ratio) or not -1 < self.poisson_ratio < 0.5:
            raise ValueError('Require -1 < nu < 0.5')
        if self.mode not in ('plane_stress', 'plane_strain') or self.units != 'mm-N-MPa':
            raise ValueError('Unsupported formulation or units')
        if self.mode == 'plane_strain' and self.thickness != 1:
            raise ValueError('Plane strain reports forces per unit depth; require thickness=1 mm')
        if self.bulk_size < self.boundary_size:
            raise ValueError('Bulk size must be at least boundary size')
        if not self.strains or any(not math.isfinite(s) or not 0 < s <= .02 for s in self.strains):
            raise ValueError('Only conservative 0 < strain <= .02 is prepared')
        if tuple(sorted(set(self.strains))) != tuple(self.strains):
            raise ValueError('Strains must increase strictly')

    def manifest(self):
        return {**asdict(self), 'dimensions': 'PROVISIONAL', 'material': 'ASSUMED_NOT_MEASURED',
                'time_axis': 'quasi_static_pseudo_time', 'large_deformation': True,
                'force_basis': 'total_N' if self.mode == 'plane_stress' else 'N_per_mm_depth'}
