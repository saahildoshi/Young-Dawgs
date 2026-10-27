"""Bounded registered v0.6.1 saved-layout and source-field experiments."""
import argparse
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
import shapely
from shapely.affinity import translate
from .config import CompressionConfig
from .mesh_generation import Mesh,MeshingPolicy,generate_mesh,save_mesh
from .mesh_diagnosis import load_mesh
from .element_quality import corner_metrics,quadratic_mapping,quality_summary
from .geometry_adapter import authenticate_fixture
from .mesh_validation import validate_mesh,feature_resolution
from .reporting import write_json,mesh_hash

BASE=Path('experiments/pipeline_v0.6.1')
HISTORICAL=Path('experiments/pipeline_v0.6/mesh_validation/run_003/level_02/generated/mesh.npz')
POLICY_B=MeshingPolicy(adaptive_curve_sampling=True,boundary_point_size=True,relocate_iterations=10)


def freeze_for_run(folder):
    protocol=BASE/'protocol/MESH_PROTOCOL.json'
    expected=json.loads((protocol.parent/'FREEZE.json').read_text())['sha256']
    digest=hashlib.sha256(protocol.read_bytes()).hexdigest()
    if digest!=expected:raise ValueError('Frozen protocol hash changed')
    (folder/'MESH_PROTOCOL.json').write_bytes(protocol.read_bytes())
    write_json(folder/'protocol_freeze.json',{'path':str(protocol),'sha256':digest})


def relocate_saved(mesh,iterations=10,*,failure_output=None):
    """Use documented discrete-entity Relocate2D on TRI3 corner layout only.

    Boundary corners are classified on a discrete curve, interior corners on
    the surface. Regenerate all interior midsides after relocating corners;
    every original boundary coordinate remains immutable.
    """
    import gmsh
    if iterations!=10:raise ValueError('Unregistered iteration setting')
    corner_ids=np.unique(mesh.triangles[:,:3]);bcorners=np.unique(mesh.boundary[:,:2])
    interior=np.setdiff1d(corner_ids,bcorners)
    started=time.perf_counter();gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.option.setNumber('General.NumThreads',1)
        gmsh.model.add('saved_layout');gmsh.model.addDiscreteEntity(1,2);gmsh.model.addDiscreteEntity(2,1,[2])
        def add_nodes(dim,tag,ids):
            gmsh.model.mesh.addNodes(dim,tag,(ids+1).tolist(),np.column_stack([mesh.nodes[ids],np.zeros(len(ids))]).ravel().tolist())
        add_nodes(1,2,bcorners);add_nodes(2,1,interior)
        gmsh.model.mesh.addElementsByType(2,1,[],(mesh.boundary[:,:2]+1).ravel().tolist())
        gmsh.model.mesh.addElementsByType(1,2,[],(mesh.triangles[:,:3]+1).ravel().tolist())
        gmsh.model.mesh.optimize('Relocate2D',force=True,niter=iterations,dimTags=[(2,1)])
        ids,xyz,_=gmsh.model.mesh.getNodes()
        nodes=mesh.nodes.copy();nodes[np.asarray(ids,dtype=np.int64)-1]=np.asarray(xyz).reshape(-1,3)[:,:2]
    finally:gmsh.finalize()
    if not np.array_equal(nodes[bcorners],mesh.nodes[bcorners]):
        if failure_output is not None:
            save_mesh(Mesh(nodes,mesh.triangles,mesh.boundary,mesh.boundary_groups),failure_output)
        raise ValueError('Optimizer moved fixed boundary corners')
    fixed=np.unique(mesh.boundary)
    mids=mesh.triangles[:,3:].ravel()
    p=nodes[mesh.triangles[:,:3]];means=((p+np.roll(p,-1,axis=1))/2).reshape(-1,2)
    movable=~np.isin(mids,fixed);nodes[mids[movable]]=means[movable]
    if not np.array_equal(nodes[fixed],mesh.nodes[fixed]):raise ValueError('Optimizer moved a boundary midside')
    return Mesh(nodes,mesh.triangles.copy(),mesh.boundary.copy(),mesh.boundary_groups.copy(),time.perf_counter()-started)


def saved_patch(mesh,eid,radius=.05):
    """Explicit local diagnostic, retaining all elements touching the radius."""
    points=mesh.nodes[mesh.triangles[:,:3]];center=points[eid].mean(axis=0)
    ids=np.flatnonzero(np.any(np.linalg.norm(points-center,axis=2)<radius,axis=1))
    tri=mesh.triangles[ids];nodes=np.unique(tri)
    edges=np.concatenate([tri[:,[0,1,3]],tri[:,[1,2,4]],tri[:,[2,0,5]]])
    _,inverse,counts=np.unique(np.sort(edges[:,:2],axis=1),axis=0,return_inverse=True,return_counts=True)
    boundary=edges[counts[inverse]==1]
    patch=Mesh(mesh.nodes[nodes],np.searchsorted(nodes,tri),np.searchsorted(nodes,boundary),np.full(len(boundary),'external'))
    return patch,{'source_elements_zero_based':ids.tolist(),'source_nodes_zero_based':nodes.tolist(),
                  'center_mm':center.tolist(),'radius_mm':radius,'scope':'CROPPED_MESH_DIAGNOSTIC_NOT_FULL_SPECIMEN'}


