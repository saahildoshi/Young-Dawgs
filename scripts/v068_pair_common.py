"""Exact original-face to native structural-element overlay helpers."""
import numpy as np


def face_owners(mesh):
    by_corner={}
    for eid,t in enumerate(mesh.triangles,1):
        for a,b in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])]:
            key=tuple(sorted((int(a),int(b))))
            by_corner.setdefault(key,[]).append(eid)
    owners=[]
    for face in mesh.boundary:
        key=tuple(sorted((int(face[0]),int(face[1]))))
        matches=by_corner.get(key,[])
        if len(matches)!=1:raise ValueError('Non-unique boundary structural owner')
        owners.append(matches[0])
    return np.asarray(owners,dtype=np.int64)


def native_skin_ids_by_face(mesh,native_rows):
    """Map oriented original boundary faces to native GC skin IDs, independent of EID order."""
    rows=np.asarray(native_rows)
    if rows.ndim!=2 or rows.shape[1]<4 or len(rows)!=len(mesh.boundary):
        raise ValueError('Incomplete native original-face inventory')
    lookup={tuple(row[1:4].astype(int)):int(row[0]) for row in rows}
    if len(lookup)!=len(rows) or len(set(lookup.values()))!=len(rows):
        raise ValueError('Duplicate native original face or skin ID')
    try:return np.asarray([lookup[tuple((face+1).tolist())] for face in mesh.boundary],dtype=np.int64)
    except KeyError as exc:raise ValueError('Original face missing native GC skin') from exc


def overlay(stream,mesh,owners,indices,etype,real):
    stream.write(f'TYPE,{etype}\nREAL,{real}\nMAT,1\n')
    for index in indices:
        a,b,mid=(mesh.boundary[index]+1).tolist();owner=int(owners[index])
        stream.write('ALLSEL,ALL\n'+f'ESEL,S,ELEM,,{owner}\nNSEL,NONE\n'
                     f'NSEL,A,NODE,,{a}\nNSEL,A,NODE,,{b}\nNSEL,A,NODE,,{mid}\n'
                     f'TYPE,{etype}\nREAL,{real}\nMAT,1\nESURF\n')
    stream.write('ALLSEL,ALL\n')
