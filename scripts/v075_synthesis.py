"""Authenticate and index stored cross-family research evidence."""
from pathlib import Path
import os

from scripts.v070_protocol import REPO, read, sha, write
from scripts.v075_protocol import ASSETS, DOC, MICRO, RUN, V074, now

EXPERIMENTS = REPO / 'experiments'
V071 = EXPERIMENTS / 'pipeline_v0.7.1/run_001'
V072 = EXPERIMENTS / 'pipeline_v0.7.2/run_001'


def timeline(path):
    """A schematic of documented stages. It contains no simulated results."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    stages = [
        ('v0.4–0.6', 'Porous generation', 'Binary solid–void geometries\nand contact checks'),
        ('v0.7.0', 'Microscopy', 'P3 particles and F1 fiber\ncross-sections'),
        ('v0.7.1', 'Native mechanics', 'P3 apparent modulus\nand native curves'),
        ('v0.7.2', 'Stiffness objective', 'Large numerical gains\nwith aligned lanes'),
        ('v0.7.3', 'Morphology limits', 'Shape and spatial checks\nfor lane formation'),
        ('v0.7.4', 'Target matching', 'Eight same-chat pairs\nand F1 mechanics'),
        ('v0.7.5', 'Replication', 'Twelve planned chats with\npretreatment matching'),
    ]
    fig, ax = plt.subplots(figsize=(15, 3.8), facecolor='#f6f6f2')
    ax.set_facecolor('#f6f6f2')
    ax.plot(range(7), [0]*7, color='#9ca7a9', linewidth=2)
    navy, teal = '#193849', '#1b706d'
    for i, (version, label, detail) in enumerate(stages):
        color = navy if i < 6 else teal
        ax.scatter([i], [0], s=105, color=color, zorder=3)
        ax.text(i, .17, version, ha='center', color=color, fontsize=11, weight='bold')
        ax.text(i, -.19, label, ha='center', color=navy, fontsize=11, weight='bold')
        ax.text(i, -.39, detail, ha='center', va='top', color='#3d535a', fontsize=9, linespacing=1.35)
    ax.set(xlim=(-.58, 6.58), ylim=(-.76, .48))
    ax.axis('off')
    fig.text(.035, .92, 'Young Dawgs microstructure research', fontsize=19, weight='bold', color=navy)
    fig.text(.035, .84, 'Schematic timeline of documented milestones and the registered replication', fontsize=10, color='#3d535a')
    fig.subplots_adjust(left=.025, right=.975, top=.80, bottom=.05)
    path.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def synthesis():
    package = read(V074 / 'summary/FINAL_PACKAGE_HASHES.json')['files']
    for name, digest in read(V074 / 'fabrication/DELIVERED_ASSETS.json')['files'].items():
        assert sha(ASSETS / name) == digest
    comp = read(V074 / 'target_property_analysis/IF_VERSUS_NF.json')
    sensitivity = read(V074 / 'target_property_analysis/SENSITIVITY_WITHOUT_NF01.json')
    pct = lambda value: f'{100 * value:.4f}%'
    pilot_rows = []
    for arm in ('IF', 'NF'):
        values = comp['arms'][arm]
        pilot_rows.append(f"| {arm} | {pct(values['initial_script_errors']['mean'])} | "
            f"{pct(values['revised_script_errors']['mean'])} | {100 * values['within_conversation_error_reduction']['mean']:.4f} |")
    f1 = read(V074 / 'f1/MESH_SENSITIVITY.json')['cases']
    p3 = [read(V071 / 'mechanical_response' / f'{name}_H1_attempt001.json')['effective_modulus_MPa']
          for name in ('M2_reference', 'M4_B02')]
    report = [
        '# Young Dawgs research synthesis',
        'The project asks whether an LLM can create stochastic microstructures that resemble a reference, predictably change their simulated response, and benefit from measured feedback. These are separate outcomes with different evidence.',
        '**Porous metamaterials.** The early binary generators produced connected solid and void patterns through procedural geometry. Connectivity, pore preservation and mesh checks qualified selected geometries, including Design 009 seed 001 and its central crop. Later licensed contact runs accepted the crop through 1.2575% compression. The 40% coupon result applied to the illustrative homogeneous polymer coupon, and the cropped polymer campaign stopped at contact qualification. [Porous compression record](../pipeline_v0.6.10/V0_6_10_HANDOFF.md).',
        '**Microscopy reconstruction.** P3 is a supplied horizontally flipped SEM tile selected for dispersed irregular inclusions. Its native labels 1 and 5 represent two solids, with provisional chemistry for label 5. F1 uses prepared C/PEEK microscopy and distinguishes matrix 0, transverse fiber cross-sections 1 and void 2. The circular fiber annotations are approximate. Actual ChatGPT scripts were compared across image-only, descriptor-informed and feedback conditions using phase fractions, component geometry, spatial correlations and other family-specific descriptors. Seeds are nested within scripts. Microscopy calibration is unknown. [Reference provenance](../pipeline_v0.7.0/reference_correction_001/V0_7_0_REFERENCE_CORRECTION.md).',
        f'**Mechanical reconstruction.** v0.7.1 measured five actual ANSYS strain checkpoints from 0.1% to 0.5%. The P3 reference and selected generated B02 specimen had H1 apparent moduli {p3[0]:.4f} and {p3[1]:.4f} MPa. Mesh sensitivity limits interpretation of close values. [P3 native curves and moduli](../pipeline_v0.7.1/V0_7_1_P3_MECHANICAL_RESULTS.md).',
        '**Stiffness optimization and morphology drift.** v0.7.2 revisions gained about 94–106% apparent stiffness by placing reinforcement in segmented vertical lanes. The original envelope admitted these shapes. Mean gains were 98.821% with measurements and 101.673% in the control. v0.7.3 added area-weighted shape tails, orientation, occupancy and near-spanning checks that flagged all 40 historical lane realizations. Controlled development means ranged from 1636.446 to 1753.014 MPa. The registered difficulty rule rejected its proposed target, so that study stopped before LLM revisions. [v0.7.2 results](../pipeline_v0.7.2/V0_7_2_HANDOFF.md) · [v0.7.3 development evidence](../pipeline_v0.7.3/V0_7_3_HANDOFF.md).',
        '**Target matching.** v0.7.4 froze 1640 MPa and evaluated eight genuine same-conversation initial/revision pairs. All 94 generated fields met exact composition and the frozen morphology limits, with two bounded construction failures retained. The stricter envelope preserved dispersed geometries while finite metrics still allowed narrower size distributions or more even spacing than the reference.',
        '| v0.7.4 arm | Initial mean error | Revised mean error | Improvement, pp |\n|---|---:|---:|---:|\n' + '\n'.join(pilot_rows),
        f"IF began closer to target. Excluding NF_01, which had an additional nonscientific turn, changed the IF-minus-NF improvement contrast to {100 * sensitivity['improvement_advantage_IF_minus_NF']:+.4f} percentage points. The pilot left the feedback-specific advantage unresolved. [v0.7.4 pilot](../pipeline_v0.7.4/V0_7_4_P3_INVERSE_DESIGN_RESULTS.md).",
        f"**Cross-family mechanics.** F1 native reference/generated H1 moduli were {f1[0]['H1_MPa']:.4f}/{f1[1]['H1_MPa']:.4f} MPa and H2 moduli were {f1[0]['H2_MPa']:.4f}/{f1[1]['H2_MPa']:.4f} MPa. Explicit void geometry omits continuum elements and the void-strip control passed. The two mesh levels changed the values by 2.54–3.24%. [F1 benchmark](../pipeline_v0.7.4/V0_7_4_F1_MECHANICAL_RESULTS.md).",
        '**Interpretation.** Reference geometry resemblance, simulated response resemblance, stiffness improvement, target matching and feedback efficacy require different comparisons. Both composite families use illustrative isotropic moduli, ideal bonded interfaces, pixel boundaries and finite-domain plane stress. The microscopy dimensions, constituent response, anisotropic fiber law, RVE qualification and damage behavior remain unverified. Independent trial counts and possible account context and backend variation constrain the inference.',
        '**v0.7.5 replication.** The registered design pairs twelve initial scripts after development measurement and randomizes feedback within each pair. Matched assignment and the feedback comparison remain pending in this historical synthesis. See the versioned trial evidence and analysis for any later measured outcomes.',
    ]
    (DOC / 'YOUNG_DAWGS_RESEARCH_SYNTHESIS.md').write_text('\n\n'.join(report) + '\n', encoding='utf-8', newline='\n')
    timeline_path = RUN / 'figures/RESEARCH_TIMELINE.png'
    timeline(timeline_path)
    assets = [
        ('Schematic research workflow timeline', timeline_path),
        ('P3 raw SEM', MICRO / 'references/P3/microscopy_input.png'),
        ('P3 evaluator annotation', MICRO / 'references/P3/evaluation_only_labels.npy'),
        ('P3 microscopy and representative generated arrays', MICRO / 'analysis/P3_held_REFERENCE_GENERATED.png'),
        ('F1 prepared C/PEEK image', MICRO / 'references/F1/microscopy_input.png'),
        ('F1 evaluator annotation', MICRO / 'references/F1/evaluation_only_labels.npy'),
        ('F1 reference and generated phase maps', V074 / 'f1/figures/F1_REFERENCE_AND_GENERATED_PHASES.png'),
        ('Historical porous Design 009 seed 001 array', EXPERIMENTS / 'pipeline_v0.4.1/resolution_validation/design_009/seed_001/1024/microstructure.npy'),
        ('Historical porous source and printable model', ASSETS / 'POROUS_METAMATERIAL_PREVIEW.png'),
        ('P3 reference and generated stress–strain', V071 / 'figures/NATIVE_CURVES.png'),
        ('F1 reference and generated stress–strain', V074 / 'f1/figures/F1_ACTUAL_STRESS_STRAIN_AND_FORCE.png'),
        ('F1 actual native curve data', V074 / 'f1/F1_NATIVE_CURVES.csv'),
        ('Historical stiffness increases', V072 / 'figures/HELDOUT_STIFFNESS.png'),
        ('Historical morphology drift', V072 / 'figures/REFERENCE_AND_GENERATED_GEOMETRY.png'),
        ('v0.7.4 initial and revised target errors', V074 / 'figures/P3_PAIRED_SCRIPT_TARGET_ERRORS.png'),
        ('P3 print-ready relief', ASSETS / 'P3_REFERENCE_PRINT_READY.stl'),
        ('Framed porous through-hole model', ASSETS / 'POROUS_METAMATERIAL_PRINT_READY.stl'),
        ('Side-by-side STL preview', ASSETS / 'P3_VS_POROUS_PRESENTATION_MODELS.png'),
        ('P3 STL preview', ASSETS / 'P3_REFERENCE_STL_PREVIEW.png'),
        ('P3 printing instructions', ASSETS / 'PRINTING_INSTRUCTIONS.md'),
        ('Porous printing instructions', ASSETS / 'POROUS_METAMATERIAL_PRINTING_INSTRUCTIONS.md'),
    ]
    lines, inventory = [], []
    for title, path in assets:
        digest = sha(path)
        relative = path.relative_to(REPO).as_posix()
        if relative in package:
            assert digest == package[relative]
        lines.append(f'- [{title}]({Path(os.path.relpath(path, DOC)).as_posix()})')
        inventory.append({'title': title, 'path': relative, 'sha256': digest})
    (DOC / 'YOUNG_DAWGS_PRESENTATION_ASSETS.md').write_text(
        '# Young Dawgs presentation assets\n\n' + '\n'.join(lines) + '\n\n'
        'The recommended P3 relief uses a solid backing and a documented 1383-pixel print-safe simplification. The framed porous model preserves the unedited crop and its 19 original interior through-holes, and encloses 16 clipped edge pockets. The historical full-resolution model contains sub-nozzle features. Both recommended STLs passed geometric checks and actual generic slicing. Physical printer results remain untested. These are enlarged educational geometries derived from 2D fields.\n\n'
        'For a short presentation, start with how the generators reproduce different kinds of geometry. Show native curves, then the stiff but visibly lane-like revisions that motivated stronger constraints. End with the prescribed target and the question of whether measured feedback improves revisions. The v0.7.5 outcome figures depend on completion of the replicated experiment.\n',
        encoding='utf-8', newline='\n')
    write(RUN / 'figures/PRESENTATION_SOURCE_MANIFEST.json', {'checked_utc': now(), 'assets': inventory})
    write(RUN / 'summary/HISTORICAL_COMPARISON.json', {
        'v072': {'IF_mean_stiffness_gain': .98821, 'NF_mean_stiffness_gain': 1.01673,
            'revised_realizations_with_lanes': 40, 'source': 'docs/pipeline_v0.7.2/V0_7_2_HANDOFF.md'},
        'v073': {'revision_calls': 0, 'reason': 'Registered baseline separation requirement was unmet',
            'source': 'docs/pipeline_v0.7.3/V0_7_3_HANDOFF.md'},
        'v074': {'analysis': comp, 'without_NF01': sensitivity, 'F1_mesh_cases': f1},
        'v075_feedback_effect': None})


if __name__ == '__main__':
    synthesis()
