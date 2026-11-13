"""Full-domain two-solid P3 meshes and direct-displacement elastic APDL inputs."""
from pathlib import Path
import hashlib
import json
import numpy as np


def structured_mesh(labels, refinement=1, width=1., height=1.):
    a=np.asarray(labels)
    if a.ndim!=2 or a.dtype!=np.uint8 or not set(np.unique(a))<={1,5}:
        raise ValueError('Expected a 2D uint8 categorical solid array with labels1/5')
    if not a.size or refinement not in (1,2,3) or width<=0 or height<=0:
        raise ValueError('Invalid structured dimensions/refinement')
    source=a.copy();r,c=a.shape;k=refinement;ny,nx=r*k,c*k
    xx,yy=np.meshgrid(np.linspace(0,width,nx+1),np.linspace(0,height,ny+1))
    nodes=np.column_stack((xx.ravel(),yy.ravel()))
    ll=(np.arange(ny)[:,None]*(nx+1)+np.arange(nx)[None,:]).ravel()
    quads=np.column_stack((ll,ll+1,ll+nx+2,ll+nx+1))
    raw=np.flipud(np.repeat(np.repeat(source,k,axis=0),k,axis=1)).ravel()
    materials=np.where(raw==1,1,2).astype(np.int32)
    digest=hashlib.sha256()
    for x in [nodes.astype('<f8'),quads.astype('<i8'),materials.astype('<i4')]:digest.update(x.tobytes())
    return {'nodes':nodes,'quads':quads,'materials':materials,'source':source,
            'nx':nx,'ny':ny,'refinement':k,'width':width,'height':height,
            'bottom':np.arange(nx+1),'top':np.arange(ny*(nx+1),(ny+1)*(nx+1)),
            'left':np.arange(0,(nx+1)*(ny+1),nx+1),'right':np.arange(nx,(nx+1)*(ny+1),nx+1),
            'pin':0,'mesh_id':digest.hexdigest()}


def validate_mesh(m):
    n,q,mat=m['nodes'],m['quads'],m['materials'];nx,ny=m['nx'],m['ny']
    assert n.shape==((nx+1)*(ny+1),2) and q.shape==(nx*ny,4)
    assert len(np.unique(n,axis=0))==len(n)
    p=n[q];area=.5*np.sum(p[:,:,0]*np.roll(p[:,:,1],-1,axis=1)-p[:,:,1]*np.roll(p[:,:,0],-1,axis=1),axis=1)
    assert np.all(area>0) and np.allclose(area,m['width']*m['height']/len(q),rtol=1e-10,atol=1e-14)
    assert np.isclose(area.sum(),m['width']*m['height'])
    grid=q.reshape(ny,nx,4)
    assert np.array_equal(grid[:,:-1,1],grid[:,1:,0])
    assert np.array_equal(grid[:,:-1,2],grid[:,1:,3])
    assert np.array_equal(grid[:-1,:,3],grid[1:,:,0])
    assert np.array_equal(grid[:-1,:,2],grid[1:,:,1])
    expected=np.flipud(np.repeat(np.repeat(m['source'],m['refinement'],0),m['refinement'],1)).ravel()
    assert np.array_equal(mat,np.where(expected==1,1,2))
    interfaces=int(np.count_nonzero(mat.reshape(ny,nx)[:,:-1]!=mat.reshape(ny,nx)[:,1:])+np.count_nonzero(mat.reshape(ny,nx)[:-1]!=mat.reshape(ny,nx)[1:]))
    return {'passed':True,'nodes':len(n),'elements':len(q),'area_mm2':float(area.sum()),
            'minimum_element_area_mm2':float(area.min()),'positive_mappings':True,
            'material_elements':{str(k):int((mat==k).sum()) for k in [1,2]},
            'material_area_fractions':{str(k):float(area[mat==k].sum()/area.sum()) for k in [1,2]},
            'shared_material_interface_edges':interfaces,'all_adjacent_edges_share_nodes':True,
            'whole_domain_connected':True,'no_duplicate_nodes':True,'no_removed_pixels':True,
            'boundary_counts':{k:len(m[k]) for k in ['top','bottom','left','right']},
            'image_row0_at_top':True,'mesh_id':m['mesh_id']}


def write_mesh(m,path):
    """Native IDs are one-based; Python connectivity remains zero-based."""
    validate_mesh(m)
    with Path(path).open('w',encoding='ascii',newline='\n') as f:
        f.write('/PREP7\n/NOPR\n')
        for i,(x,y) in enumerate(m['nodes'],1):f.write(f'N,{i},{x:.17g},{y:.17g},0\n')
        current=None
        for i,(quad,material) in enumerate(zip(m['quads'],m['materials']),1):
            if material!=current:f.write(f'MAT,{material}\n');current=material
            f.write('EN,'+str(i)+','+','.join(str(int(v)+1) for v in quad)+'\n')
        for key,axis,value in [('BOTTOM','Y',0),('TOP','Y',m['height']),('LEFT','X',0),('RIGHT','X',m['width'])]:
            f.write(f'NSEL,S,LOC,{axis},{value:.17g}\nCM,{key},NODE\n')
        f.write('ALLSEL,ALL\n/GOPR\nFINISH\n')


