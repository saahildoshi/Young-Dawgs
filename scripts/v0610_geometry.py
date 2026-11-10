"""Additional conservative continuous-arc penetration bound; never overrides native rejection."""
import argparse
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,MultiLineString
from shapely.ops import unary_union
from scripts.v0610_common import BASE,RUN,read,write_json,file_hash
from scripts.v068_track_b import mesh_and_plan
from scripts.v068_pair_common import face_owners

CHORD=1e-8
SPACING=5e-6
GUARD=1e-12
LIMIT=5e-5


def curve(vertices,t):
    return (t*(t-1)/2)[:,None]*vertices[0]+(t*(t+1)/2)[:,None]*vertices[1]+(1-t*t)[:,None]*vertices[2]


def sampled_curve(vertices,spacing=None,chord=CHORD):
    sag=float(np.linalg.norm(vertices[2]-(vertices[0]+vertices[1])/2))
    if spacing is None:n=max(1,int(np.ceil(np.sqrt(sag/chord))))
    else:
        velocities=np.array([-1.5*vertices[0]-.5*vertices[1]+2*vertices[2],.5*vertices[0]+1.5*vertices[1]-2*vertices[2]])
        speed=float(np.linalg.norm(velocities,axis=1).max());n=max(1,int(np.ceil(2*speed/spacing)))
    points=curve(vertices,np.linspace(-1,1,n+1))
    return points,2*speed/n if spacing else None,sag/(n*n)


def patch_topology(mesh,faces):
    owners=face_owners(mesh)[faces]-1
    nodes=np.unique(mesh.triangles[owners]);elements=np.flatnonzero(np.any(np.isin(mesh.triangles,nodes),axis=1))
    edges={}
    for tri in mesh.triangles[elements]:
        for face in [(tri[0],tri[1],tri[3]),(tri[1],tri[2],tri[4]),(tri[2],tri[0],tri[5])]:edges.setdefault(tuple(sorted(face[:2])),[]).append(face)
    physical={tuple(sorted(f[:2])) for f in mesh.boundary}
    boundary=[fs[0] for fs in edges.values() if len(fs)==1]
    return elements,np.array([f for f in boundary if tuple(sorted(f[:2])) in physical],dtype=int),np.array([f for f in boundary if tuple(sorted(f[:2])) not in physical],dtype=int)


def mapped_patch(mesh,xy,topology):
    elements,physical,cuts=topology;polys=[]
    for tri in mesh.triangles[elements]:
        points=[]
        for face in [(tri[0],tri[1],tri[3]),(tri[1],tri[2],tri[4]),(tri[2],tri[0],tri[5])]:points.extend(sampled_curve(xy[list(face)])[0][:-1])
        p=Polygon(points)
        if not p.is_valid:raise ValueError('Invalid diagnostic mapped triangle polygon')
        polys.append(p)
    solid=unary_union(polys)
    if not solid.is_valid:raise ValueError('Invalid diagnostic patch union')
    def lines(faces):return MultiLineString([sampled_curve(xy[f])[0] for f in faces]) if len(faces) else None
    return solid.buffer(CHORD+GUARD),lines(physical),lines(cuts)


def directional_bound(xy,source_faces,target_patch):
    solid,physical,cuts=target_patch;allpoints=[];gap=0;chord=0
    for face in source_faces:
        points,length,error=sampled_curve(xy[face],SPACING);allpoints.append(points);gap=max(gap,length);chord=max(chord,error)
    lines=MultiLineString(allpoints);points=np.vstack(allpoints)
    clearance=float(lines.distance(cuts))-chord-CHORD-GUARD if cuts is not None else None
    if clearance is not None and clearance<=gap/2+2*CHORD+GUARD:raise ValueError('Source arc too near artificial diagnostic patch cut for a continuous certificate')
    inside=shapely.contains_xy(solid,points[:,0],points[:,1]);depth=0.
    if np.any(inside):depth=float(shapely.distance(shapely.points(points[inside]),physical).max())
    return {'sampled_max_inside_depth_mm':depth,'maximum_source_arclength_between_samples_mm':gap,'target_boundary_chord_bound_mm':CHORD,'source_polyline_chord_bound_mm':chord,'cut_clearance_lower_bound_mm':clearance,'continuous_depth_upper_bound_mm':depth+gap/2+2*CHORD+GUARD,'samples':len(points)}


