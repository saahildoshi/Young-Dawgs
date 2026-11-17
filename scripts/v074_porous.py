"""Exact historical solid-network extrusion, with open through-thickness pores."""
import hashlib
import importlib.metadata
import numpy as np
from scipy import ndimage as ndi
import shapely
from shapely.geometry import box, MultiLineString
from shapely import affinity
import manifold3d
import trimesh
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,ASSETS,now

SOURCE=REPO/'experiments/pipeline_v0.4.1/resolution_validation/design_009/seed_001/1024/microstructure.npy'
CACHE=REPO/'experiments/pipeline_v0.5/baseline_vectorization/run_003/fixture_B_design009_seed001'


def stats(a):
    solid,n=ndi.label(a)
    void,nv=ndi.label(~a)
    exterior=set(np.unique(np.r_[void[0],void[-1],void[:,0],void[:,-1]]))-{0}
    return {'pixels':int(a.size),'solid_pixels':int(a.sum()),'solid_fraction':float(a.mean()),
        'solid_components_4':n,'solid_components_8':ndi.label(a,np.ones((3,3)))[1],
        'void_regions_4':nv,'enclosed_pores':nv-len(exterior),'boundary_clipped_void_regions':len(exterior)}


def extrude(poly,path):
    original=poly
    poly=poly.simplify(0,preserve_topology=True)
    assert poly.symmetric_difference(original).area==0
    rings=[np.asarray(poly.exterior.coords)[:-1,:2]]+[np.asarray(r.coords)[:-1,:2] for r in poly.interiors]
    cross=manifold3d.CrossSection(rings,manifold3d.FillRule.EvenOdd)
    solid=manifold3d.Manifold.extrude(cross,5.)
    assert str(solid.status())=='Error.NoError'
    # Remove triangulation redundancy at a nominal1e-7mm tolerance. Source XY
    # support is independently rechecked at three heights after STL export.
    mesh=solid.simplify(1e-7).to_mesh()
    trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(path,file_type='stl')


def validate(path,poly):
    mesh=trimesh.load_mesh(path,process=False);mesh.merge_vertices();mesh.remove_unreferenced_vertices()
    valence=np.bincount(mesh.edges_unique_inverse)
    slices={}
    for z in [.25,2.5,4.75]:
        segments=trimesh.intersections.mesh_plane(mesh,[0,0,1],[0,0,z])
        # Floating plane/triangle arithmetic creates sub-ulp endpoint gaps.
        # Snap only the independent section linework at1e-7mm, far below the
        # exact binary display pitch; neither exported mesh nor source changes.
        section=shapely.build_area(shapely.set_precision(MultiLineString(segments[:,:,:2].tolist()),1e-7))
        slices[str(z)]={'area_mm2':float(section.area),'symmetric_difference_mm2':float(section.symmetric_difference(poly).area),
            'through_holes':len(section.interiors) if section.geom_type=='Polygon' else None}
    status=manifold3d.Manifold(manifold3d.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32))).status()
    lowx,lowy,highx,highy=poly.bounds
    checks={'finite':bool(np.isfinite(mesh.vertices).all()),'watertight':bool(mesh.is_watertight),
        'oriented_normals':bool(mesh.is_winding_consistent),'positive_volume':mesh.volume>0,
        'one_connected_body':len(mesh.split(only_watertight=False))==1,'two_faces_per_edge':bool(np.all(valence==2)),
        'no_duplicate_faces':len(np.unique(np.sort(mesh.faces,axis=1),axis=0))==len(mesh.faces),
        'no_degenerate_faces':bool(np.all(mesh.area_faces>1e-10)),
        'correct_bounds':bool(np.allclose(mesh.bounds,[[lowx,lowy,0],[highx,highy,5]],atol=1e-6)),
        'analytic_volume':abs(mesh.volume-poly.area*5)<.01,
        'flat_top_and_bottom':bool(np.all(np.isin(mesh.vertices[:,2],[0.,5.]))),
        'Euler_genus_matches_through_pores':int(mesh.euler_number)==2-2*len(poly.interiors),
        'independent_three_sections_match_source':all(r['symmetric_difference_mm2']<.001 and r['through_holes']==len(poly.interiors) for r in slices.values()),
        'manifold3d_accepts':str(status)=='Error.NoError',
        'self_intersections_excluded_by_simple_polygon_straight_extrusion':bool(poly.is_valid and poly.geom_type=='Polygon')}
    checks={k:bool(v) for k,v in checks.items()}
    record={'STL_sha256':sha(path),'bytes':path.stat().st_size,'vertices':len(mesh.vertices),'triangles':len(mesh.faces),
        'volume_mm3':float(mesh.volume),'bounds_mm':mesh.bounds.tolist(),'through_holes':len(poly.interiors),
        'Euler_number':int(mesh.euler_number),'boundary_edges':int((valence==1).sum()),'nonmanifold_edges':int((valence!=2).sum()),
        'independent_sections':slices,'checks':checks,'passed':all(checks.values()),
        'reimport':'Independent trimesh STL parse, identical-position welding only; no mesh repair',
        'intersection_scope':'Valid simple polygon straight extrusion; independently matched horizontal sections and analytic volume; no generic arbitrary-triangle collision algorithm claimed'}
    write(RUN/'fabrication'/f'{path.stem}_REIMPORT.json',record)
    assert record['passed'],[k for k,v in checks.items() if not v]
    return mesh,record