def local_trials(output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);freeze_for_run(output)
    geometry,_,provenance=authenticate_fixture(Path('.'),CompressionConfig())
    mesh=load_mesh(HISTORICAL)
    diagnosis=json.loads((BASE/'mesh_diagnosis/run_001/diagnosis.json').read_text())
    cases=[min(diagnosis['failed_elements'],key=lambda r:r['minimum_angle_deg']),
           next(r for r in diagnosis['failed_elements'] if r['boundary_edge_count']==2)]
    records=[]
    for case in cases:
        eid=case['element_zero_based'];folder=output/f'element_{eid:06d}';folder.mkdir()
        generated=folder/'generated';generated.mkdir()
        patch,scope=saved_patch(mesh,eid);save_mesh(patch,generated/'original_patch.npz')
        try:
            optimized=relocate_saved(patch,failure_output=generated/'A_REJECTED_boundary_motion.npz');save_mesh(optimized,generated/'A_relocated.npz')
            c=corner_metrics(optimized.nodes[optimized.triangles[:,:3]]);q=quadratic_mapping(optimized.nodes[optimized.triangles])
            result_a={**quality_summary(c,q),'boundary_unchanged':bool(np.array_equal(patch.nodes[np.unique(patch.boundary)],optimized.nodes[np.unique(patch.boundary)])),
                      'seconds':optimized.generation_seconds,'mesh_sha256':mesh_hash(optimized)}
        except Exception as exc:result_a={'status':'FAILED_LOCAL_API_OR_QUALITY','reason':str(exc)}
        center=mesh.nodes[mesh.triangles[eid,:3]].mean(axis=0)
        # The crop remains an explicitly distinct diagnostic with exact source
        # intersection, translation only, and no claim of full-specimen equivalence.
        low=np.maximum(center-.05,[0,0]);high=np.minimum(center+.05,[10.24,10.24])
        crop=geometry.intersection(shapely.box(*low,*high))
        if crop.geom_type!='Polygon':
            result_b={'status':'UNSUPPORTED_MULTIPART_LOCAL_CROP','geometry_type':crop.geom_type}
        else:
            crop=translate(crop,xoff=-low[0],yoff=-low[1])
            config=replace(CompressionConfig(),width=float(high[0]-low[0]),height=float(high[1]-low[1]))
            candidate=generate_mesh(crop,config,policy=POLICY_B);save_mesh(candidate,generated/'B_remeshed.npz')
            c=corner_metrics(candidate.nodes[candidate.triangles[:,:3]]);q=quadratic_mapping(candidate.nodes[candidate.triangles])
            polys=shapely.polygons(candidate.nodes[candidate.triangles[:,:3]])
            region=shapely.build_area(shapely.multilinestrings(candidate.nodes[candidate.boundary[:,:2]]))
            result_b={**quality_summary(c,q),'source_intersection_offset_mm':low.tolist(),
                      'source_intersection_box_mm':[low.tolist(),high.tolist()],
                      'domain_difference_mm2':float(region.symmetric_difference(crop).area),
                      'coverage_valid':bool(shapely.coverage_is_valid(polys)),
                      'seconds':candidate.generation_seconds,'nodes':len(candidate.nodes),'mesh_sha256':mesh_hash(candidate),
                      'scope':'SOURCE_CROP_DIAGNOSTIC_NOT_FULL_SPECIMEN'}
        record={'element_zero_based':eid,'original':scope,'A':result_a,'B':result_b}
        write_json(folder/'trial.json',record);records.append(record)
    supported=all(r['B'].get('below_angle_gate',1)==0 and r['B'].get('quadratic_mapping',{}).get('invalid_or_uncertified_elements',1)==0
                  and r['B'].get('coverage_valid') and r['B'].get('domain_difference_mm2',1)<1e-12 for r in records)
    report={'trials':records,'B_supported_for_full_candidate':bool(supported),
            'A_full_candidate_justified':all(r['A'].get('below_angle_gate',1)==0 for r in records),
            'settings_B':asdict(POLICY_B),'historical_source_hash':provenance['geometry_sha256']}
    write_json(output/'local_trial_summary.json',report)
    print(json.dumps({'B_supported_for_full_candidate':supported,'A':[(r['element_zero_based'],r['A'].get('min_angle_deg')) for r in records],
                      'B':[(r['element_zero_based'],r['B'].get('min_angle_deg'),r['B'].get('status')) for r in records]}),flush=True)
    return report


