"""Quantify the original terminal near-touch without claiming local gap equality."""
import argparse
import numpy as np
from shapely.geometry import LineString

from metamaterial_eval.simulation.quadratic_separation import certify_separated
from scripts.v067_qualify_fixture import table
from scripts.v068_common import BASE,RUN,read,write_json,file_hash


PAIRS=[(27837,28505),(27838,28504)]


def arc(edge):
    a,b,m=edge;t=np.linspace(0,1,1001)[:,None]
    return (1-t)*(1-2*t)*a+t*(2*t-1)*b+4*t*(1-t)*m


def measure(label):
    fixture=BASE/'track_A_expanded_fixture_001'
    with np.load(fixture/'mesh.npz',allow_pickle=False) as z:
        xy=z['nodes'];boundary=z['boundary'];original=z['original_boundary_indices']
    parent=np.load(fixture/'measured_displacements.npy',mmap_mode='r')[14]
    post=BASE/(label+'_post1_002');p=read(post/'simulation_manifest.json')
    state=next(s for s in p['states'] if s['load_step']==15)
    u=table(post/(state['prefix']+'_displacements.csv'),3)
    if len(u)!=len(xy):raise ValueError('Incomplete local terminal field')
    results=[]
    for one,two in PAIRS:
        i,j=[int(np.flatnonzero(original==k)[0]) for k in [one,two]]
        endpoints=[]
        for vertices in [xy+parent,xy+u[:,1:3]]:
            a,b=vertices[boundary[i]],vertices[boundary[j]]
            proof=certify_separated(a,b)
            sampled=float(LineString(arc(a)).distance(LineString(arc(b))))
            endpoints.append({'certified_separated':proof['passed'],
                              'certified_lower_bound_mm':proof['minimum_certified_separation_mm'],
                              'sampled_1000_segment_distance_mm':sampled,
                              'proof_processed_cells':proof['processed_cells']})
        results.append({'original_boundary_indices':[one,two],
                        'original_local_face_indices':[i,j],
                        'parent':endpoints[0],'local':endpoints[1],
                        'signed_local_minus_parent_sampled_distance_mm':
                            endpoints[1]['sampled_1000_segment_distance_mm']-endpoints[0]['sampled_1000_segment_distance_mm']})
    result={'schema':'young-dawgs-v068-original-terminal-nanogap-comparison',
            'label':label,'state':state,
            'parent_displacement_sha256':file_hash(fixture/'measured_displacements.npy'),
            'native_local_field_sha256':file_hash(post/(state['prefix']+'_displacements.csv')),
            'pairs':results,
            'interpretation':'Signed local minus parent sampled geometric distance, not a rigorous signed physical gap. Certified lower bounds separately prove separation only when positive; failure to certify is not alone an intersection proof. No local-to-full nanogap equality is inferred.'}
    write_json(RUN/'track_A_local_fixture'/(label+'_nanogap.json'),result)
    print(label,[(r['parent']['sampled_1000_segment_distance_mm'],
                  r['local']['sampled_1000_segment_distance_mm'],
                  r['signed_local_minus_parent_sampled_distance_mm']) for r in results],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');measure(p.parse_args().label)
