"""Explicit external contact inventory; internal self-contact is fail-closed."""
import numpy as np


def platen_plan(mesh, config):
    plan={}
    for group, normal in [('top',[0,-1]),('bottom',[0,1])]:
        edges=mesh.boundary[mesh.boundary_groups==group]
        if not len(edges):raise ValueError(f'Missing {group} platen contact boundary')
        xy=mesh.nodes[edges[:,:2]]
        y=config.height if group=='top' else 0
        if not np.allclose(xy[:,:,1],y,atol=1e-8,rtol=0):
            raise ValueError('Contact group contains off-platen faces')
        solid_normals=np.column_stack((xy[:,1,1]-xy[:,0,1],xy[:,0,0]-xy[:,1,0]))
        expected=[0,1] if group=='top' else [0,-1]
        if np.any(solid_normals@np.asarray(expected)<=0):
            raise ValueError('Specimen contact normal faces inward')
        plan[group]={'edges':edges.tolist(),'nodes':np.unique(edges).tolist(),
                     'target_normal':normal,'initial_gap_mm':0.0,
                     'friction_mu':0.0,'bonded':False,'algorithm':'augmented_Lagrange',
                     'contact_element':'CONTA172','target_element':'TARGE169',
                     'normal_verification':'geometric_only_ANSYS_pending'}
    plan['internal_self_contact']={'status':'UNQUALIFIED_NOT_CONFIGURED',
        'reason':'No installed ANSYS release or engagement benchmark; adjacent continuum faces must never be paired automatically',
        'blocks':['advanced_compression','internal_contact_comparison','research_readiness']}
    return plan


def require_internal_contact(evidence):
    if evidence.get('status')!='SOLVER_VERIFIED' or not evidence.get('nonadjacent_only') or not evidence.get('engaged_in_benchmark'):
        raise RuntimeError('Internal self-contact requires actual nonadjacent-surface engagement evidence')
