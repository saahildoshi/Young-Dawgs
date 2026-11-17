"""Actual STL-derived comparative presentation figure and compact fabrication report."""
import importlib.metadata
import numpy as np
import trimesh
from scripts.v070_protocol import read,write,sha
from scripts.v074_experiment import RUN,DOC,ASSETS,now


def build():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax,name,title in zip(axes,['P3_REFERENCE_PRINT_READY.stl','POROUS_METAMATERIAL_PRINT_READY.stl'],
        ['P3 composite relief · two solid phases','Historical porous metamaterial · open voids']):
        mesh=trimesh.load_mesh(ASSETS/name,process=False);up=mesh.face_normals[:,2]>.99
        colors=np.where((mesh.triangles_center[up,2]>3)[:,None],np.array([.88,.66,.27,1]),np.array([.16,.27,.36,1])) if name.startswith('P3') else '#2e8592'
        ax.add_collection(PolyCollection(mesh.triangles[up,:,:2],facecolors=colors,edgecolors='none',antialiased=False))
        size=168 if name.startswith('P3') else 165
        ax.set(xlim=(0,size),ylim=(0,size),aspect='equal',title=title)
        ax.set_xticks([]);ax.set_yticks([])
        ax.set_xlabel('Raised inclusions on continuous backing\n168×168×3.6mm; matrix is solid' if name.startswith('P3') else 'Extruded network with35 through-holes\n165×165×5mm; no backing')
    fig.suptitle('Actual exported presentation models · arbitrary enlarged display dimensions',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(ASSETS/'P3_VS_POROUS_PRESENTATION_MODELS.png',dpi=180);plt.close(fig)
    packages={n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-image','matplotlib','shapely','trimesh','manifold3d']}
    (ASSETS/'fabrication_requirements.txt').write_text(''.join(f'{key}=={value}\n' for key,value in packages.items()),encoding='utf-8',newline='\n')
    p=read(ASSETS/'STL_SOURCE_MANIFEST.json');porous=read(ASSETS/'POROUS_METAMATERIAL_SOURCE_MANIFEST.json')
    pv=read(ASSETS/'STL_VALIDATION.json');qv=read(ASSETS/'POROUS_METAMATERIAL_STL_VALIDATION.json')
    report='''# Presentation fabrication results

Two different material systems are represented. P3 is a raised composite annotation on a continuous solid backing; its matrix is not void. The historical Design9/seed1 model is a straight extrusion of the porous network, with genuine open holes and no backing. Both are enlarged educational props, not authentic3D reconstructions, calibrated specimens or physically printed results.

| File | Display dimensions (mm) | Independent mesh qualification | Open enclosed through-pores |
|---|---|---|---|
| P3_REFERENCE_EXACT_RELIEF.stl |168×168×3.6|FAIL:14 diagonal-only nonmanifold contacts|0|
| P3_REFERENCE_PRINT_READY.stl |168×168×3.6|PASS|0|
| POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl |160×160×5|PASS; fine details remain|412|
| POROUS_METAMATERIAL_ORIGINAL.stl |160×160×5|PASS; authenticated central crop|19|
| POROUS_METAMATERIAL_PRINT_READY.stl |165×165×5|PASS; external2.5mm frame|35|

P3 source labels1/5 contain20731 raised pixels. The print copy contains20354:1383 pixels change (880 removed,503 added), and four-connected raised regions change78→52. Scientific source arrays remain unchanged. Prescribed3×3 opening/closing is followed by six additions at three remaining diagonal-contact sites. The unchanged exact export is retained with its failure explicitly visible.

The porous full1024 array has500104 solid pixels and one four-connected body. Its15-pixel add-only repair was already part of the preserved historical canonical source. The central[384:640,384:640] crop has32195 solid pixels, one body,19 interior pores and16 boundary-clipped void pockets. The crop is recommended at presentation size because it enlarges each original pixel to0.625mm instead of0.15625mm in the full specimen. No internal crop pixel is changed. A1625mm² frame outside the160mm field encloses the16 boundary pockets; the original19 interior holes remain open. Uniform XY scaling preserves proportions.

All qualified meshes have positive volume, consistent winding, two faces per edge, no duplicate/degenerate faces and one connected body after independent STL parsing and identical-position welding. Porous midsections at Z0.25,2.5,4.75mm match the expected polygons with zero area difference; Euler characteristic agrees with the through-hole count. Source polygon fidelity is authenticated against all1048576 pixel centers, integer axis-aligned boundaries and exact area. Eight zero-area crop-boundary line remnants are discarded, as in the historical positive-area crop convention. A nominal1e-7mm triangulation simplification removes degeneracy; analytic volume and all independent sections retain exact source support. Self-intersection exclusion is based on the valid simple-polygon straight extrusion or disjoint height-field construction, plus independent topology/section tests; no arbitrary-triangle collision solver is claimed.

Actual installed Dremel CuraEngine slicing succeeded for both recommended files using a hypothetical220×220×250mm bed,0.4mm nozzle,0.45mm extrusion width and0.2mm layers. P3 produced18 layers, porous25. Independent G-code inspection found all layers present, on-bed extrusion, no support paths and one significant connected first-layer body. Approximate nominal first-layer coverage is99.985% for P3 and99.463% for porous. All35 porous centers and eroded pore cores remain clear. These are computed bead-footprint approximations, not measurements of a physical print. Older slicer header placeholders for time/zero filament are not trusted; actual E moves and elapsed-time output are retained separately.

Two initial slicer setup attempts and two rejected porous triangulation attempts are preserved outside Git with hashes and compact receipts. The first slicer attempt used a wrong extruder path, the second placed the object off bed; neither qualifies. No scientific geometry or historical solver result was changed to resolve these fabrication setup issues.

Minimum-width diagnostics are approximate EDT/skeleton proxies. Narrow stair-step/taper details remain, including0.625mm steps in the crop. The frame improves boundary support without guaranteeing0.8mm minimum width everywhere. Both recommended meshes have actual generic-engine and toolpath checks, but physical reliability and compatibility with the user's printer are NOT_VERIFIED. Reslice for the real printer and inspect narrow members, holes and optional color changes. No generic G-code is supplied as printer-ready.

Actual mesh previews, generic toolpath previews, the side-by-side comparison, source/validation JSON and separate printing instructions are in presentation_assets/v0.7.4. P3 instructions describe an optional color change after the2.4mm base; porous instructions describe the source-faithful and framed variants. There were zero new porous mechanical solves and zero3D mechanical analyses.
'''
    (DOC/'V0_7_4_STL_PRESENTATION_PROP.md').write_text(report,encoding='utf-8',newline='\n')
    write(RUN/'fabrication/DELIVERED_ASSETS.json',{'created_utc':now(),'files':{str(path.relative_to(ASSETS)):sha(path) for path in sorted(ASSETS.iterdir()) if path.is_file()},
        'recommended_P3':pv['variants']['P3_REFERENCE_PRINT_READY.stl']['passed'],
        'recommended_porous':qv['variants']['POROUS_METAMATERIAL_PRINT_READY.stl']['passed'],
        'actual_generic_slicer_checks_passed':all(x['actual_slicer_validation']['passed'] for x in [pv,qv]),
        'physical_print_or_actual_printer_validation':False})
    print('FABRICATION REPORT + COMPARISON',len(list(ASSETS.iterdir())),'assets',flush=True)


if __name__=='__main__':build()
