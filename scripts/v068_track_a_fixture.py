"""Expanded original-mesh parent-context fixture for focused Track A tests."""
import json
from pathlib import Path
import numpy as np

from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.reporting import mesh_hash
from scripts.v068_common import REPO,RUN,BASE,write_json,file_hash


ROI=(1.55,2.40,9.75,10.24)


def prepare():
    protocol={'schema':'young-dawgs-v068-track-a-expanded-fixture-registration',
              'ROI_centroid_mm':ROI,'selection':'Original canonical fine TRI6 element centroids in the fixed ROI; all original six nodes retained; no remesh or geometry edit.',
              'reason':'Wider side and deeper bottom context than v0.6.7 ROI [1.70,2.24,9.95,10.24], surrounding the original contact-onset nanogap at about [1.97,10.22].',
              'cut_motion':'Exact measured full-parent native displacement histories at every cut node for all 15 original states.',
              'parent_gate':{'cut_displacement_max_mm':1e-10,'core_U_RMS_relative':.02,
                             'core_SYY_SEQV_EYY_EXX_RMS_relative':.1,
                             'near_contact_gap':'Explicit signed quadratic gap difference; no inferred equality.'},
              'scope':'Local fixture only; extrapolation beyond parent is diagnostic, never a full-specimen performance result.',
              'contact_candidates':['original nodal2 baseline','unified5 if native-qualified','one localized pair if defensible'],
              'candidate_budget_seconds':5400}
    write_json(RUN/'protocol/TRACK_A_EXPANDED_FIXTURE.json',protocol)
    manifest=REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json'
    full,_,_=resolve_manifest(manifest,root=Path.home()/'YoungDawgs-Artifacts')
    center=full.nodes[full.triangles[:,:3]].mean(axis=1)
    original_elements=np.flatnonzero((center[:,0]>=ROI[0])&(center[:,0]<=ROI[1])&
                                 (center[:,1]>=ROI[2])&(center[:,1]<=ROI[3]))
    original_nodes=np.unique(full.triangles[original_elements]);reverse=np.full(len(full.nodes),-1,dtype=np.int64)
    reverse[original_nodes]=np.arange(len(original_nodes))
    triangles=reverse[full.triangles[original_elements]]
    faces=np.concatenate([triangles[:,[0,1,3]],triangles[:,[1,2,4]],triangles[:,[2,0,5]]])
    _,ix,counts=np.unique(np.sort(faces[:,:2],axis=1),axis=0,return_index=True,return_counts=True)
    boundary=faces[ix[counts==1]]
    original_faces={tuple(sorted(edge)):i for i,edge in enumerate(full.boundary)}
    parent_boundary=np.array([original_faces.get(tuple(sorted(original_nodes[e])),-1) for e in boundary])
    groups=np.array([str(full.boundary_groups[i]) if i>=0 else 'artificial_cut' for i in parent_boundary])
    for j,i in enumerate(parent_boundary):
        if i>=0:boundary[j]=reverse[full.boundary[i]]
    cut=np.unique(boundary[parent_boundary<0]);mesh=Mesh(full.nodes[original_nodes].copy(),triangles,boundary,groups)
    d=BASE/'track_A_expanded_fixture_001';d.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(d/'mesh.npz',nodes=mesh.nodes,triangles=mesh.triangles,
                        boundary=mesh.boundary,boundary_groups=mesh.boundary_groups,
                        original_nodes_one_based=original_nodes+1,
                        original_elements_one_based=original_elements+1,
                        original_boundary_indices=parent_boundary,
                        cut_nodes_zero_based=cut)
    old=json.loads((REPO/'experiments/pipeline_v0.6.6/run_001/summary/V0_6_6_VALIDATION.json').read_text(encoding='utf-8'))
    snapshots=sorted([s for s in old['snapshot_artifacts'] if s['model_variant']=='FINE_FULL_SELF_CONTACT_NODAL_V066_021'],
                     key=lambda s:s['engineering_strain'])
    if len(snapshots)!=15:raise ValueError('Full parent history count changed')
    fields=[]
    for item in snapshots:
        p=Path(item['directory'])/'native_displacement.npy';u=np.load(p,mmap_mode='r')
        fields.append(np.asarray(u[original_nodes,:2]));item['native_displacement_sha256']=file_hash(p)
    np.save(d/'measured_displacements.npy',np.stack(fields))
    spec={'schema':'young-dawgs-v068-original-mesh-expanded-fixture',
          'ROI_centroid_mm':ROI,'mesh_semantic_sha256':mesh_hash(mesh),
          'mesh_archive_sha256':file_hash(d/'mesh.npz'),
          'history_array_sha256':file_hash(d/'measured_displacements.npy'),
          'source_snapshots':snapshots,'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),
          'physical_faces':int(sum(parent_boundary>=0)),'artificial_cut_faces':int(sum(parent_boundary<0)),
          'cut_nodes':len(cut),'original_nodes_retained':len(original_nodes),
          'source_mesh_manifest_sha256':file_hash(manifest),
          'source_full_mesh_semantic_sha256':mesh_hash(full),
          'contact':'Physical original faces only; generated artificial cut skins deleted in every case.',
          'material':'E1000MPa, nu0.3, t1mm, plane stress, NLGEOM ON',
          'mechanical_scope':'DIAGNOSTIC_LOCAL_NOT_FULL_SPECIMEN'}
    write_json(d/'fixture_manifest.json',spec)
    write_json(RUN/'track_A_local_fixture/SOURCE_EXTRACTION.json',
               {**{k:v for k,v in spec.items() if k!='source_snapshots'},
                'source_snapshot_inventory':[{'engineering_strain':s['engineering_strain'],
                                              'native_displacement_sha256':s['native_displacement_sha256']} for s in snapshots],
                'raw_fixture_directory':str(d),'raw_fixture_mesh_sha256':file_hash(d/'mesh.npz')})
    print(json.dumps({k:spec[k] for k in ['nodes','TRI6','physical_faces','artificial_cut_faces','cut_nodes']}),flush=True)


if __name__=='__main__':prepare()