def worker(output,level):
    folder=Path(output);folder.mkdir(parents=True,exist_ok=False);freeze_for_run(folder)
    protocol=json.loads((folder/'MESH_PROTOCOL.json').read_text())
    levels={v['id']:v for v in protocol['new_full_mesh_levels_after_strategy_identified']}
    if level not in levels:raise ValueError('Unregistered full level')
    settings=levels[level]
    config=replace(CompressionConfig(),boundary_size=settings['boundary_size_mm'],bulk_size=settings['bulk_size_mm'])
    generated=folder/'generated';generated.mkdir()
    started=time.perf_counter()
    try:
        geometry,_,provenance=authenticate_fixture(Path('.'),config)
        mesh=generate_mesh(geometry,config,policy=POLICY_B);generation=time.perf_counter()-started
        save_mesh(mesh,generated/'mesh.npz')
        if len(mesh.nodes)>4000000 or len(mesh.triangles)>1800000:raise RuntimeError('Registered node/element budget exceeded')
        at=time.perf_counter();quality,distribution=validate_mesh(mesh,geometry,config);validation=time.perf_counter()-at
        at=time.perf_counter();features=feature_resolution(mesh,provenance['source_only_solid_probes'],config);feature_seconds=time.perf_counter()-at
        np.savez_compressed(generated/'quality_distributions.npz',quality=distribution,
                           min_angle_deg=corner_metrics(mesh.nodes[mesh.triangles[:,:3]])['minimum_angle_deg'])
        write_json(folder/'mesh_quality.json',quality);write_json(folder/'feature_resolution.json',features)
        write_json(folder/'simulation_manifest.json',{'schema':'young-dawgs-v0.6.1-mesh','config':config.manifest(),
              'geometry_sha256':provenance['geometry_sha256'],'mesh_sha256':mesh_hash(mesh),'meshing_policy':asdict(POLICY_B),
              'mesh_gate':quality['accepted'],'feature_gate':features['accepted'],'mechanical_convergence':'UNQUALIFIED',
              'geometry_provenance':provenance})
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        report={'level':level,'accepted':quality['accepted'] and features['accepted'],'quality':quality,
                'feature_minimum_elements_across':features['minimum_elements_across'],'features_accepted':features['accepted'],
                'generation_seconds_including_authentication':generation,'validation_seconds':validation,
                'feature_validation_seconds':feature_seconds,'total_seconds':time.perf_counter()-started,
                'process_peak_rss_bytes':peak,'mesh_npz_bytes':(generated/'mesh.npz').stat().st_size}
        write_json(folder/'run_summary.json',report)
        print(f'{level}: nodes={len(mesh.nodes)} elements={len(mesh.triangles)} min_angle={quality["min_angle_deg"]:.6f} accepted={report["accepted"]}',flush=True)
    except Exception as exc:
        write_json(folder/'FAILURE.json',{'stage':'full_candidate','reason':str(exc),'error_type':type(exc).__name__})
        raise


def study(output,local_evidence):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    evidence=json.loads(Path(local_evidence).read_text())
    if not evidence.get('B_supported_for_full_candidate'):raise RuntimeError('Full candidate blocked: local strategy evidence failed')
    if shutil.disk_usage('.').free<2*1024**3:raise RuntimeError('Insufficient registered free disk space')
    output.mkdir(parents=True);freeze_for_run(output);summaries=[]
    # The replacement fine candidate is assessed first; only then assess truly
    # different full-field coarse/finer resolutions, all with new identifiers.
    for level in ['fine_new','coarse_new','finer_new']:
        folder=output/level;started=time.perf_counter();peak=0;stop=None
        with (output/(level+'_worker.log')).open('w') as stream:
            process=subprocess.Popen([sys.executable,'-m','metamaterial_eval.simulation.mesh_remediation','worker','--output',str(folder),'--level',level],stdout=stream,stderr=subprocess.STDOUT)
            while process.poll() is None:
                proc=Path(f'/proc/{process.pid}/status')
                if proc.exists():
                    import re
                    match=re.search(r'^VmRSS:\s+(\d+)\s+kB',proc.read_text(),re.MULTILINE)
                    if match:peak=max(peak,int(match.group(1))*1024)
                if peak>4*1024**3:stop='RSS_BUDGET_EXCEEDED'
                if time.perf_counter()-started>600:stop='TIME_BUDGET_EXCEEDED'
                if stop:process.terminate();process.wait();break
                time.sleep(.5)
        if stop or process.returncode!=0:
            report={'level':level,'accepted':False,'status':stop or 'WORKER_FAILURE','returncode':process.returncode,'sampled_peak_rss_bytes':peak}
            if not folder.exists():folder.mkdir()
            write_json(folder/'WORKER_FAILURE.json',report)
        else:
            report=json.loads((folder/'run_summary.json').read_text());report['sampled_peak_rss_bytes']=peak
        summaries.append(report);write_json(output/'study_summary.json',{'levels':summaries,'local_evidence':str(local_evidence),
                      'mechanical_convergence':'UNQUALIFIED_NO_SOLVER','budget_monitor':'Linux /proc VmRSS sampled every0.5s; worker lifetime high-water RSS also reported'})
        print(level,report.get('accepted'),flush=True)
        if not report.get('accepted'):break
    return summaries


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['local','study','worker'])
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--level');parser.add_argument('--local-evidence',type=Path)
    args=parser.parse_args()
    if args.command=='local':local_trials(args.output)
    elif args.command=='worker':worker(args.output,args.level)
    else:study(args.output,args.local_evidence)


if __name__=='__main__':main()
