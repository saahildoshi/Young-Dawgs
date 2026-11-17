"""Additive F1 plane-stress mesh: native0/1 solids; native2 is absent continuum."""
import hashlib
from pathlib import Path
import re
import numpy as np
from scipy import ndimage as ndi
from .composite_elastic import structured_mesh,extraction_commands,readonly_input

def solid_mesh(labels,k=1):
    a=np.asarray(labels)
    if a.ndim!=2 or a.dtype!=np.uint8 or not set(np.unique(a))<={0,1,2}:raise ValueError('Expected native0/1/2 uint8')
    if k not in (1,2):raise ValueError('F1 refinement must be1 or2')
    comp,n=ndi.label(a!=2);n8=ndi.label(a!=2,np.ones((3,3)))[1]
    if n!=n8:raise ValueError('Unsupported solid components joined only at pixel corners; original retained')
    full=structured_mesh(np.where(a==1,5,1).astype(np.uint8),k)
    raw=np.flipud(np.repeat(np.repeat(a,k,0),k,1)).ravel();keep=raw!=2
    component=np.flipud(np.repeat(np.repeat(comp,k,0),k,1)).ravel()[keep]
    q=full['quads'][keep];used,inverse=np.unique(q,return_inverse=True);nodes=full['nodes'][used];quads=inverse.reshape(-1,4)
    m={**full,'nodes':nodes,'quads':quads,'materials':np.where(raw[keep]==0,1,2).astype(np.int32),
        'source':a.copy(),'element_component':component,'original_grid_node_ids':used,'solid_components':n,'pins':[]}
    for key,axis,value in [('bottom',1,0.),('top',1,1.),('left',0,0.),('right',0,1.)]:
        m[key]=np.flatnonzero(np.isclose(nodes[:,axis],value,atol=1e-14,rtol=0))
    for index in range(1,n+1):
        vertices=np.unique(quads[component==index]);bottom=np.intersect1d(vertices,m['bottom']);top=np.intersect1d(vertices,m['top'])
        if not len(bottom) or not len(top):raise ValueError(f'Solid component{index} does not reach both prescribed boundaries; no hidden island restraint/removal')
        m['pins'].append(int(bottom[np.argmin(nodes[bottom,0])]))
    m['pin']=m['pins'][0]
    digest=hashlib.sha256()
    for array in [nodes.astype('<f8'),quads.astype('<i8'),m['materials'].astype('<i4')]:digest.update(array.tobytes())
    m['mesh_id']=digest.hexdigest();return m

def validate_solid_mesh(m):
    n,q,mat=m['nodes'],m['quads'],m['materials'];a=m['source'];k=m['refinement']
    assert len(q)==int((a!=2).sum())*k*k
    assert len(np.unique(q))==len(n) and len(np.unique(n,axis=0))==len(n)
    xyz=n[q];area=.5*np.sum(xyz[:,:,0]*np.roll(xyz[:,:,1],-1,axis=1)-xyz[:,:,1]*np.roll(xyz[:,:,0],-1,axis=1),axis=1)
    assert np.all(area>0) and np.allclose(area,1/(a.size*k*k),atol=1e-14,rtol=1e-10)
    raw=np.flipud(np.repeat(np.repeat(a,k,0),k,1)).ravel();expected=np.where(raw[raw!=2]==0,1,2)
    assert np.array_equal(mat,expected)
    edges=np.sort(np.vstack([q[:,[0,1]],q[:,[1,2]],q[:,[2,3]],q[:,[3,0]]]),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True);assert np.all(counts<=2)
    free=unique[counts==1];xy=n[free];outer=np.any(np.all(np.isclose(xy,0,atol=1e-14)|np.isclose(xy,1,atol=1e-14),axis=1),axis=1)
    # Correct outer edge: both nodes lie on the SAME x or y envelope side.
    outer=np.any(np.all(np.isclose(xy,0,atol=1e-14),axis=1)|np.all(np.isclose(xy,1,atol=1e-14),axis=1),axis=1)
    return {'passed':True,'nodes':len(n),'elements':len(q),'solid_area_mm2':float(area.sum()),'envelope_area_mm2':1.,
        'void_area_mm2':float((a==2).mean()),'source_phase_counts':{str(v):int((a==v).sum()) for v in [0,1,2]},
        'material_elements':{str(v):int((mat==v).sum()) for v in [1,2]},
        'material_envelope_area_fractions':{str(v):float(area[mat==v].sum()) for v in [1,2]},
        'material_solid_area_fractions':{str(v):float(area[mat==v].sum()/area.sum()) for v in [1,2]},
        'free_void_edges':int((~outer).sum()),'outer_boundary_edges':int(outer.sum()),'solid_components':m['solid_components'],
        'pins':m['pins'],'no_void_elements':True,'no_unused_nodes':True,'image_row0_at_top':True,'shared_solid_interfaces':True,'mesh_id':m['mesh_id']}

