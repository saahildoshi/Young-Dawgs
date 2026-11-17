"""Authenticated presentation relief; never a physical 3D reconstruction or FE mesh."""
import importlib.metadata
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import trimesh
import manifold3d
from scripts.v070_protocol import read,write,sha
from scripts.v074_experiment import RUN,DOC,ASSETS,MICRO,now

def diagonal_contacts(mask):
    a,b,c,d=mask[:-1,:-1],mask[:-1,1:],mask[1:,:-1],mask[1:,1:]
    return (a&d&~b&~c)|(~a&~d&b&c)

def print_mask(source):
    shape=np.ones((3,3),bool)
    mask=ndi.binary_closing(ndi.binary_opening(source,structure=shape),structure=shape)
    steps=[]
    # A documented fabrication-only union resolves remaining nonmanifold point contacts.
    for sweep in range(16):
        sites=np.argwhere(diagonal_contacts(mask))
        if not len(sites):break
        before=int(mask.sum())
        for y,x in sites:mask[y:y+2,x:x+2]=True
        steps.append({'sweep':sweep,'checkerboards':len(sites),'pixels_added':int(mask.sum())-before})
    if diagonal_contacts(mask).any():raise ValueError('Print topology cleanup exhausted registered16 sweeps')
    return mask,steps

def heightfield(mask,field=160.,border=4.,base=2.4,relief=1.2):
    if mask.shape!=(256,256):raise ValueError('Expected source field256²')
    edges=np.r_[0.,border+np.linspace(0,field,257),field+2*border]
    yy,xx=np.meshgrid(edges,edges,indexing='ij');xy=np.column_stack([xx.ravel(),yy.ravel()]);nv=len(xy)
    vertices=np.vstack([np.column_stack([xy,np.full(nv,z)]) for z in [0,base,base+relief]])
    cells=np.zeros((258,258),bool);cells[1:-1,1:-1]=np.flipud(mask)
    grid=np.arange(nv).reshape(259,259);q=np.column_stack([grid[:-1,:-1].ravel(),grid[:-1,1:].ravel(),grid[1:,1:].ravel(),grid[1:,:-1].ravel()])
    levels=np.where(cells,2,1);top=q+levels.ravel()[:,None]*nv
    faces=[top[:,[0,1,2]],top[:,[0,2,3]],q[:,[0,3,2]],q[:,[0,2,1]]]
    pad=np.pad(levels,1)
    for neighbour,order in [(pad[1:-1,2:],[1,2,2,1]),(pad[1:-1,:-2],[3,0,0,3]),(pad[2:,1:-1],[2,3,3,2]),(pad[:-2,1:-1],[0,1,1,0])]:
        use=(levels>neighbour).ravel();local=q[use][:,order];low=neighbour.ravel()[use];high=levels.ravel()[use]
        local=local+np.column_stack([low,low,high,high])*nv
        faces.extend([local[:,[0,1,2]],local[:,[0,2,3]]])
    m=trimesh.Trimesh(vertices=vertices,faces=np.vstack(faces),process=False);m.remove_unreferenced_vertices()
    return m

