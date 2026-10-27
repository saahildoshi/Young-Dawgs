"""Actual saved-mesh defect diagnosis; no source repair or solver inference."""
from pathlib import Path
import time
import numpy as np
import shapely
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from .mesh_generation import Mesh
from .element_quality import corner_metrics,quadratic_mapping,quality_summary,cross
from .reporting import write_json,mesh_hash


def load_mesh(path):
    with np.load(path,allow_pickle=False) as z:
        return Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])


def source_segments(geometry):
    rings=[geometry.exterior,*geometry.interiors]
    segments=np.concatenate([np.stack([np.asarray(r.coords)[:-1],np.asarray(r.coords)[1:]],axis=1) for r in rings])
    owners=np.concatenate([np.full(len(r.coords)-1,i) for i,r in enumerate(rings)])
    local=np.concatenate([np.arange(len(r.coords)-1) for r in rings])
    return segments,owners,local


def source_corner_angles(geometry):
    angles=[]
    for ring in [geometry.exterior,*geometry.interiors]:
        p=np.asarray(ring.coords)[:-1];a=p-np.roll(p,1,axis=0);b=np.roll(p,-1,axis=0)-p
        angles.extend((180-np.degrees(np.arctan2(cross(a,b),np.sum(a*b,axis=1)))).tolist())
    return np.asarray(angles)


def diagnose(mesh,geometry,provenance,config,output):
    output=Path(output)
    if output.exists():raise FileExistsError(f'Refusing to overwrite diagnosis {output}')
    output.mkdir(parents=True);started=time.perf_counter()
    points=mesh.nodes[mesh.triangles[:,:3]]
    corners=corner_metrics(points);mapping=quadratic_mapping(mesh.nodes[mesh.triangles])
    failed=np.flatnonzero(corners['minimum_angle_deg']<10)
    boundary_nodes=set(map(int,mesh.boundary.ravel()))
    boundary_edges={tuple(sorted(e[:2])) for e in mesh.boundary}
    segments,owners,local=source_segments(geometry);lines=shapely.linestrings(segments)
    tree=shapely.STRtree(lines);pore_tree=shapely.STRtree(lines[owners>0])
    polys=shapely.polygons(points[failed]);centers=points[failed].mean(axis=1)
    nearest=tree.nearest(polys);nearest_pore=pore_tree.nearest(polys)
    distance=shapely.distance(polys,lines[nearest]);pore_distance=shapely.distance(polys,lines[owners>0][nearest_pore])
    probes=[]
    for p in provenance['source_only_solid_probes']:
        a=np.array(p['xy'],float);b=a.copy();a[p['axis']]-=p['source_pixel_run']/2;b[p['axis']]+=p['source_pixel_run']/2
        coords=np.array([a,b]);coords[:,0]*=config.width/1024;coords[:,1]=config.height-coords[:,1]*config.height/1024
        probes.append(shapely.LineString(coords))
    probe_tree=shapely.STRtree(probes);probe_nearest=probe_tree.nearest(polys)
    probe_distance=shapely.distance(polys,np.asarray(probes,dtype=object)[probe_nearest])
    flat=mesh.triangles[:,:3].ravel();sort=np.argsort(flat);ordered=flat[sort]
    records=[]
    for index,eid in enumerate(failed):
        tri=mesh.triangles[eid];neighbors=set()
        for node in tri[:3]:
            ids=sort[np.searchsorted(ordered,node,'left'):np.searchsorted(ordered,node,'right')]//3
            neighbors.update(map(int,ids))
        neighbors.discard(int(eid));edge_neighbors=[i for i in sorted(neighbors) if len(set(map(int,tri[:3]))&set(map(int,mesh.triangles[i,:3])))>=2]
        actual_edges=[tuple(sorted([int(tri[a]),int(tri[b])])) for a,b in [(0,1),(1,2),(2,0)]]
        incidence=sum(int(n) in boundary_nodes for n in tri[:3]);boundary_count=sum(e in boundary_edges for e in actual_edges)
        records.append({'element_zero_based':int(eid),'element_one_based':int(eid)+1,'type':'TRI6',
            'corner_ids_zero_based':tri[:3].tolist(),'midside_ids_zero_based':tri[3:].tolist(),
            'coordinates_mm':mesh.nodes[tri].tolist(),'angles_deg':corners['angles_deg'][eid].tolist(),
            'minimum_angle_deg':float(corners['minimum_angle_deg'][eid]),'signed_area_mm2':float(corners['signed_area'][eid]),
            'quadratic_determinant_min':float(mapping['determinant_min'][eid]),
            'quadratic_positive':bool(mapping['positive_over_reference_triangle'][eid]),
            'midpoint_error_mm':float(mapping['max_midpoint_error'][eid]),'boundary_corner_count':int(incidence),
            'boundary_edge_count':int(boundary_count),'location':'boundary_edge' if boundary_count else 'boundary_vertex' if incidence else 'interior_vertices',
            'source_boundary_distance_mm':float(distance[index]),'pore_boundary_distance_mm':float(pore_distance[index]),
            'nearest_source_entity':{'ring':int(owners[nearest[index]]),'segment':int(local[nearest[index]])},
            'nearest_sampled_narrow_feature_distance_mm':float(probe_distance[index]),
            'nearest_sampled_feature':provenance['source_only_solid_probes'][int(probe_nearest[index])],
            'feature_distance_limitation':'distance to registered finite axial chord, not an exhaustive nearest-neck distance',
            'edge_neighbors':[{'element_zero_based':i,'min_angle_deg':float(corners['minimum_angle_deg'][i]),'quality':float(corners['quality'][i])} for i in edge_neighbors],
            'one_ring_elements':sorted(neighbors)})
    pairs=cKDTree(centers).query_pairs(.1,output_type='ndarray') if len(failed) else np.empty((0,2),int)
    graph=coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(failed),len(failed)))
    clusters=connected_components(graph,directed=False,return_labels=False) if len(failed) else 0
    ga=source_corner_angles(geometry)
    report={**quality_summary(corners,mapping),'mesh_sha256':mesh_hash(mesh),'failed_fraction':len(failed)/len(mesh.triangles),
            'failed_elements':records,'spatial_clusters':int(clusters),'cluster_distance_mm':.1,
            'source_minimum_solid_boundary_angle_deg':float(ga.min()),
            'root_cause':'MESH_INDUCED_INTERIOR_LAYOUT_AND_BOUNDARY_DISCRETIZATION_SIZE_IMBALANCE',
            'geometry_forced_below_10_degrees':bool(np.any(ga<10)),
            'boundary_failure_count':sum(r['boundary_edge_count']>0 for r in records),
            'interior_vertex_failure_count':sum(r['boundary_corner_count']==0 for r in records),
            'source_unchanged':True,'seconds':time.perf_counter()-started,
            'gmsh_entity_note':'historical NPZ does not retain Gmsh curve IDs; ring/segment ownership is recovered from authenticated geometry'}
    write_json(output/'diagnosis.json',report)
    worst=int(failed[np.argmin(corners['minimum_angle_deg'][failed])])
    write_json(output/'worst_TRI6_fixture.json',{'source_mesh_sha256':report['mesh_sha256'],
               'element_zero_based':worst,'coordinates_mm':mesh.nodes[mesh.triangles[worst]].tolist(),
               'minimum_angle_deg':float(corners['minimum_angle_deg'][worst])})
    diagnostic_figures(mesh,geometry,corners,mapping,records,output/'figures')
    return report