def extraction_commands(m,steps):
    """Actual nodal reactions; ETABLE values stay associated with each element."""
    nn,ne=len(m['nodes']),len(m['quads']);top=m['top']+1;bottom=m['bottom']+1
    out=['/POST1','RSYS,0','ALLSEL,ALL','/OUTPUT,result_sets,txt','SET,LIST','/OUTPUT',
         'SET,LAST','*GET,NSETS,ACTIVE,0,SET,NSET','*GET,NNAT,NODE,0,COUNT','*GET,ENAT,ELEM,0,COUNT',
         '*CFOPEN,curve,csv',f'*DO,ISTEP,1,{len(steps)}','SET,ISTEP,1',
         '*GET,TNOW,ACTIVE,0,SET,TIME','ETABLE,ERAS','ETABLE,EENG,SENE','ETABLE,ELVOL,VOLU','SSUM',
         '*GET,TENG,SSUM,0,ITEM,EENG','*GET,TVOL,SSUM,0,ITEM,ELVOL',
         'FTOP=0','FBOT=0','UTMIN=1','UTMAX=-1','UBMAX=0',
         f'*DO,INODE,{int(top[0])},{int(top[-1])}',
         '*GET,FR,NODE,INODE,RF,FY','FTOP=FTOP+FR','*GET,UV,NODE,INODE,U,Y',
         'UTMIN=MIN(UTMIN,UV)','UTMAX=MAX(UTMAX,UV)','*ENDDO',
         f'*DO,INODE,{int(bottom[0])},{int(bottom[-1])}',
         '*GET,FR,NODE,INODE,RF,FY','FBOT=FBOT+FR','*GET,UV,NODE,INODE,U,Y','UBMAX=MAX(UBMAX,ABS(UV))','*ENDDO',
         f'*GET,FPIN,NODE,{m["pin"]+1},RF,FX',
         '*VWRITE,ISTEP,TNOW,UTMIN,UTMAX,UBMAX,FTOP,FBOT,FPIN,TENG,TVOL,NNAT,ENAT',
         "(F8.0,11(',',E24.16))",'*ENDDO','*CFCLOS','SET,LAST']
    out += [f'*DIM,NIDS,ARRAY,{nn}',f'*DIM,NVAL,ARRAY,{nn},4','*VFILL,NIDS(1),RAMP,1,1']
    for col,item,comp in [(1,'LOC','X'),(2,'LOC','Y'),(3,'U','X'),(4,'U','Y')]:
        out += [f'*VGET,NVAL(1,{col}),NODE,1,{item},{comp}']
    out += ['*CFOPEN,nodes,csv','*VWRITE,NIDS(1),NVAL(1,1),NVAL(1,2),NVAL(1,3),NVAL(1,4)',
            "(F12.0,4(',',E24.16))",'*CFCLOS','*DEL,NIDS','*DEL,NVAL']
    fields=[('SXX','S','X'),('SYY','S','Y'),('SXY','S','XY'),('SEQ','S','EQV'),
            ('EXX','EPEL','X'),('EYY','EPEL','Y'),('GXY','EPEL','XY'),('SZZ','S','Z'),('ENER','SENE',''),('EVOL','VOLU','')]
    out += ['ETABLE,ERAS',f'*DIM,EIDS,ARRAY,{ne}',f'*DIM,EVAL,ARRAY,{ne},11','*VFILL,EIDS(1),RAMP,1,1',
            '*VGET,EVAL(1,1),ELEM,1,ATTR,MAT']
    for col,(lab,item,comp) in enumerate(fields,2):
        out += [f'ETABLE,{lab},{item},{comp}',f'*VGET,EVAL(1,{col}),ELEM,1,ETAB,{lab}']
    out += ['*CFOPEN,fields,csv','*VWRITE,EIDS(1),'+','.join(f'EVAL(1,{c})' for c in range(1,12)),
            "(F12.0,11(',',E24.16))",'*CFCLOS','*DEL,EIDS','*DEL,EVAL',
            '*CFOPEN,native_counts,csv','*VWRITE,NSETS,NNAT,ENAT',"(3(F16.0,','))",'*CFCLOS','FINISH']
    return out


def source_input(m,materials,steps,thickness=1.):
    lines=['/BATCH','/CLEAR,START','/FILNAME,elastic','/PREP7','ET,1,PLANE182',
           'KEYOPT,1,1,0','KEYOPT,1,3,3','KEYOPT,1,6,0',f'R,1,{thickness:.17g}','TYPE,1','REAL,1']
    for mid,p in materials.items():lines += [f'MP,EX,{mid},{p["E_MPa"]:.17g}',f'MP,PRXY,{mid},{p["nu"]:.17g}']
    lines += ['FINISH',"/INPUT,mesh,inp",'/PREP7','D,BOTTOM,UY,0','D,TOP,UY,0',f'D,{m["pin"]+1},UX,0',
              '/OUTPUT,inventory,txt','ETLIST,ALL','RLIST,ALL','MPLIST,ALL','DLIST,ALL','CHECK','/OUTPUT','FINISH',
              '/SOLU','ANTYPE,STATIC,NEW','NLGEOM,OFF','EQSLV,SPARSE','AUTOTS,OFF','NSUBST,1,1,1','KBC,1','OUTRES,ALL,ALL','OUTPR,ALL,NONE']
    for strain in steps:lines += [f'TIME,{strain:.17g}',f'D,TOP,UY,{-strain*m["height"]:.17g}','SOLVE']
    lines += ['FINISH','SAVE,model,db']+extraction_commands(m,steps)+['/EXIT,NOSAVE']
    return '\n'.join(lines)+'\n'


def readonly_input(m,steps,source):
    source=Path(source).resolve().as_posix()
    if "'" in source:raise ValueError('Unsupported APDL quote in source path')
    return '\n'.join(['/BATCH','/CLEAR,START',f"RESUME,'{source}/model',db",'/POST1',
                     f"FILE,'{source}/elastic',rst"]+extraction_commands(m,steps)+['/EXIT,NOSAVE'])+'\n'