def write_solid_mesh(m,path):
    validate_solid_mesh(m)
    with Path(path).open('w',encoding='ascii',newline='\n') as f:
        f.write('/PREP7\n/NOPR\n')
        for i,(x,y) in enumerate(m['nodes'],1):f.write(f'N,{i},{x:.17g},{y:.17g},0\n')
        material=None
        for i,(quad,mid) in enumerate(zip(m['quads'],m['materials']),1):
            if mid!=material:f.write(f'MAT,{mid}\n');material=mid
            f.write('EN,'+str(i)+','+','.join(str(int(v)+1) for v in quad)+'\n')
        for key in ['bottom','top','left','right']:
            f.write('NSEL,NONE\n')
            for node in m[key]:f.write(f'NSEL,A,NODE,,{int(node)+1}\n')
            f.write(f'CM,{key.upper()},NODE\n')
        f.write('ALLSEL,ALL\n/GOPR\nFINISH\n')

def extract_solid(m,steps):
    out=extraction_commands(m,steps)
    for boundary in ['top','bottom']:
        ids=m[boundary]+1;begin=out.index(f'*DO,INODE,{int(ids[0])},{int(ids[-1])}')
        end=out.index('*ENDDO',begin)
        out[begin:end+1]=[f'CMSEL,S,{boundary.upper()}','*GET,BCN,NODE,0,COUNT','*GET,INODE,NODE,0,NUM,MIN','*DO,IBC,1,BCN']+out[begin+1:end]+['INODE=NDNEXT(INODE)','*ENDDO','ALLSEL,ALL']
    old=f'*GET,FPIN,NODE,{m["pin"]+1},RF,FX';idx=out.index(old)
    out[idx:idx+1]=['FPIN=0']+[line for node in m['pins'] for line in [f'*GET,FXONE,NODE,{node+1},RF,FX','FPIN=FPIN+FXONE']]
    return out

def source_solid(m,materials,steps):
    lines=['/BATCH','/CLEAR,START','/FILNAME,elastic','/PREP7','ET,1,PLANE182','KEYOPT,1,1,0','KEYOPT,1,3,3','KEYOPT,1,6,0','R,1,1','TYPE,1','REAL,1']
    for mid,p in materials.items():lines +=[f'MP,EX,{mid},{p["E_MPa"]:.17g}',f'MP,PRXY,{mid},{p["nu"]:.17g}']
    lines+=['FINISH','/INPUT,mesh,inp','/PREP7','D,BOTTOM,UY,0','D,TOP,UY,0']+[f'D,{node+1},UX,0' for node in m['pins']]
    lines+=['/OUTPUT,inventory,txt','ETLIST,ALL','RLIST,ALL','MPLIST,ALL','DLIST,ALL','CHECK','/OUTPUT','FINISH','/SOLU','ANTYPE,STATIC,NEW','NLGEOM,OFF','EQSLV,SPARSE','AUTOTS,OFF','NSUBST,1,1,1','KBC,1','OUTRES,ALL,ALL','OUTPR,ALL,NONE']
    for strain in steps:lines +=[f'TIME,{strain:.17g}',f'D,TOP,UY,{-strain:.17g}','SOLVE']
    return '\n'.join(lines+['FINISH','SAVE,model,db']+extract_solid(m,steps)+['/EXIT,NOSAVE'])+'\n'

def reopen_solid(m,steps,source):
    source=Path(source).resolve().as_posix()
    if "'" in source:raise ValueError('Unsupported path quote')
    return '\n'.join(['/BATCH','/CLEAR,START',f"RESUME,'{source}/model',db",'/POST1',f"FILE,'{source}/elastic',rst"]+extract_solid(m,steps)+['/EXIT,NOSAVE'])+'\n'

def constraints_solid(text,m):
    rows=re.findall(r'^\s*(\d+)\s+(UX|UY)\s+([+\-\d.Ee]+)',text,re.M)
    actual={(int(n),axis) for n,axis,v in rows}
    expected={(int(n)+1,'UY') for side in ['top','bottom'] for n in m[side]}|{(n+1,'UX') for n in m['pins']}
    return {'passed':actual==expected and len(rows)==len(expected),'actual':len(rows),'expected':len(expected),'unexpected':sorted(actual-expected),'missing':sorted(expected-actual)}