def validate(path,mask,require_manifold):
    # Independent file parse, no face deletion, winding repair, hole filling or geometry edits.
    m=trimesh.load_mesh(path,process=False);raw_faces=len(m.faces);m.merge_vertices();m.remove_unreferenced_vertices()
    counts=np.bincount(m.edges_unique_inverse);areas=m.area_faces
    adjacency=m.face_adjacency;graph=coo_matrix((np.ones(len(adjacency)*2),(np.r_[adjacency[:,0],adjacency[:,1]],np.r_[adjacency[:,1],adjacency[:,0]])),shape=(len(m.faces),len(m.faces)))
    components=int(connected_components(graph,directed=False)[0])
    expected=168**2*2.4+int(mask.sum())*(160/256)**2*1.2
    flat_faces=m.triangles[np.all(np.abs(m.triangles[:,:,2])<1e-8,axis=1)]
    raised_area=float(m.area_faces[(m.face_normals[:,2]>.999)&(m.triangles_center[:,2]>3.5)].sum())
    status=manifold3d.Manifold(manifold3d.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32))).status()
    checks={'file_exists_nonzero':path.is_file() and path.stat().st_size>0,'finite_coordinates':bool(np.isfinite(m.vertices).all()),
        'positive_volume':m.volume>0,'consistent_winding':bool(m.is_winding_consistent),'watertight':bool(m.is_watertight),
        'no_boundary_edges':bool(np.all(counts!=1)),'two_faces_per_edge':bool(np.all(counts==2)),
        'no_duplicate_faces':len(np.unique(np.sort(m.faces,axis=1),axis=0))==len(m.faces),
        'no_degenerate_faces':bool(np.all(areas>1e-10)),'one_face_connected_surface':components==1,
        'bounds':bool(np.allclose(m.bounds,[[0,0,0],[168,168,3.6]],atol=1e-6)),
        'analytic_volume':abs(m.volume-expected)/expected<1e-6,
        'flat_base_complete_area':abs(trimesh.triangles.area(flat_faces).sum()-168**2)<.01,
        'raised_projection_matches_mask':abs(raised_area-int(mask.sum())*(160/256)**2)<.01,
        'manifold3d_accepts_oriented_2manifold':str(status)=='Error.NoError',
        'no_diagonal_only_raised_contacts':not diagonal_contacts(mask).any()}
    # Exhaustive geometric construction invariant: one top/bottom per XY cell,
    # one exposed height-transition side per edge; disjoint cell/edge interiors.
    # No overlapping closed shells are combined. This excludes crossing surfaces
    # for this axis-aligned height field when checkerboard singularities are absent.
    checks['self_intersection_excluded_by_heightfield_support_and_no_checkerboards']=not diagonal_contacts(mask).any()
    checks={name:bool(value) for name,value in checks.items()}
    result={'checked_utc':now(),'file_sha256':sha(path),'file_bytes':path.stat().st_size,'raw_imported_faces':raw_faces,'welded_vertices':len(m.vertices),
        'faces':len(m.faces),'volume_mm3':float(m.volume),'analytic_volume_mm3':expected,'bounds_mm':m.bounds.tolist(),
        'boundary_edges':int((counts==1).sum()),'nonmanifold_edges':int((counts!=2).sum()),'surface_components':components,
        'manifold3d_status':str(status),'checks':checks,'passed':all(checks.values()),
        'independent_reimport':'trimesh STL parser, identical-position vertex welding only; no geometry repair',
        'intersection_scope':'Construction proof plus exhaustive lattice checkerboard test, volume/projection checks and independent manifold/topology validation; no generic arbitrary-triangle intersection solver claimed'}
    if require_manifold:assert result['passed'],[k for k,v in checks.items() if not v]
    return m,result

