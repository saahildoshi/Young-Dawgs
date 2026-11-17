"""Independent inspection of actual generic Cura G-code; never printer-ready code."""
import re
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import MultiLineString,Polygon
from shapely import affinity
import trimesh
from scripts.v070_protocol import read,write,sha
from scripts.v074_experiment import RUN,ASSETS,now


def parse(path):
    position={'X':0.,'Y':0.,'Z':0.,'E':0.};absolute=True;xyz_absolute=True
    layer=-1;kind='UNKNOWN';rows=[];filament=0.;debt=0.;times=[]
    for line in path.read_text().splitlines():
        if line.startswith(';LAYER:'):layer=int(line.split(':')[1])
        if line.startswith(';TYPE:'):kind=line.split(':',1)[1]
        if line.startswith(';TIME_ELAPSED:'):times.append(float(line.split(':')[1]))
        fields=line.split(';')[0].split()
        if not fields:continue
        command=fields[0]
        values={k:float(v) for k,v in re.findall(r'([XYZEF])([-+]?\d*\.?\d+)', ' '.join(fields[1:]))}
        if command=='M82':absolute=True
        elif command=='M83':absolute=False
        elif command=='G90':xyz_absolute=True
        elif command=='G91':xyz_absolute=False
        elif command=='G92':position.update({k:v for k,v in values.items() if k in position})
        elif command in ['G0','G1']:
            old=position.copy()
            for axis in ['X','Y','Z']:
                if axis in values:position[axis]=values[axis] if xyz_absolute else old[axis]+values[axis]
            de=0.
            if 'E' in values:
                de=values['E']-old['E'] if absolute else values['E']
                position['E']=values['E'] if absolute else old['E']+values['E']
            if de<0:debt-=de
            net=max(0.,de-debt)
            if de>0:debt=max(0.,debt-de)
            distance=np.hypot(position['X']-old['X'],position['Y']-old['Y'])
            if net>1e-8 and distance>1e-8:
                filament+=net
                rows.append({'layer':layer,'z':position['Z'],'type':kind,
                    'segment':[[old['X'],old['Y']],[position['X'],position['Y']]],'filament_mm':net})
    return rows,filament,times[-1] if times else None


def section(mesh,z):
    segments=trimesh.intersections.mesh_plane(mesh,[0,0,1],[0,0,z])
    return shapely.build_area(shapely.set_precision(MultiLineString(segments[:,:,:2].tolist()),1e-7))


