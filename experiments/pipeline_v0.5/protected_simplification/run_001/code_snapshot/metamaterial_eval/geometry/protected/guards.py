"""Prospective dense risk detection and tolerance-influenced exact guards."""
import time
import numpy as np
import shapely
from shapely import box, STRtree
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from ..sensitivity.features import prepare_features
from .model import BoundaryModel


def prepare_risks(fixture, config, features=None):
    started = time.perf_counter()
    model = BoundaryModel(fixture['baseline'])
    features = features if features is not None else prepare_features(fixture, config['b1_config'])
    mask = fixture['mask']; sk = skeletonize(mask.astype(bool)); edt = ndi.distance_transform_edt(mask)
    degree = ndi.convolve(sk.astype(np.int16), np.ones((3,3), dtype=np.int16))-sk
    dense = []
    for kind, selected in [('narrow_edt', sk & (2*edt <= config['guards']['narrow_edt_diameter'])),
                           ('junction', sk & (degree >= config['guards']['junction_degree_min']))]:
        labels, count = ndi.label(selected, structure=np.ones((3,3)))
        for i, sl in enumerate(ndi.find_objects(labels), 1):
            if sl is None:
                continue
            points = np.argwhere(labels[sl] == i) + [sl[0].start, sl[1].start]
            radii = edt[points[:,0], points[:,1]]
            dense.append({'feature_id':f'{kind}_{i:05d}', 'kind':kind,
                          'source_yx':points.tolist(), 'radii':radii.tolist(),
                          'minimum_edt_diameter':float(2*radii.min()),
                          'interpretation':'Raster EDT diameter at skeleton support, not a proven minimum load-bearing width.'})
    pairs = model.tree.query(model.lines, predicate='dwithin', distance=config['guards']['risk_pair_distance'])
    a, b = pairs
    keep = a < b; a, b = a[keep], b[keep]
    same = model.owner[a] == model.owner[b]
    sizes = np.diff(model.offsets)[model.owner[a]]
    sep = np.abs(model.local_index[a]-model.local_index[b]); sep = np.minimum(sep, sizes-sep)
    directions = model.segments[:,1]-model.segments[:,0]
    cosine = np.sum(directions[a]*directions[b],axis=1)/(np.linalg.norm(directions[a],axis=1)*np.linalg.norm(directions[b],axis=1))
    # Opposing sides of a short U-shaped opening can be only two segment
    # indices apart. Index separation alone misses such exterior channels.
    opposed = cosine <= config['guards']['same_ring_opposed_cosine']
    keep = ~same | (sep >= config['guards']['same_ring_index_separation']) | ((sep>1)&opposed)
    close = []
    for i, j in sorted(zip(a[keep].tolist(), b[keep].tolist())):
        xy = model.segments[[i,j]].reshape(-1,2)
        close.append({'feature_id':f'proximity_{i:06d}_{j:06d}', 'kind':'boundary_proximity',
                      'source_segments':[i,j], 'support_bounds':[float(xy[:,0].min()),float(xy[:,1].min()),float(xy[:,0].max()),float(xy[:,1].max())],
                      'baseline_separation':float(model.lines[i].distance(model.lines[j])),
                      'interpretation':'Nonadjacent boundary separation; phase/corridor width is not inferred from this alone.'})
    return {'model':model, 'features':features, 'dense':dense, 'proximity':close,
            'feature_detection_seconds':time.perf_counter()-started}


def build_guards(risks, epsilon, config, resolution=1024):
    started = time.perf_counter(); records = []; domain = box(0,0,resolution,resolution)
    margin = epsilon + config['guards']['influence_margin']
    def add(identifier, kind, shape, **data):
        shape = shape.intersection(domain)
        if not shape.is_empty:
            records.append({'guard_id':identifier, 'kind':kind, 'geometry':shape,
                            'bounds':list(shape.bounds), 'influence_tolerance':epsilon, **data})
    for p in risks['features']['repairs']:
        x,y = p['xy']; h = p['L1_radius']+config['guards']['repair_margin']+epsilon
        add('repair_'+p['contact_id'], 'repair', box(x-h,y-h,x+h,y+h),
            repair_id=p['contact_id'], source_xy=p['xy'], L1_radius=p['L1_radius'],
            baseline_clearance=p['baseline_recorded_clearance'])
    for p in risks['features']['natural_neck_probes']:
        xy = np.asarray(p['baseline_chord']['segment_xy']+p['solid_anchors_xy'])
        bounds = np.asarray(p['roi_bounds'])
        lo = np.minimum(bounds[:2], xy.min(axis=0)); hi = np.maximum(bounds[2:], xy.max(axis=0))
        add(p['probe_id'], 'normal_chord', box(*(lo-margin), *(hi+margin)),
            source_xy=p['center_xy'], baseline_width=p['baseline_chord']['width'])
    for i,p in enumerate(risks['features']['saved_boundary_necks']):
        bounds = np.asarray(p['roi_bounds']); add(f'saved_connector_{i:03d}', 'saved_connector',
            box(*(bounds[:2]-margin), *(bounds[2:]+margin)), baseline_depths=p['baseline_depths'])
    for p in risks['dense']:
        yx = np.asarray(p['source_yx']); centers = yx[:,::-1]+.5
        h = np.asarray(p['radii'])+margin
        boxes = shapely.box(centers[:,0]-h, centers[:,1]-h, centers[:,0]+h, centers[:,1]+h)
        add(p['feature_id'], p['kind'], shapely.union_all(boxes), source_yx=p['source_yx'],
            baseline_edt_diameters=(2*np.asarray(p['radii'])).tolist(), minimum_edt_diameter=p['minimum_edt_diameter'])
    for p in risks['proximity']:
        bounds = np.asarray(p['support_bounds'])
        add(p['feature_id'], p['kind'], box(*(bounds[:2]-margin), *(bounds[2:]+margin)),
            source_segments=p['source_segments'], baseline_separation=p['baseline_separation'])
    shapes = [r['geometry'] for r in records]; tree = STRtree(shapes)
    model = risks['model']; protected = np.zeros(len(model.lines),dtype=bool)
    memberships = [[] for _ in records]
    if records:
        hits = tree.query(model.lines, predicate='intersects')
        protected[hits[0]] = True
        for si, gi in zip(*hits):
            memberships[int(gi)].append(int(si))
    for r, ids in zip(records, memberships):
        r['protected_segments'] = sorted(ids)
        vertices = sorted({(int(model.owner[s]),int(model.local_index[s])) for s in ids} |
                          {(int(model.owner[s]),int((model.local_index[s]+1) % len(model.xy[model.owner[s]]))) for s in ids})
        r['protected_vertices'] = [list(v) for v in vertices]
    return {'records':records, 'tree':tree, 'union':shapely.union_all(shapes),
            'protected':protected, 'construction_seconds':time.perf_counter()-started}


def guard_document(guards):
    return [{**{k:v for k,v in g.items() if k!='geometry'}, 'geometry_wkb_hex':g['geometry'].wkb_hex} for g in guards['records']]
