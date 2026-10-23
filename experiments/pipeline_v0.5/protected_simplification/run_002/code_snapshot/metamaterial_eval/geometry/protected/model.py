"""Stable original-coordinate segment model and cyclic constrained chains."""
import numpy as np
import shapely
from shapely import Polygon, MultiPolygon, STRtree
from ..manifold.contacts import polygon_rings


def signed_area(xy):
    xy = np.asarray(xy)
    return float(np.sum(xy[:, 0]*np.roll(xy[:, 1], -1)-xy[:, 1]*np.roll(xy[:, 0], -1))/2)


class BoundaryModel:
    def __init__(self, geometry):
        self.geometry = geometry
        self.rings = polygon_rings(geometry)
        self.xy = [np.asarray(r['xy'][:-1], dtype=float) for r in self.rings]
        self.offsets = np.cumsum([0]+[len(x) for x in self.xy])
        self.segments = np.concatenate([np.stack((x, np.roll(x, -1, axis=0)), axis=1) for x in self.xy])
        self.lines = shapely.linestrings(self.segments)
        self.tree = STRtree(self.lines)
        self.owner = np.concatenate([np.full(len(x), i, dtype=np.int32) for i, x in enumerate(self.xy)])
        self.local_index = np.concatenate([np.arange(len(x)) for x in self.xy])

    def assemble(self, keeps):
        rebuilt = [x[keep] for x, keep in zip(self.xy, keeps)]
        if any(len(x) < 3 or signed_area(x)*signed_area(y) <= 0 for x, y in zip(self.xy, rebuilt)):
            raise ValueError('Collapsed ring or changed ring orientation.')
        ps = []
        for pi in sorted({r['polygon'] for r in self.rings}):
            ids = [i for i, r in enumerate(self.rings) if r['polygon'] == pi]
            shell = next(rebuilt[i] for i in ids if self.rings[i]['role'] == 'shell')
            holes = [rebuilt[i] for i in ids if self.rings[i]['role'] == 'hole']
            ps.append(Polygon(shell, holes))
        return ps[0] if self.geometry.geom_type == 'Polygon' else MultiPolygon(ps)

    def chains(self, protected):
        """Return original vertex index sequences, covering every free edge once."""
        chains = []
        for ri, xy in enumerate(self.xy):
            n = len(xy); locked = protected[self.offsets[ri]:self.offsets[ri+1]]
            if locked.all():
                continue
            if not locked.any():
                a = min(range(n), key=lambda i: (tuple(xy[i]), i))
                b = int(np.argmax(np.sum((xy-xy[a])**2, axis=1)))
                starts_ends = [(a, b), (b, a)]
                for start, end in starts_ends:
                    count = (end-start) % n
                    ids = (np.arange(count+1)+start) % n
                    chains.append({'chain_id':f'r{ri:04d}_s{start:06d}', 'ring':ri, 'vertices':ids})
            else:
                for start in np.flatnonzero(~locked & np.roll(locked, 1)):
                    count = 0
                    while not locked[(start+count) % n]:
                        count += 1
                    ids = (np.arange(count+1)+start) % n
                    chains.append({'chain_id':f'r{ri:04d}_s{start:06d}', 'ring':ri, 'vertices':ids})
        return chains
