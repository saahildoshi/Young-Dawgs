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


def overlay(stream,mesh,owners,indices,etype,real):
    stream.write(f'TYPE,{etype}\nREAL,{real}\nMAT,1\n')
    for index in indices:
        a,b,mid=(mesh.boundary[index]+1).tolist();owner=int(owners[index])
        stream.write('ALLSEL,ALL\n'+f'ESEL,S,ELEM,,{owner}\nNSEL,NONE\n'
                     f'NSEL,A,NODE,,{a}\nNSEL,A,NODE,,{b}\nNSEL,A,NODE,,{mid}\n'
                     f'TYPE,{etype}\nREAL,{real}\nMAT,1\nESURF\n')
    stream.write('ALLSEL,ALL\n')
