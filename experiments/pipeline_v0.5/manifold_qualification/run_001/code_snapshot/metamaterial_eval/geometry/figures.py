"""Diagnostic displays only; canonical binary arrays are never interpolated."""
import numpy as np
from scipy import ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image
from skimage.morphology import skeletonize


def segments(loops):
    return [np.asarray(r["xy"]) for r in loops]


def binary_panel(ax, mask, title, loops=None):
    n = mask.shape[0]
    ax.imshow(mask, cmap="gray", vmin=0, vmax=1, origin="upper", extent=(0,n,n,0), interpolation="nearest")
    if loops is not None:
        ax.add_collection(LineCollection(segments(loops), colors="#00b8ff", linewidths=.35))
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")


def write_figures(folder, mask, result, repair=None):
    loops, rec = result["document"]["loops"], result["reconstructed"]
    Image.fromarray(mask*255).save(folder/'original.png')
    Image.fromarray(rec*255).save(folder/'reconstructed.png')
    difference = np.zeros((*mask.shape,3), dtype=np.uint8)
    difference[(mask == 0) & (rec == 1)] = (255,50,20)
    difference[(mask == 1) & (rec == 0)] = (30,100,255)
    Image.fromarray(difference).save(folder/'difference.png')
    fig, axes = plt.subplots(2,2,figsize=(12,12), layout="constrained")
    binary_panel(axes[0,0], mask, "Original NPY occupancy")
    binary_panel(axes[0,1], mask, "Exact cell boundaries", loops)
    binary_panel(axes[1,0], rec, "Boundary-loop reconstruction")
    axes[1,1].imshow(difference, origin="upper", extent=(0,len(mask),len(mask),0), interpolation="nearest")
    axes[1,1].set_title("Difference: red FP / blue FN; black = equal", fontsize=10)
    fig.savefig(folder/'diagnostics.png',dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10,10), layout="constrained")
    binary_panel(ax, mask, "Exact vector boundary overlay (raster-cell units)", loops)
    fig.savefig(folder/'boundary_overlay.png',dpi=160); plt.close(fig)

    # Automatically selected inspection windows; these are not mechanical screens.
    dist = ndi.distance_transform_edt(mask)
    interior = np.zeros_like(mask, dtype=bool); interior[32:-32,32:-32] = True
    skeleton = skeletonize(mask.astype(bool))
    candidates = np.argwhere(skeleton & (dist > 1) & interior)
    narrow = candidates[np.argmin(dist[tuple(candidates.T)])] if len(candidates) else np.array([len(mask)//2]*2)
    neighbors = ndi.convolve(skeleton.astype(int),np.ones((3,3),dtype=int)) - skeleton
    junctions = np.argwhere(skeleton & (neighbors >= 3) & interior)
    junction = junctions[len(junctions)//2] if len(junctions) else narrow
    labels, _ = ndi.label(mask == 0, structure=np.ones((3,3)))
    border = np.unique(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])))
    enclosed = (labels > 0) & ~np.isin(labels, border)
    pores = np.argwhere(enclosed & ~ndi.binary_erosion(enclosed))
    pore = pores[len(pores)//2] if len(pores) else narrow
    top_crossings = np.flatnonzero(np.diff(mask[0].astype(int))) + 1
    external_x = top_crossings[np.argmin(abs(top_crossings-len(mask)/2))] if len(top_crossings) else len(mask)//2
    windows = [("Narrow strut candidate", narrow), ("Enclosed pore boundary", pore),
               ("Complex junction candidate", junction), ("External boundary", np.array([2,external_x]))]
    if repair and repair.get("bridges"):
        bridge = repair["bridges"][0]
        windows.append(("Saved repaired connection", (np.array(bridge["start_yx"])+bridge["end_yx"])/2))
    if result["boundaries"]["nonmanifold_vertices_xy"]:
        x,y = result["boundaries"]["nonmanifold_vertices_xy"][0]
        windows.append(("Point-contact singularity", np.array([y,x])))
    fig, axes = plt.subplots(2,3,figsize=(14,9),layout="constrained")
    metadata = []
    for ax, (title, center) in zip(axes.flat, windows):
        binary_panel(ax, mask, title, loops)
        row,col = map(float,center)
        radius = max(16, int(np.ceil(2*dist[int(row),int(col)]))) if title == 'Complex junction candidate' else 16
        bounds = [max(0,col-radius),min(len(mask),col+radius),max(0,row-radius),min(len(mask),row+radius)]
        ax.set_xlim(bounds[:2]); ax.set_ylim(bounds[3],bounds[2])
        ax.set_xticks(np.arange(np.ceil(bounds[0]),bounds[1]+1,4))
        ax.set_yticks(np.arange(np.ceil(bounds[2]),bounds[3]+1,4))
        ax.grid(alpha=.2)
        metadata.append({"title":title,"bounds_xy":bounds})
    for ax in list(axes.flat)[len(windows):]:
        ax.axis("off")
    fig.savefig(folder/'closeups.png',dpi=160); plt.close(fig)
    return metadata
