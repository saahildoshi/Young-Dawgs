"""Analytical reference definitions and reproducible solver-input preparation."""
from dataclasses import replace
from pathlib import Path
from shapely import box
from .config import CompressionConfig
from .mesh_generation import generate_mesh,save_mesh
from .mesh_validation import validate_mesh
from .ansys_adapter import write_input
from .reporting import write_json,mesh_hash


def prepare_benchmarks(output):
    output=Path(output)
    if output.exists():raise FileExistsError(f'Refusing to overwrite benchmark run: {output}')
    output.mkdir(parents=True)
    config=CompressionConfig(width=1,height=1,boundary_size=.04,bulk_size=.1)
    geometry=box(0,0,1,1)
    mesh=generate_mesh(geometry,config)
    quality,_=validate_mesh(mesh,geometry,config)
    write_json(output/'rectangle_mesh_quality.json',quality)
    if not quality['accepted']:raise RuntimeError('Rectangle mesh gates failed')
    generated=output/'generated';generated.mkdir()
    save_mesh(mesh,generated/'rectangle_mesh.npz')
    for mode in ['plane_stress','plane_strain']:
        for contact in [False,True]:
            write_input(generated/(mode+('_contact' if contact else '_direct')),mesh,replace(config,mode=mode),contact=contact)
    # A strictly labelled analytical infinitesimal reference. Finite-geometry
    # response is compared only at small strain, not asserted equal at 2%.
    import csv
    with (output/'ANALYTICAL_rectangle_reference.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['source','strain','plane_stress_nominal_MPa','plane_stress_force_N','plane_strain_nominal_MPa_per_unit_depth'])
        for strain in [0,.0001,.0005,.001,.005]:
            stress=config.young_modulus*strain
            writer.writerow(['ANALYTICAL_INFINITESIMAL_NOT_ANSYS',strain,stress,stress*config.width*config.thickness,stress/(1-config.poisson_ratio**2)])
    # Connected C-channel: nonadjacent horizontal faces approach under vertical
    # compression. This is an unexecuted candidate engagement test, not proof.
    channel=box(0,0,1,1).difference(box(.2,.49,1.1,.51))
    internal_mesh=generate_mesh(channel,config)
    internal_quality,_=validate_mesh(internal_mesh,channel,config)
    save_mesh(internal_mesh,generated/'internal_contact_candidate_mesh.npz')
    write_json(output/'internal_contact_candidate.json',{
        'geometry':'synthetic connected C-channel; 0.02 mm gap, H=1 mm',
        'initial_gap_mm':.02,'candidate_face_ranges':{'lower':{'y':.49,'x':[.25,1]},'upper':{'y':.51,'x':[.25,1]}},
        'adjacent_continuum_exclusion':'exclude shared-node faces and the connecting web',
        'mesh_quality':internal_quality,'mesh_sha256':mesh_hash(internal_mesh),
        'internal_contact_elements_created':False,'status':'NOT_CONFIGURED_NOT_EXECUTED',
        'required_evidence':['nonadjacent-only element inventory','closing gap','active contact status','pressure and penetration','reaction change vs same model without internal contact'],
        'readiness':'BLOCKED_PENDING_TARGET_RELEASE_REVIEW_AND_SOLVER'})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,m,title in [(axes[0],mesh,'Rectangle benchmark input'),(axes[1],internal_mesh,'Internal-contact candidate; unconfigured')]:
        ax.add_collection(PolyCollection(m.nodes[m.triangles[:,:3]],facecolors='#dce7eb',edgecolors='#234d69',linewidths=.3))
        ax.set(xlim=(-.05,1.05),ylim=(-.05,1.05),aspect='equal',title=title)
    fig.suptitle('Synthetic geometry controls — ANSYS NOT EXECUTED');fig.tight_layout()
    fig.savefig(output/'benchmark_setup.png',dpi=160);plt.close(fig)
    write_json(output/'benchmark_status.json',{'rectangle_inputs':'DRAFT_UNVERIFIED',
        'analytical_values':'INFINITESIMAL_CONTROLS_NOT_ANSYS','solver_execution':'NOT_EXECUTED',
        'platen_contact':'CONFIGURED_IN_DRAFT_NOT_DEMONSTRATED','internal_contact':'NOT_CONFIGURED_NOT_DEMONSTRATED'})
