"""Stochastic variability diagnostics, separate from reconstruction accuracy."""
import hashlib,itertools
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import pdist


def configuration_signature(a):
    labels,n=ndi.label(a);sizes=np.bincount(labels.ravel())[1:]
    centers=np.array(ndi.center_of_mass(a,labels,range(1,n+1)))
    # Areas and pair distances ignore component order, translation and rigid
    # rotation of centroid coordinates. Rasterization can alter rotated areas.
    distances=np.sort(pdist(centers)) if len(centers)>1 else np.array([])
    values=np.r_[np.sort(sizes),np.round(distances,3)]
    return hashlib.sha256(values.tobytes()).hexdigest()


def diversity(arrays):
    if not arrays:return {'outputs':0,'unique_hashes':None,'mean_jaccard_distance':None,'mean_hamming_fraction':None,'configuration_signatures':None}
    hashes=[hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for a in arrays];jd=[];hd=[]
    for a,b in itertools.combinations(arrays,2):
        union=np.count_nonzero(a|b);jd.append(1-np.count_nonzero(a&b)/union if union else 0);hd.append(np.mean(a!=b))
    return {'outputs':len(arrays),'unique_hashes':len(set(hashes)),'mean_jaccard_distance':float(np.mean(jd)) if jd else None,
        'mean_hamming_fraction':float(np.mean(hd)) if hd else None,'configuration_signatures':len({configuration_signature(a) for a in arrays}),
        'interpretation':'Pixel Jaccard/Hamming are diversity diagnostics only,not reference reconstruction scores. Configuration signatures and source audit screen simple rigid transformations;no complete proof of stochastic independence.'}