def preview(mesh,full,crop):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(14,10))
    ax=fig.add_subplot(2,2,1,projection='3d')
    rv,rf=trimesh.remesh.subdivide_to_size(mesh.vertices,mesh.faces,max_edge=8,max_iter=8)
    render=trimesh.Trimesh(rv,rf,process=False)
    light=np.maximum(.35,render.face_normals@np.array([.2,-.3,.9]))
    colors=np.tile([.18,.52,.57,1.],(len(rf),1));colors[:,:3]*=light[:,None]
    ax.add_collection3d(Poly3DCollection(render.triangles,facecolors=colors,edgecolors='none',antialiased=False,zsort='min'))
    ax.set(xlim=(0,165),ylim=(0,165),zlim=(0,12),xlabel='Display X (mm)',ylabel='Display Y (mm)',title='Actual print STL · open through-holes')
    ax.set_box_aspect((165,165,12));ax.view_init(35,-55);ax.set_zticks([])
    ax=fig.add_subplot(2,2,2);up=mesh.face_normals[:,2]>.99
    ax.add_collection(PolyCollection(mesh.triangles[up,:,:2],facecolors='#2e8592',edgecolors='none',antialiased=False))
    ax.set(xlim=(0,165),ylim=(0,165),aspect='equal',xlabel='Display X (mm)',ylabel='Display Y (mm)',title='Actual STL top · 165 ×165 ×5 mm')
    ax=fig.add_subplot(2,2,3);ax.imshow(full,cmap='gray_r',interpolation='nearest')
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((383.5,383.5),256,256,fill=False,edgecolor='#d67c20',linewidth=2))
    ax.set_title('Authenticated full1024 mask · central crop marked');ax.set_xticks([]);ax.set_yticks([])
    ax=fig.add_subplot(2,2,4)
    side=np.abs(mesh.face_normals[:,1])>.99
    ax.add_collection(PolyCollection(mesh.triangles[side][:,:,[0,2]],facecolors='#2e8592',edgecolors='none',antialiased=False))
    ax.set(xlim=(0,165),ylim=(0,6),xlabel='Display X (mm)',ylabel='Z (mm)',title='Actual STL side projection · no backing plate')
    ax.set_aspect('equal')
    fig.suptitle('Design9 seed1 · historical porous geometry, enlarged for presentation',fontsize=15)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(ASSETS/'POROUS_METAMATERIAL_PREVIEW.png',dpi=170);plt.close(fig)