def diagnostic_figures(mesh,geometry,corners,mapping,records,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection,LineCollection
    output=Path(output);output.mkdir()
    xy=mesh.nodes[mesh.triangles[:,:3]]
    fig,ax=plt.subplots(figsize=(7,7))
    ax.add_collection(LineCollection([np.asarray(r.coords) for r in [geometry.exterior,*geometry.interiors]],colors='#c1c7cc',linewidths=.25))
    ids=[r['element_zero_based'] for r in records]
    ax.scatter(xy[ids].mean(axis=1)[:,0],xy[ids].mean(axis=1)[:,1],s=25,c=corners['minimum_angle_deg'][ids],cmap='autumn_r',vmin=8,vmax=10)
    ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',title=f'Original fine mesh: {len(ids)} actual triangles below10°',xlabel='x [mm]',ylabel='y [mm]')
    fig.tight_layout();fig.savefig(output/'low_angle_map.png',dpi=160);plt.close(fig)
    worst=min(records,key=lambda r:r['minimum_angle_deg'])
    for name,r in [('worst_element',worst),('boundary_size_imbalance',next(r for r in records if r['boundary_edge_count']==2))]:
        point=xy[r['element_zero_based']].mean(axis=0);radius=.04
        selected=np.any(np.linalg.norm(xy-point,axis=2)<radius,axis=1)
        fig,ax=plt.subplots(figsize=(7,6));ax.add_collection(PolyCollection(xy[selected],facecolors='none',edgecolors='#64849a',linewidths=.6))
        ax.add_collection(PolyCollection(xy[[r['element_zero_based']]],facecolors='#efb499',edgecolors='#b74425'))
        ax.add_collection(LineCollection([np.asarray(ring.coords) for ring in [geometry.exterior,*geometry.interiors]],colors='#222222',linewidths=1))
        coords=np.asarray(r['coordinates_mm']);ax.scatter(coords[:3,0],coords[:3,1],c='#264766',marker='o',s=24,label='corner nodes')
        ax.scatter(coords[3:,0],coords[3:,1],c='#b63131',marker='x',s=34,label='midside nodes')
        for k,(x,y) in enumerate(coords):ax.annotate(str(k+1),(x,y),xytext=(3,3),textcoords='offset points')
        ax.set(xlim=(point[0]-radius,point[0]+radius),ylim=(point[1]-radius,point[1]+radius),aspect='equal',xlabel='x [mm]',ylabel='y [mm]',title=f'Original TRI6 #{r["element_one_based"]}: {r["minimum_angle_deg"]:.4f}°; geometry overlay')
        ax.legend();fig.tight_layout();fig.savefig(output/(name+'.png'),dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    axes[0].hist(corners['minimum_angle_deg'],bins=60);axes[0].axvline(10,c='r');axes[0].set(xlabel='Minimum corner angle [deg]',ylabel='Count')
    axes[1].hist(corners['quality'],bins=60);axes[1].set(xlabel='Corner quality',ylabel='Count')
    axes[2].hist(mapping['determinant_min'],bins=60);axes[2].set(xlabel='Whole-element minimum detJ [mm²]',ylabel='Count')
    fig.suptitle('Actual original fine mesh: corner shape and separate quadratic mapping');fig.tight_layout();fig.savefig(output/'quality_distributions.png',dpi=160);plt.close(fig)