def qualify(source,branch=''):
    base=BASE/branch;run=RUN/branch;native_path=run/'track_B_progressive_compression'/(source+'_qualification.json');q=read(native_path)
    mesh,_,_,_=mesh_and_plan();p=read(run/'protocol/TRACK_B_LOCAL_PAIR_002.json');src=np.array(p['source_contact_faces_zero_based']);tgt=np.array(p['target_contact_faces_zero_based'])
    topology=[patch_topology(mesh,src),patch_topology(mesh,tgt)];post=base/(source+'_post1_all_v2');records=[];states=[];continuous=not q.get('failures')
    for i,state in enumerate(q['states'],1):
        raw=post/f'stage{i:03d}_displacements.csv';a=np.loadtxt(raw,delimiter=',',skiprows=1)
        if len(a)!=len(mesh.nodes) or not np.array_equal(a[:,0],np.arange(1,len(a)+1)):raise ValueError('Incomplete original-node displacement sequence')
        xy=mesh.nodes+a[:,1:3];record={'load_step':state['load_step'],'substep':state['substep'],'time':state['requested_time'],'passed':False}
        try:
            source_patch=mapped_patch(mesh,xy,topology[0]);target_patch=mapped_patch(mesh,xy,topology[1])
            bounds=[directional_bound(xy,mesh.boundary[src],target_patch),directional_bound(xy,mesh.boundary[tgt],source_patch)]
            record.update(directions=bounds,maximum_continuous_bound_mm=max(b['continuous_depth_upper_bound_mm'] for b in bounds),passed=all(b['continuous_depth_upper_bound_mm']<=LIMIT for b in bounds))
        except ValueError as exc:record['failure']=str(exc)
        records.append(record);row={**state,'failures':list(state['failures']),'continuous_geometry_passed':record['passed']}
        if not record['passed']:row['failures'].append('Continuous quadratic selected-arc geometry bound failed or uncertified')
        if not continuous:row['failures'].append('Earlier final mechanical gate failed')
        row['accepted']=bool(continuous and state['accepted'] and record['passed']);continuous=continuous and row['accepted'];states.append(row)
    geometry_path=run/'track_B_progressive_compression'/(source+'_continuous_geometry.json')
    write_json(geometry_path,{'schema':'v0610-additional-continuous-selected-arc-bound','limit_mm':LIMIT,'source_native_qualification_sha256':file_hash(native_path),'source_RST_sha256':file_hash(base/source/'compression.rst'),'scope':'Both selected arcs against exact original-element opposing patch. All other boundaries still require unchanged native whole-boundary crossing gate. Distance bound uses exact source curves, chord-bounded target geometry, arclength Lipschitz margin and certified artificial-cut clearance.','states':records})
    final={**q,'schema':'v0610-final-native-and-continuous-geometry-qualification','native_qualification_sha256':file_hash(native_path),'continuous_geometry_sha256':file_hash(geometry_path),'states':states,'accepted':bool(states) and all(s['accepted'] for s in states),'max_qualified_strain':max((s['requested_time'] for s in states if s['accepted']),default=None)}
    final['status']='PASS_COMPLETE_CROP_MECHANICAL_PATH' if final['accepted'] else 'HOLD_FINAL_CROP_MECHANICAL_GATE'
    write_json(run/'track_B_progressive_compression'/(source+'_mechanical_qualification.json'),final)
    print(final['status'],final['max_qualified_strain'],'geometry failures',sum(not r['passed'] for r in records),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--branch',default='');a=p.parse_args();qualify(a.source,a.branch)