def build():
    assert sha(SOURCE)=='e4b28517f4147a9f5eefd045a023f8f7bf2f99c63e950d995ad9ce5bbe68faf8'
    a=np.load(SOURCE,allow_pickle=False);assert a.shape==(1024,1024) and set(np.unique(a))=={0,1}
    assert hashlib.sha256(a.tobytes()).hexdigest()=='a29ab50312d0181c6bce0aa1fa644da953fdb467f42acd945d79507c3d28d145'
    full=a.astype(bool);crop=full[384:640,384:640]
    polygon=shapely.from_wkb((CACHE/'polygon_candidate.wkb').read_bytes())
    rings=[np.asarray(polygon.exterior.coords)]+[np.asarray(r.coords) for r in polygon.interiors]
    assert polygon.is_valid and polygon.area==int(a.sum())
    assert all(np.all(r==np.rint(r)) and np.all(np.any(np.diff(r,axis=0)==0,axis=1)) for r in rings)
    shapely.prepare(polygon)
    y,x=np.mgrid[:1024,:1024]
    assert np.array_equal(shapely.contains_xy(polygon,x+.5,y+.5),full),'Cached polygon must match every original pixel'
    clipped=polygon.intersection(box(384,384,640,640))
    # Eight zero-area boundary line remnants are not solid pixels. This is the
    # same positive-area intersection convention as the historical crop audit.
    parts=list(clipped.geoms) if clipped.geom_type=='GeometryCollection' else [clipped]
    positive=[g for g in parts if g.area>0]
    assert len(positive)==1 and all(g.area==0 for g in parts if g not in positive)
    selected=affinity.translate(positive[0],xoff=-384,yoff=-384)
    assert selected.area==int(crop.sum()) and selected.geom_type=='Polygon' and len(selected.interiors)==19
    # Flip image y down to presentation y up; preserve every source pixel.
    fullmm=affinity.scale(affinity.translate(affinity.scale(polygon,xfact=1,yfact=-1,origin=(0,0)),yoff=1024),xfact=160/1024,yfact=160/1024,origin=(0,0))
    cropmm=affinity.scale(affinity.translate(affinity.scale(selected,xfact=1,yfact=-1,origin=(0,0)),yoff=256),xfact=.625,yfact=.625,origin=(0,0))
    frame=box(-2.5,-2.5,162.5,162.5).difference(box(0,0,160,160))
    framed=affinity.translate(cropmm.union(frame),xoff=2.5,yoff=2.5)
    assert framed.is_valid and framed.geom_type=='Polygon'
    write(RUN/'fabrication/POROUS_EXPORT_POLICY.json',{'registered_utc':now(),'before_export':True,
        'recommended':'Authenticated central256 crop,160mm field,5mm thickness,2.5mm external frame,165mm outer dimensions',
        'selection_reason':'Full1024 at160mm has0.15625mm pixel steps and sub0.8mm skeleton-width proxies; central crop magnifies original details fourfold. Full faithful export retained.',
        'internal_source_pixels_changed':0,'no_backing_plate':True,'solid_network_edits':False,
        'frame_only_outside_original_field':True,'frame_captures_boundary_clipped_pores':True,
        'geometry_is_presentation_not_calibrated_specimen':True})
    variants={'POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl':fullmm,
        'POROUS_METAMATERIAL_ORIGINAL.stl':cropmm,'POROUS_METAMATERIAL_PRINT_READY.stl':framed}
    records={}
    for name,poly in variants.items():
        path=ASSETS/name;assert not path.exists();extrude(poly,path)
        mesh,records[name]=validate(path,poly)
        if name.endswith('PRINT_READY.stl'):final=mesh
        print(name,records[name]['passed'],len(mesh.faces),'pores',len(poly.interiors),flush=True)
    origin={'created_utc':now(),'design':9,'seed':1,'source_path':str(SOURCE.relative_to(REPO)).replace('\\','/'),
        'source_file_sha256':sha(SOURCE),'source_array_sha256':hashlib.sha256(a.tobytes()).hexdigest(),
        'source_shape':[1024,1024],'phase_definitions':{'0':'open void','1':'solid network'},
        'source_historical15_pixel_repair':'The authenticated v041 canonical source already contains15 add-only topology repairs, preserved unchanged; no v074 internal edits.',
        'historical_provenance_path':str((CACHE/'input_provenance.json').relative_to(REPO)).replace('\\','/'),
        'historical_provenance_sha256':sha(CACHE/'input_provenance.json'),'cached_exact_polygon_sha256':sha(CACHE/'polygon_candidate.wkb'),
        'cached_polygon_authentication':'Every integer/axis-aligned ring plus all1048576 original pixel centers and exact source area verified',
        'full_source':stats(full),'crop_source':stats(crop),'crop_box_image_row_column':[384,384,640,640],
        'crop_array_semantic_sha256':hashlib.sha256(a[384:640,384:640].tobytes()).hexdigest(),
        'crop_zero_area_boundary_remnants_discarded':len(parts)-len(positive),
        'display_dimensions_not_simulation_scale':True,'thickness_mm':5,'full_field_mm':160,'crop_field_mm':160,
        'recommended_frame_mm':2.5,'recommended_outer_mm':165,'internal_pixels_changed':0,
        'print_source_area_mm2':float(cropmm.area),'print_framed_area_mm2':float(framed.area),
        'external_frame_added_area_mm2':float(framed.area-cropmm.area),
        'crop_field_solid_fraction':float(crop.mean()),'framed_envelope_solid_fraction':float(framed.area/165**2),
        'crop_original_enclosed_pores':19,'framed_through_pores':len(framed.interiors),
        'pore_change':'External frame encloses boundary-clipped void pockets; all original interior pores remain open and every internal solid/void pixel is unchanged.',
        'fabrication_only_no_FE_rerun':True,'physically_printed':False,
        'STL_files':{n:sha(ASSETS/n) for n in variants},'STL_units':'Unitless; import as millimeters',
        'packages':{n:importlib.metadata.version(n) for n in ['trimesh','manifold3d','shapely']}}
    write(ASSETS/'POROUS_METAMATERIAL_SOURCE_MANIFEST.json',origin)
    write(ASSETS/'POROUS_METAMATERIAL_STL_VALIDATION.json',{'created_utc':now(),'variants':records,
        'actual_slicer_status':'PENDING','minimum_width_status':'Source-faithful internal geometry retains0.625mm pixel-edge tapers. External frame supports boundaries, not a guarantee of universal0.8mm minimum neck. Actual toolpaths must be checked;0.4mm nozzle assumed.',
        'no_self_intersection_claim_beyond_documented_construction_proof':True,'physically_printed':False})
    preview(final,full,crop)


if __name__=='__main__':build()