def inspect(attempt,name,height):
    receipt=read(RUN/f'fabrication/SLICER_EXECUTION_attempt{attempt:03d}.json')
    assert receipt['returncode']==0 and receipt['input_STL_sha256']==sha(ASSETS/name)
    directory=Path(receipt['raw_directory']);gcode=directory/'GENERIC_PREVIEW_NOT_FOR_PRINTING.gcode'
    rows,filament,estimate=parse(gcode)
    segments=np.array([r['segment'] for r in rows]);bounds=np.stack([segments.min(axis=(0,1)),segments.max(axis=(0,1))])
    levels=sorted({r['layer'] for r in rows});zs=sorted({r['z'] for r in rows})
    mesh=trimesh.load_mesh(ASSETS/name,process=False);mesh.merge_vertices()
    # Cura centered the model on the hypothetical220mm bed.
    offset=110-(mesh.bounds[0,:2]+mesh.bounds[1,:2])/2
    geometry=affinity.translate(section(mesh,.1),xoff=offset[0],yoff=offset[1])
    first=MultiLineString([r['segment'] for r in rows if r['layer']==0])
    footprint=first.buffer(.2255,quad_segs=4)
    pieces=list(footprint.geoms) if footprint.geom_type=='MultiPolygon' else [footprint]
    significant=[p for p in pieces if p.area>.05]
    holes=[]
    for ring in geometry.interiors:
        hole=Polygon(ring);core=hole.buffer(-.5)
        holes.append({'area_mm2':hole.area,'core_area_mm2':core.area,
            'extrusion_overlap_core_mm2':footprint.intersection(core).area,
            'representative_center_clear':not footprint.covers(hole.representative_point())})
    warnings=(directory/'stderr.txt').read_text(errors='replace').splitlines()
    meaningful=[line for line in warnings if any(w in line.lower() for w in ['error','repair','stitch','non-manifold','not found','unknown setting']) and not line.startswith('[WARNING]  -s ')]
    checks={'native_slicer_exit0':True,'nonempty_extrusions':len(rows)>0,
        'all_layers_have_extrusions':levels==list(range(round(height/.2))),
        'layer_heights':bool(np.allclose(zs,np.arange(1,round(height/.2)+1)*.2,atol=1e-6)),
        'extrusion_paths_on_generic_bed':bool(bounds.min()>=0 and bounds.max()<=220),
        'no_support_paths':not any('SUPPORT' in r['type'] for r in rows),
        'positive_actual_extrusion':filament>0,'no_actual_mesh_repair_or_error_warning':not meaningful,
        'single_significant_first_layer_body':len(significant)==1,
        'original_through_pore_cores_unfilled':all(r['extrusion_overlap_core_mm2']<.001 for r in holes),
        'original_through_pore_centers_clear':all(r['representative_center_clear'] for r in holes)}
    result={'checked_utc':now(),'STL':name,'STL_sha256':sha(ASSETS/name),'Gcode_sha256':sha(gcode),
        'raw_Gcode_path':str(gcode),'engine_release_observation':'Installed Dremel CuraEngine bannerDEV; generated header1.2.3',
        'printer_profile':receipt['profile'],'actual_printer_known':False,'physically_printed':False,
        'layers_with_extrusion':levels,'z_mm':zs,'extruding_segment_count':len(rows),'extrusion_path_bounds_xy_mm':bounds.tolist(),
        'nominal_bead_width_mm':.45,'first_layer_buffer_width_mm':.451,
        'buffer_limitation':'Nominal footprint approximation with0.0005mm radial tolerance to join rounded G-code segments; no actual bead measurement',
        'first_layer_nominal_coverage_fraction':float(footprint.intersection(geometry).area/geometry.area),
        'first_layer_significant_connected_bodies':len(significant),'tiny_numerical_fragments':len(pieces)-len(significant),
        'through_pore_checks':holes,'filament_mm_from_actual_E_moves_retraction_compensated':filament,
        'engine_estimated_duration_s':estimate,'header_time_and_zero_filament_not_used':True,
        'actual_execution_warnings':meaningful,'checks':{k:bool(v) for k,v in checks.items()},'passed':bool(all(checks.values())),
        'compatibility_scope':'Actual installed engine accepted/sliced STL under hypothetical generic settings; user printer/material tolerances and physical reliability remain unverified'}
    write(RUN/'fabrication'/f'{Path(name).stem}_TOOLPATH_VALIDATION.json',result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    selected=[0,round(height/.2)-1] if name.startswith('POROUS') else [0,11,12,17]
    fig,axes=plt.subplots(1,len(selected),figsize=(5*len(selected),5),squeeze=False)
    for ax,layer in zip(axes[0],selected):
        use=[r for r in rows if r['layer']==layer]
        ax.add_collection(LineCollection([r['segment'] for r in use],colors='#347d89',linewidths=.45))
        ax.set(xlim=(20,200),ylim=(20,200),aspect='equal',xlabel='Generic bed X (mm)',ylabel='Generic bed Y (mm)',title=f'Actual layer{layer+1} · Z{use[0]["z"]:.1f}mm')
    fig.suptitle('Actual Cura toolpaths · hypothetical generic profile · no physical print / no printer-ready G-code')
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(ASSETS/f'{Path(name).stem}_SLICER_PREVIEW.png',dpi=160);plt.close(fig)
    target=ASSETS/('POROUS_METAMATERIAL_STL_VALIDATION.json' if name.startswith('POROUS') else 'STL_VALIDATION.json')
    validation=read(target);validation['actual_slicer_status']='GENERIC_ENGINE_AND_TOOLPATH_CHECKS_PASS' if result['passed'] else 'GENERIC_ENGINE_ACCEPTED_TOOLPATH_CHECKS_FAILED'
    validation['actual_slicer_validation']=result;write(target,validation)
    print(name,result['passed'],'layers',len(levels),'coverage',result['first_layer_nominal_coverage_fraction'],'failed',[k for k,v in checks.items() if not v],flush=True)


if __name__=='__main__':
    inspect(3,'P3_REFERENCE_PRINT_READY.stl',3.6)
    inspect(4,'POROUS_METAMATERIAL_PRINT_READY.stl',5.)