def preview(m,source,mask):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import ListedColormap
    cmap=ListedColormap(['#29465c','#e1a944']);fig=plt.figure(figsize=(14,10))
    ax=fig.add_subplot(2,2,1,projection='3d')
    color=np.where((m.triangles_center[:,2]>2.45)[:,None],np.array([.88,.66,.27,1]),np.array([.20,.33,.43,1]))
    light=np.maximum(.35,np.asarray(m.face_normals)@np.array([.2,-.3,.9]));color[:,:3]*=light[:,None]
    # Subdivide only the rendering tessellation to avoid painter-sort occlusion
    # by large coplanar base triangles; the exported STL is unchanged.
    rv,rf=trimesh.remesh.subdivide_to_size(m.vertices,m.faces,max_edge=8,max_iter=8)
    render=trimesh.Trimesh(rv,rf,process=False)
    color=np.where((render.triangles_center[:,2]>2.45)[:,None],np.array([.88,.66,.27,1]),np.array([.20,.33,.43,1]))
    light=np.maximum(.35,np.asarray(render.face_normals)@np.array([.2,-.3,.9]));color[:,:3]*=light[:,None]
    ax.add_collection3d(Poly3DCollection(render.triangles,facecolors=color,edgecolors='none',antialiased=False,zsort='min'))
    ax.set(xlim=(0,168),ylim=(0,168),zlim=(0,12),xlabel='Display X (mm)',ylabel='Display Y (mm)',zlabel='Z (mm)',title='Actual print STL · isometric')
    ax.set_box_aspect((168,168,12));ax.view_init(elev=35,azim=-55)
    ax.set_zticks([])
    ax=fig.add_subplot(2,2,2);use=m.face_normals[:,2]>.99
    polys=PolyCollection(m.triangles[use,:,:2],array=m.triangles_center[use,2],cmap=cmap,clim=(2.4,3.6),edgecolors='none',antialiased=False)
    ax.add_collection(polys);ax.set(xlim=(0,168),ylim=(0,168),aspect='equal',title='Actual STL top view · 168 ×168 mm',xlabel='Display X (mm)',ylabel='Display Y (mm)')
    ax=fig.add_subplot(2,2,3);ax.imshow(source,cmap=cmap,vmin=0,vmax=1,interpolation='nearest')
    ax.set(title='Authenticated source annotation · pixel geometry');ax.set_xticks([]);ax.set_yticks([])
    ax=fig.add_subplot(2,2,4)
    ax.fill_between([0,168],0,2.4,color='#29465c');ax.fill_between([4,164],2.4,3.6,color='#e1a944',alpha=.15,label='Relief envelope')
    use=np.abs(m.face_normals[:,1])>.9
    # Profile triangles projected from the actual exported mesh; overlapping
    # projections are expected in an orthographic side silhouette.
    side_colors=np.where(m.triangles_center[use,2]>2.45,'#e1a944','#29465c')
    ax.add_collection(PolyCollection(m.triangles[use][:,:,[0,2]],facecolors=side_colors,edgecolors='none',antialiased=False))
    ax.set(xlim=(0,168),ylim=(0,4.2),xlabel='Display X (mm)',ylabel='Z (mm)',title='Actual STL side projection · base2.4 / relief1.2 mm')
    ax.set_aspect('equal')
    fig.suptitle('Enlarged P3 presentation relief · arbitrary display dimensions, not a measured 3D material',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(ASSETS/'P3_REFERENCE_STL_PREVIEW.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,a,title in zip(axes,[source,mask,source!=mask],['Exact source','Print-safe XY mask','Changed source pixels']):
        ax.imshow(a,cmap=cmap,interpolation='nearest');ax.set_title(title);ax.set_xticks([]);ax.set_yticks([])
    fig.tight_layout();fig.savefig(ASSETS/'P3_SOURCE_VS_PRINT_SAFE.png',dpi=160);plt.close(fig)

def build():
    original=MICRO/'references/P3/evaluation_only_labels.npy';source=np.load(original)==5
    assert int(source.sum())==20731
    mask,steps=print_mask(source)
    write(RUN/'fabrication/PRINT_SAFE_POLICY_ADDENDUM.json',{'registered_utc':now(),'before_STL_export':True,
        'reason':'14 exact checkerboards;3 remain after prescribed3x3 opening/closing. Checkerboards create nonmanifold vertical edges in a two-level height field.',
        'additional_operation':'For each remaining2x2 diagonal-only raised contact, fill both empty cells. At most16 monotone sweeps, otherwise explicit failure.',
        'mechanical_or_experimental_source_changed':False,'operations_observed':steps})
    records={}
    for name,a in [('P3_REFERENCE_EXACT_RELIEF.stl',source),('P3_REFERENCE_PRINT_READY.stl',mask)]:
        raw=heightfield(a);solid=manifold3d.Manifold(manifold3d.Mesh(np.asarray(raw.vertices,dtype=np.float32),np.asarray(raw.faces,dtype=np.uint32)))
        if str(solid.status())=='Error.NoError':
            compact=solid.simplify(1e-7).to_mesh();raw=trimesh.Trimesh(compact.vert_properties[:,:3],compact.tri_verts,process=False)
        path=ASSETS/name;raw.export(path,file_type='stl')
        imported,record=validate(path,a,name.endswith('PRINT_READY.stl'));records[name]=record
        if name.endswith('PRINT_READY.stl'):final=imported
    np.save(ASSETS/'P3_PRINT_SAFE_DISPLAY_MASK.npy',np.where(mask,5,1).astype(np.uint8),allow_pickle=False)
    # Digital feature qualification is separate from printer-specific slicing.
    widths={}
    for name,a in [('exact',source),('print_safe',mask)]:
        lab,n=ndi.label(a);areas=np.bincount(lab.ravel())[1:];distance=ndi.distance_transform_edt(a)
        widths[name]={'4_connected_regions':n,'8_connected_regions':ndi.label(a,np.ones((3,3)))[1],
            'regions_under_3_pixels':int((areas<3).sum()),'smallest_region_area_px':int(areas.min()),
            'smallest_region_max_EDT_width_proxy_mm':float(min(2*distance[lab==i].max()-1 for i in range(1,n+1))*(160/256)),
            'single_pixel_pitch_mm':160/256,'one_pixel_edge_steps_remain':True,
            'interpretation':'Approximate pixel-center EDT proxy (2d-1)×pitch for each region maximum, not an exact inscribed disk or minimum neck; staircase ends may be omitted by a nozzle.'}
    validation={'created_utc':now(),'variants':records,'feature_diagnostics':widths,'actual_slicer_status':'NOT_RUN_YET',
        'physically_printed':False,'preview_from_actual_reimported_STL':True}
    write(ASSETS/'STL_VALIDATION.json',validation)
    write(ASSETS/'STL_SOURCE_MANIFEST.json',{'source_identity':'P3 supplied HorizontalFlip microscopy-derived categorical annotation',
        'source_path':str(original),'source_sha256':sha(original),'labels':{'1':'matrix backing representation','5':'provisional reinforcement raised representation'},
        'presentation_scale_not_microscopy_scale':True,'source_shape':[256,256],'field_mm':[160,160],'outer_mm':[168,168],
        'pixel_to_display_mm':.625,'base_mm':2.4,'relief_mm':1.2,'total_height_mm':3.6,
        'source_reinforcement_pixels':int(source.sum()),'print_reinforcement_pixels':int(mask.sum()),
        'source_fraction':float(source.mean()),'print_projected_fraction':float(mask.mean()),'changed_pixels':int((source!=mask).sum()),
        'removed_pixels':int((source&~mask).sum()),'added_pixels':int((~source&mask).sum()),
        'modifications':'3x3 square opening then closing, followed by explicitly recorded2x2 diagonal-contact unions; only the print copy changes',
        'topology_fix_sweeps':steps,'mesh_method':'One exposed two-height-field boundary surface, shared vertices, no internal faces/overlapping shells; optional coplanar simplification below1e-7mm nominal tolerance',
        'packages':{n:importlib.metadata.version(n) for n in ['trimesh','manifold3d','numpy','scipy']},
        'STL_files':{name:sha(ASSETS/name) for name in records},'STL_units':'STL is unitless; import coordinates as millimeters',
        'not_3D_reconstruction':True,'not_3D_FEM_specimen':True,'not_calibrated_or_physically_printed':True})
    preview(final,source,mask)
    print('STL EXPORT',[(name,r['passed'],r['faces']) for name,r in records.items()],'changedpixels',int((source!=mask).sum()),flush=True)

if __name__=='__main__':build()
