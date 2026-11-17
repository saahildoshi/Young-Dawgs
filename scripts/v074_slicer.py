"""Actual installed CuraEngine import/slice, on a clearly hypothetical generic bed."""
import os
import argparse
import subprocess
from pathlib import Path
from scripts.v070_protocol import read,write,sha
from scripts.v074_experiment import RUN,ASSETS,BASE,now

def run(name='P3_REFERENCE_PRINT_READY.stl',attempt=3):
    root=Path(r'C:\Program Files\Dremel DigiLab 3D Slicer')
    engine=root/'CuraEngine.exe';directory=BASE.parent.parent/f'fabrication_v074_slicer_attempt{attempt:03d}';directory.mkdir(exist_ok=False)
    settings={'machine_width':220,'machine_depth':220,'machine_height':250,'machine_center_is_zero':False,'machine_extruder_count':1,
        'machine_nozzle_size':.4,'material_diameter':1.75,'layer_height':.2,'layer_height_0':.2,
        'line_width':.45,'wall_line_width':.45,'wall_line_width_0':.45,'wall_line_width_x':.45,'skin_line_width':.45,'infill_line_width':.45,
        'wall_line_count':2,'top_layers':4,'bottom_layers':4,'infill_sparse_density':15,'infill_line_distance':3,
        'speed_print':40,'speed_wall':30,'speed_wall_0':25,'speed_wall_x':30,'speed_topbottom':30,'speed_infill':40,'speed_layer_0':20,'speed_travel':120,
        'material_print_temperature':200,'material_bed_temperature':60,
        'adhesion_type':'none','support_enable':False,'machine_start_gcode':'','machine_end_gcode':'',
        'meshfix_union_all':False,'meshfix_extensive_stitching':False,'center_object':True,'mesh_position_x':0,'mesh_position_y':0,'mesh_position_z':0}
    command=[str(engine),'slice','-m2','-j',str(root/'resources/definitions/fdmprinter.def.json')]
    for key,value in settings.items():command+=['-s',f'{key}={str(value).lower() if isinstance(value,bool) else value}']
    command+=['-e0']
    for key,value in {'material_diameter':1.75,'material_print_temperature':200,'material_print_temperature_layer_0':200,'machine_nozzle_size':.4}.items():command+=['-s',f'{key}={value}']
    command+=['-l',str(ASSETS/name),'-o',str(directory/'GENERIC_PREVIEW_NOT_FOR_PRINTING.gcode')]
    env={**os.environ,'CURA_ENGINE_SEARCH_PATH':str(root/'resources/definitions')+';'+str(root/'resources/extruders')}
    with (directory/'stdout.txt').open('w') as out,(directory/'stderr.txt').open('w') as err:
        r=subprocess.run(command,cwd=directory,env=env,stdout=out,stderr=err,timeout=600)
    record={'executed_utc':now(),'command':command,'returncode':r.returncode,'settings':settings,
        'engine_sha256':sha(engine),'input_STL':name,'input_STL_sha256':sha(ASSETS/name),'raw_directory':str(directory),
        'actual_printer_known':False,'profile':'Hypothetical generic220×220×250mm,0.4mm nozzle/0.2mm layer PLA; no physical print or printer compatibility claim'}
    previous=RUN/'fabrication/SLICER_EXECUTION.json'
    if previous.exists() and not (RUN/'fabrication/SLICER_EXECUTION_attempt001.json').exists():
        write(RUN/'fabrication/SLICER_EXECUTION_attempt001.json',read(previous))
    write(RUN/f'fabrication/SLICER_EXECUTION_attempt{attempt:03d}.json',record)
    write(RUN/f'fabrication/{Path(name).stem}_SLICER_EXECUTION.json',record)
    if name.startswith('P3_'):write(previous,record)
    print('SLICER',r.returncode,directory,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',default='P3_REFERENCE_PRINT_READY.stl');p.add_argument('--attempt',type=int,default=3);a=p.parse_args();run(a.name,a.attempt)
