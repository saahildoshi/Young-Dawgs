"""Preregistered central crop: exact morphology, independently qualified mesh."""
import json
import numpy as np
import shapely
from shapely.geometry import box
from shapely.affinity import translate
from shapely.geometry.polygon import orient
from metamaterial_eval.simulation.geometry_adapter import authenticate_fixture,engineering_geometry
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.mesh_generation import generate_mesh,save_mesh
from metamaterial_eval.simulation.mesh_remediation import POLICY_B
from metamaterial_eval.simulation.mesh_validation import validate_mesh,feature_resolution
from metamaterial_eval.geometry.planar import rasterize_exact_geometry
from metamaterial_eval.geometry.validation.checks import select_probes
from metamaterial_eval.geometry.manifold.contacts import inspect_boundary
from metamaterial_eval.geometry.topology import analyze_raster_topology
from metamaterial_eval.simulation.reporting import mesh_hash
from scripts.v068_common import REPO,RUN,BASE,read,write_json,file_hash


def main():
    plan=read(RUN/'protocol/TRACK_B.json')
    _,mask,provenance=authenticate_fixture(REPO,CompressionConfig())
    source=REPO/provenance['geometry_path'];g=shapely.from_wkb(source.read_bytes())
    intersection=g.intersection(box(384,384,640,640))
    parts=list(intersection.geoms) if hasattr(intersection,'geoms') else [intersection]
    area=[p for p in parts if p.area>0];assert len(area)==1 and area[0].geom_type=='Polygon'
    pixel=orient(translate(area[0],xoff=-384,yoff=-384),1)
    cropped=mask[384:640,384:640]
    assert np.array_equal(rasterize_exact_geometry(pixel,256),cropped)
    topology=analyze_raster_topology(cropped);manifold=inspect_boundary(pixel)
    assert topology['intended_network'] and manifold['manifold'] and pixel.is_valid
    assert pixel.minimum_clearance>=1-1e-10
    config=CompressionConfig(width=2.56,height=2.56,boundary_size=plan['mesh']['boundary_size_mm'],bulk_size=plan['mesh']['bulk_size_mm'])
    geometry=engineering_geometry(pixel,256,config)
    directory=BASE/'track_B_source_001';directory.mkdir(parents=True,exist_ok=False)
    (directory/'geometry.wkb').write_bytes(shapely.to_wkb(geometry))
    np.save(directory/'source_mask.npy',cropped)
    probes=[p for p in select_probes(cropped) if p['phase']=='solid']
    pores=np.array([shapely.Polygon(r).area for r in geometry.interiors])
    spec={'specimen_id':'V068_TRACK_B_DESIGN009_SEED001_CENTRAL256','selection_registered_before_mechanics':True,
          'source_original_sha256':file_hash(source),'source_crop_pixel_box':[384,384,640,640],
          'geometry_sha256':file_hash(directory/'geometry.wkb'),'geometry_path':str(directory/'geometry.wkb'),
          'width_mm':2.56,'height_mm':2.56,'area_mm2':geometry.area,'solid_fraction':geometry.area/2.56**2,
          'pores':len(geometry.interiors),'equivalent_pore_diameter_mm_percentiles':np.percentile(np.sqrt(4*pores/np.pi),[0,25,50,75,100]).tolist(),
          'solid_axial_chord_pixel_percentiles':np.percentile([p['source_pixel_run'] for p in probes],[0,25,50,75,100]).tolist(),
          'minimum_source_pixel_mm':.01,'minimum_clearance_mm':geometry.minimum_clearance,
          'topology':topology,'manifold':manifold,'discarded_zero_area_intersections':len(parts)-len(area),
          'positive_area_components_removed':0,'physical_model':plan['material'],'config':config.manifest(),
          'scope':'Separate cropped specimen; artificial exterior cuts become its physical platen/free boundaries. No transferred full-specimen cut displacements.'}
    write_json(RUN/'track_B_geometry/GEOMETRY_001.json',spec)
    print('Geometry qualified',len(geometry.interiors),'pores; generating TRI6',flush=True)
    mesh=generate_mesh(geometry,config,policy=POLICY_B)
    quality,_=validate_mesh(mesh,geometry,config)
    features=feature_resolution(mesh,probes,config,resolution=256)
    save_mesh(mesh,directory/'mesh.npz')
    result={'mesh_id':'V068_TRACK_B_CENTRAL256_QUADRATIC_001','mesh_path':str(directory/'mesh.npz'),
            'byte_sha256':file_hash(directory/'mesh.npz'),'semantic_sha256':mesh_hash(mesh),
            'source_geometry_sha256':spec['geometry_sha256'],'quality':quality,'features':features,
            'config':config.manifest(),'accepted':bool(quality['accepted'] and features['accepted']),
            'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(RUN/'track_B_mesh/MESH_001.json',result)
    write_json(directory/'mesh_manifest.json',result)
    print(json.dumps({'accepted':result['accepted'],'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),'angle':quality['min_angle_deg'],'feature_min':features['minimum_elements_across']}),flush=True)


if __name__=='__main__':main()
