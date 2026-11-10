"""Evidence-bound final v0610 reports, independent statuses and 102-answer handoff."""
import subprocess
from scripts.v0610_common import BASE,RUN,DOC,REPO,read,write_json,file_hash

STATUS='HOLD_CONTACT_ONSET__POLYMER_CROP_NOT_EXECUTED__THIRTY_PERCENT_NOT_ACHIEVED'
START='3fda931f857730e2abef04cfd5f04ef08378f7fb'


def document(name,text):
    (DOC/name).write_text(text.strip()+'\n',encoding='utf-8',newline='\n')


def report():
    perf=read(RUN/'performance/PERFORMANCE.json');tests=read(RUN/'verification/TEST_SUMMARY.json');branches=read(RUN/'mechanical_response/BRANCH_SUMMARY.json');metrics=read(RUN/'mechanical_response/METRICS.json')
    reference=RUN/'material_selection/E1000_REFERENCE.json'
    write_json(reference,{'identity':'CROP_LINEAR_ELASTIC_E1000_V068','E_MPa':1000.,'nu':.3,'plane_stress':True,'reference_thickness_mm':1.,'law':'Historical isotropic linear elastic with NLGEOM; not a calibrated polymer','provenance':'Retrospective explicit property index of unchanged pre-existing source model; source input/setup/manifests were registered before execution.'})
    experiments=[]
    for process in perf['processes']:
        if not process['kind'].endswith('SOURCE'):continue
        from pathlib import Path
        source=Path(process['directory']);polymer=process['kind']=='COUPON_SOURCE'
        material=RUN/'material_selection/MATERIAL.json' if polymer else reference
        experiments.append({'source':str(source),'material_identity':read(material)['identity'],'material_configuration_sha256':file_hash(material),
            'input_sha256':process['input_sha256'],'source_manifest_sha256':file_hash(source/'simulation_manifest.json'),
            'execution_receipt_sha256':process['receipt_sha256'],'RST_sha256':read(source/'execution_receipt.json')['process']['artifacts']['compression.rst']['sha256'],
            'mesh_identity':'HOMOGENEOUS_TWO_TRI6_COUPON' if polymer else read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256']})
    write_json(RUN/'validation/EXPERIMENT_PROVENANCE.json',{'scope':'Retrospective hash index; not a new prospective registration or acceptance decision','experiments':experiments})
    final=read(RUN/'track_B_progressive_compression/track_B_pair5_arc_strict_001_mechanical_qualification.json');state=[s for s in final['states'] if s['accepted']][-1]
    fields=state['fields'];m=state['measurement'];rows=[]
    for b in branches:
        maximum='none' if b['maximum_accepted_strain'] is None else f"{100*b['maximum_accepted_strain']:.7f}%"
        rows.append(f"| `{b['branch']}` | {b['native_saved_states']} | {100*b['maximum_native_strain']:.5f}% | {b['accepted_prefix_states']} | {maximum} | {100*b['first_rejected_requested_strain']:.5f}% |")
    table='| E1000 source | Native states | Native maximum | Accepted prefix states | Accepted maximum | First rejection |\n|---|---:|---:|---:|---:|---:|\n'+'\n'.join(rows)
    result=f"""The highest independently accepted crop compression remains **1.2575%**, at 0.032192 mm top-platen travel, with upper/lower reactions −3.790084913840559/+3.790084911690149 N and nominal compression stress 1.4805019194689684 MPa. This is a new forward-contact E1000 reference run that reproduces the historical maximum; it does not extend it. **30% and 40% crop compression were not achieved.**

The illustrative polymer coupon passed through 40%. No polymer crop source solve was launched because neither registered contact candidate passed the 1.2675% onset gate. The finite campaign stopped at its two-candidate limit with machine time remaining. Local-fixture parent matching did not block either direct crop trial."""
    doclinks='All experiment links below are relative to `experiments/pipeline_v0.6.10/run_001/`. Raw licensed files are retained under `'+str(BASE)+'`. Hashes bind the local raw artifacts; source RSTs and databases are intentionally outside Git.'
    document('V0_6_10_PROTOCOL.md',f"""# v0.6.10 protocol and disposition

{result}

Registration: `protocol/PROTOCOL.json`, 2026-11-10T18:12:43.557895Z; request SHA256 `9f01d756da98de0fa3e7d0b7f1485604357127228ed6772104d08a3f51ccb247`; starting HEAD `{START}`. Sole structural specimen: authenticated central256 crop, [384,384,640,640], 2.56 × 2.56 mm, 1 mm reference thickness, one connected solid, 19 pores, raster solid fraction 0.491256713867188. The preserved boundary-conforming mesh has 174746 nodes and 79678 TRI6 elements. No original full-specimen source solve was performed.

Prospective limits: 12 hours campaign time, 5400 s source stage, 1200 s without converged progress, one native process, 80 GiB free-disk reserve, system-health supervision, no arbitrary RSS cap. Each native launch uses a unique path-derived job ID. Internal `compression` filenames remain isolated by directory for native restart compatibility. No material, geometry, mesh, friction or force/penetration gate was silently changed.

Gates: upper/lower reaction imbalance ≤1%; independent opposing contact-force imbalance ≤1%; native endpoint penetration ≤5e−5 mm; positive analytic deformed TRI6 maps; no unexplained quadratic-boundary crossing; complete authenticated native histories and fields. The supplementary continuous selected-arc depth certificate uses ≤5e−6 mm source arclength spacing, ≤1e−8 mm target chord error, a Lipschitz sampling margin and artificial-cut clearance. It cannot override a pressure-bearing native contact failure. `_mechanical_qualification.json` is the final continuation authority.

Candidate 1 extended both contiguous arcs by six original faces at each end. After its coarse solve failed reaction accuracy, one registered fresh accuracy retry tightened CNVTOL,F from 0.005 to 0.00001 and precontact increments, without changing physical contact. A separate registered technical supervisor correction lets ANSYS handle recoverable trial errors and cutbacks; fatal errors, stall, health, disk and clock limits remain active. The shared monitor defaults retain historical behavior.

Candidate 2 was initially tentative symmetric two-pass contact. Before execution, `CANDIDATE_002_REVERSED_ROLES.json` explicitly replaced it with a single reversed pair to isolate directional assignment and avoid simultaneous redundant constraints. Both physical candidates used the actual crop; no truncated local parent-match prerequisite applied.

`POLYMER_ENTRY_GATE_001.json` prospectively required an uninterrupted accepted E1000 prefix through 1.2675%. A fresh unloaded polymer database, separately defined material and independent polymer path were required after that gate. No material-incompatible restart is permitted. Planned polymer targets were 0.5%,1%,1.5%,2%,5%,10%,15%,20%,25%,30%,35%,40%. Those polymer crop targets were not executed.

{table}

Final disposition: `{STATUS}`. `protocol/CAMPAIGN_STOP.json` records the exhausted candidate budget and preserved failures. No acceptance threshold was relaxed. Read-only final extraction and verification continued after the source-study stop.

{doclinks}
""")
    document('V0_6_10_CONTACT_ONSET_DIAGNOSIS.md',"""# Contact-onset diagnosis

The strongest supported mechanism is loss of local pressure-bearing detection at the adjoining-face corner, while load remains on a neighboring skin. Complete loss of all contact force, abrupt physical-normal reversal, a polymer failure and a proven ANSYS internal implementation defect are not established.

The historical opening source skin is **95927**, original physical boundary face **2138**; its adjacent skin **95928**, physical face **2139**, remains loaded. The opposing exterior notch includes physical face **2637** and historical target skin **95916**. These are selected exterior arcs near the upper-right crop boundary, not internal pore-wall self-contact. Native per-skin histories were preserved in v0.6.9 and re-examined here; `contact_forensics/ARC_EXTENSION.json` records the index mapping and registered coverage hypothesis.

At historical 1.2575% the opening skin is closed/status2. At 1.2675% it is open/status1 with zero pressure while its neighbor remains pressure bearing (about 39.53 MPa). Thus a net nonzero pair force is insufficient proof of correct pressure support across the whole curved boundary. Geometric edge-normal rotations of about 0.0864°,0.1115°,0.0379° do not demonstrate a flip; these reconstructed physical normals are not the unexported internal ANSYS detection normals.

The forward extended trial places face2138 in the interior of source faces2128–2151 and the opposing arc in target faces2628–2649. All 46 partitioned physical faces were removed exactly once from general contact. 15362 general-contact skins remain; source24 + target22 + GC15362 =15408 physical boundary faces. Native oriented topology matches this partition without omitted or duplicated faces. Consequently, simply extending the former endpoints did not repair the transition.

In the strict forward run, the corresponding new source skin95945 is closed at1.2575%, with18.11375 MPa maximum endpoint pressure. At the first rejected saved state, LS6/SS1,1.260833333%, it is open while its neighbor carries37.0815 MPa. The two-sided native structural force proof still passes; reaction imbalance is3.38e−8. This isolates a local pressure-support defect that global equilibrium does not diagnose. The conservative whole-boundary screen finds intersections involving source faces2138/2139 and target face2637. The native pressure-bearing criterion rejects the unsupported part.

The independent supplementary continuous geometry bound passes all91 forward states and all94 reversed states. This means the geometric depth is within the registered tolerance, not that unsupported crossing has become acceptable. The original native contact gate remains failed. At the last accepted forward state the conservative two-direction continuous depth bound is3.3646502e−6 mm, below5e−5 mm.

Reversing the arcs causes an earlier failure: LS4/SS2,1.159090909%, intersecting faces2138/2139 against2637, with no closed pressure-bearing selected source face. Its continuous accepted prefix ends at1.154545455%. Directional assignment matters, but role exchange is not a correction. The native run later exits nonconverged near1.4624%; this numerical limit occurs after the scientific path has already failed.

Coverage/exclusion errors were a testable hypothesis and were explicitly audited. There is no evidence here of a missing face or redundant exposure after the corrected partition, and no basis to blame insufficient arc length alone. A future experiment should isolate supported corner-aware detection/segmentation or an alternative complete general-contact treatment. The exact solver-internal cause remains unproven.
""")
    document('V0_6_10_CONTACT_RECOVERY.md',f"""# Registered contact recovery

No contact correction was selected for polymer crop production. Both licensed candidates were supported sufficiently to build native inventories and run actual E1000 crop sources, but neither supplied an accepted path through the 1.2675% barrier.

{table}

All three source attempts start from the unloaded authenticated crop. Geometry, TRI6 mesh, E=1000 MPa,ν=0.3, friction0, unified CONTA172 KEYOPT(4)=5, selected-pair FKN10 and general-contact FKN100 remain fixed. Candidate1 uses source24,target22,GC15362. Candidate2 exchanges source/target roles to22/24 while retaining the same physical partition. Native setup/ETLIST/RLIST/GCDEF and exact oriented topologies are retained under the relevant `track_B_contact_fixture/` and `native_results/` directories.

The coarse candidate1 has no accepted prefix because its first 0.05% state has about1.32% reaction imbalance. It converges34 states to1.18106%, then a trial distortion of element36599 triggers the historical error-stop supervisor while ANSYS is attempting a bisection. This is preserved as an interrupted attempt, not proof that native adaptive cutback could not recover. The separately registered strict accuracy retry and supervisor correction are technical controls, not a third physical contact candidate.

The strict forward source reaches native1.5% with91 states,62 accepted fromzero to1.2575%. Later convergence does not repair the first unsupported crossing at1.260833333%. The reversed source has94 native states but only47 accepted in the uninterrupted prefix to1.154545455%. The first crossing at1.159090909% carries no selected-pair pressure. Its native failure near1.4624% is separately recorded. All outputs, failed native states and nonlinear telemetry are retained outside Git, with compact evidence and hashes versioned.

Independent opposing structural patch-force scans cover all saved native states for each attempt. Endpoint status/pressure/penetration and pressure-bearing target IDs are checked alongside physical boundary evidence. At1.2575% the forward force proof passes, two selected source faces are closed and maximum endpoint penetration is8.539264e−7 mm. Correct opening remains representable: open faces genuinely have native status0/1, and no artificial tie was imposed. This does not establish successful separation after a high-strain contact cycle; no unloading cycle was run.

No general-contact pore skin closes in any of these accepted prefixes. General contact is configured and its exact coverage verified; pore-contact force transfer at large strain remains untested. No internally closed pair is inferred from an empty native contact field file.

The final `_mechanical_qualification.json` combines native pressure/force/whole-boundary qualification with the additional continuous selected-arc certificate. Both are required. Failed states are never used to authorize continuation, a material change or a restart. No further parameter sweep was performed after exhausting the two registered physical candidates.
""")
    document('V0_6_10_CROP_COMPRESSION.md',f"""# Actual crop compression

{result}

{table}

The actual static loading uses NLGEOM, sparse direct solution, full Newton, line search, adaptive substeps,40 Newton iterations per trial, all native output at every converged substep and NLOAD for structural-force proof. Source targets are0.5%,1%,1.15%,1.2%,1.2575%,1.2675%,1.5%. Strict sources use CNVTOL,F=0.00001, initial precontact strain step0.0001,max0.0005; near onset initial0.00005,max0.0001,min1e−6. These are pseudo-time strain targets, not measured strain rates. Rigid frictionless platens impose top UY=−2.56ε; the original support/control-node scheme is unchanged.

There are219 native saved crop states across the three separate attempts. The forward strict accepted prefix contains62 states; the reverse accepted prefix47. They are separate contact-branch results and cannot be concatenated. The coarse prefix has zero accepted states. Parsed native cutback events: coarse1,strict0,reverse10. The reverse source exits at minimum increment near1.4624% after its94th converged state; all later failed iterations are diagnostics. No native1.5% state is mechanically accepted.

`mechanical_response/ALL_NATIVE_CHECKPOINTS.csv` has every native checkpoint, material/contact identity, exact independently extracted strain where qualified, travel, reactions, nominal stress, equilibrium/contact/mesh quantities, rejection reason and source/input/mesh/proof hashes. A blank mechanical quantity means it was not promoted by qualification; it is not an invented zero. `BRANCH_SUMMARY.json` records continuous path lengths. Raw all-state POST1 CSVs remain in the corresponding source `_post1_all_v2` directory.

At the last accepted forward state nominal stress is |upper reaction|/(2.56mm×1mm), engineering compression is |top UY|/2.56mm. This nominal stress is not the average native Cauchy SYY. The fitted initial loading slope is{metrics['initial_nominal_loading_slope_MPa']:.8f} MPa over{100*metrics['slope_strain_window'][0]:.4f}%–0.5%; it is an apparent finite-crop branch slope, not the constituent E. The trapezoidal loading-work density from0.01% to1.2575% is{metrics['accepted_prefix_loading_work_density_MJ_m3']:.10f} MJ/m³. No unmeasured zero-to-first increment is filled. There is no unloading/hysteresis measurement and no defensible plateau/densification/collapse strain from this short trajectory.

The historical accepted1.2% restart was authenticated, but all new sources are fresh unloaded solves. **Zero genuine restarts occurred.** The strict accepted1.2575% result can be independently read at LS5/SS8; the full source contains later rejected states and is not approved as an all-valid restart parent. No polymer branch changes an E1000 nonlinear restart. The optional polymer infrastructure remains gated and unexecuted.
""")
    document('V0_6_10_DEFORMATION_RESULTS.md',f"""# Actual deformation and native fields

All crop plots show actual E1000 results, with deformation scale1. No simulated or magnified30%/40% crop state exists. Coupon40% is clearly separate.

![Actual accepted crop states](../../experiments/pipeline_v0.6.10/run_001/figures/ACTUAL_ACCEPTED_DEFORMATION.png)

![Accepted branch curves](../../experiments/pipeline_v0.6.10/run_001/figures/ACCEPTED_RESPONSE.png)

![Contact transition](../../experiments/pipeline_v0.6.10/run_001/figures/CONTACT_TRANSITION.png)

`NATIVE_STRESS.png` contains native SXX,SYY,SXY,SEQV; `NATIVE_ELASTIC_STRAIN.png` contains native EPEL XX,YY,XY; `NATIVE_DISPLACEMENT.png` contains UX,UY and magnitude. All are at accepted1.2575%,LS5/SS8. Stress/strain values are native corner-node averages,47525 corners. No midside stress is filled. Visual linear interpolation across corner triangles is solely for display; color clipping is explicitly1st–99th percentile, while numeric extrema remain available. UX/UY are available for all174746 native nodes; rendered corner triangulation does not visualize every midside displacement. Boundary panels sample each exact quadratic edge solely for drawing; mechanical certificates use independent analytic/bounded procedures.

Maximum native displacement magnitude is{fields['max_displacement_mm']:.12g} mm. Native corner SYY ranges{fields['SYY_MPa_percentiles'][0]:.9g} to{fields['SYY_MPa_percentiles'][-1]:.9g} MPa; SEQV maximum{fields['SEQV_MPa_percentiles'][-1]:.9g} MPa. Native EPEL YY ranges{fields['elastic_EYY_percentiles'][0]:.10g} to{fields['elastic_EYY_percentiles'][-1]:.10g}. These local strains exceed the global compression magnitude and are not an elastic failure limit for any real polymer. Hotspots are concentrated around narrow ligaments, notch transitions and loading boundaries; they lack mesh-convergence and yield/damage validation.

`NATIVE_CONTACT.png` plots actual status and endpoint pressure/penetration. Positive native penetration is overlap; signed gap can be obtained as its negative under the native convention. Empty/farfield contact fields remain unavailable, not fabricated values. The versioned final contact CSVs and raw full native datasets preserve native target IDs, force and endpoint measures. There are two closed selected exterior source faces, maximum pressure18.1137543 MPa, endpoint penetration8.53926394e−7 mm. These exterior-notch faces are distinct from internal pore contact, which remains open. There is no accepted evidence of pore closure, densification or global buckling/collapse; no mode classification is inferred from small local bending alone.

The conservative analytic TRI6 map minimum is{fields['minimum_analytic_map_determinant']:.12g} mm² with zero invalid maps. Pore/boundary orientation is screened; small penalty overlap within tolerance is distinguished from unsupported crossings. The accepted state has a two-direction selected-arc continuous depth bound3.3646502e−6 mm; the next saved state is rejected for missing pressure-bearing support despite bounded small depth.

The final native fields were extracted twice in separate licensed read-only POST1 processes, from the authenticated new strict RST at LS5/SS8. Both extractions are byte-identical for all8 scientific CSVs, including full tensor fields, displacement, reactions, platen status/force and general/selected-contact records. The repeated U and selected-pair CSV also match the original all-state extraction. `fields/REPEAT_READBACK.json` binds source RST, final gate and scientific hashes; source input and native setup are authenticated in each readback manifest. Raw tensor CSVs remain outside Git under `final_readback_001/` and`002/`.

For the polymer coupon, native normal EPEL is logarithmic (EPEL YY=log0.6 at40%) and native SYY agrees with Cauchy stress. The old E1000 crop EPEL stays labeled with its native measure and material branch; it is not reinterpreted as a calibrated polymer strain. Native shear convention is retained, without claiming independently verified nonlinear tensor-shear conversion. Reference-area reaction curves remain nominal throughout.

`figures/FIGURE_INVENTORY.json` records plot SHA256s, exact source state and field-repeat proof. Five key figures were visually reviewed for readable layout, actual-state labels and geometry scale; numerical checks are separate from visual display.
""")
    statuses={name:'NOT_ESTABLISHED' for name in read(RUN/'protocol/STATUS_CATALOG.json')['independent_statuses']}
    statuses.update(CROP_SOURCE_AUTHENTICATED='PASS',CROP_MESH_AUTHENTICATED='PASS_UNCHANGED_TRI6',CROP_TOPOLOGY_PRESERVED='PASS_19_PORES_ONE_SOLID',
        POLYMER_CLASS_SELECTED='ILLUSTRATIVE_FLEXIBLE_ELASTOMER',POLYMER_MODEL_DEFINED='COMPRESSIBLE_NEO_HOOKEAN_E10_NU045',MATERIAL_PARAMETER_PROVENANCE='EXPLICIT_ILLUSTRATIVE_NOT_FITTED',
        MATERIAL_COUPON_VERIFIED='PASS_LICENSED_1_TO_40_PERCENT',MATERIAL_EXPERIMENTALLY_CALIBRATED='NO',CONTACT_ONSET_DIAGNOSED='LOCAL_CORNER_PRESSURE_SUPPORT_LOSS_INTERNAL_CAUSE_UNPROVEN',
        CONTACT_FORMULATION_SELECTED='NONE_QUALIFIED_THROUGH_ONSET',CONTACT_PATCH_COVERAGE_VERIFIED='PASS_EXACT_NONREDUNDANT_NATIVE_PARTITION',
        CONTACT_FORCE_TRANSFER_VERIFIED='PASS_ACCEPTED_E1000_PREFIX_ONLY',CONTACT_GEOMETRY_VALID='PASS_ACCEPTED_PREFIX_LATER_UNSUPPORTED_CROSSING_REJECTED',
        INTERNAL_CONTACT_CONFIGURED='PASS_15362_GC_SKINS',INTERNAL_CONTACT_ACTUALLY_ENGAGED='NO_CLOSED_GC_SKINS_IN_ACCEPTED_PREFIX',
        CROP_PROGRESSIVE_COMPRESSION_EXECUTED='YES_THREE_E1000_SOURCES_NO_POLYMER_CROP',CROP_BEYOND_1_2575_PERCENT='NO',
        CROP_TWO_PERCENT='NOT_ACHIEVED',CROP_FIVE_PERCENT='NOT_ACHIEVED',CROP_TEN_PERCENT='NOT_ACHIEVED',CROP_TWENTY_PERCENT='NOT_ACHIEVED',CROP_THIRTY_PERCENT='NOT_ACHIEVED',CROP_FORTY_PERCENT='NOT_ACHIEVED',
        STRESS_STRAIN_CURVE='PASS_SEPARATE_ACCEPTED_E1000_PREFIXES',FORCE_DISPLACEMENT_CURVE='PASS_SEPARATE_ACCEPTED_E1000_PREFIXES',
        NATIVE_STRESS_STRAIN_FIELDS='PASS_REPEAT_E1000_ACCEPTED_MAXIMUM',TRUE_SCALE_DEFORMATION='PASS_ACTUAL_NATIVE_CROP_STATES',NATIVE_CONTACT_FIELDS='PASS_WITH_AVAILABILITY_MASKS',
        RESTART_VERIFIED='HISTORICAL_1_2_PERCENT_AUTHENTICATED_ZERO_NEW_RESTARTS',MECHANICAL_MESH_CONVERGENCE='UNQUALIFIED',DR_WANG_LARGE_STRAIN_OBJECTIVE='NOT_ACHIEVED',
        POLYMER_PHYSICAL_VALIDITY='UNQUALIFIED_NO_GRADE_CALIBRATION',PAPER_READINESS='HOLD',LLM_FEEDBACK_READY='NO',LLM_OPTIMIZATION='NOT_PERFORMED')
    write_json(RUN/'validation/SCIENTIFIC_STATUSES.json',{'overall':STATUS,'independent_statuses':statuses})
    document('V0_6_10_VALIDATION.md',f"""# v0.6.10 validation

## A. Executive summary

{result}

Scientific status: `{STATUS}`.

## B. Scientific scope

Existing central256 crop only:2.56×2.56 mm,1mm reference thickness,19 original pores,one solid,174746 nodes,79678 TRI6. No original full specimen,3D,manufacturing,batch FEM or LLM optimization was performed. Canonical geometry,generators,frozen evaluator and historical result directories are unchanged.

## C. Material model

An explicitly illustrative flexible elastomeric polyurethane-like idealization uses compressible Neo-Hookean W=μ/2(I1bar−3)+(J−1)²/d, E10MPa,ν0.45,μ3.448275862MPa,K33.33333333MPa,d0.06MPa⁻¹. No grade,temperature,rate or experimental calibration is assigned. ANSYS NEO accepts μ,d,not C10,d. The installed2024R1 PLANE183 TRI6 plane-stress coupon with KEYOPT6=0 and1mm reference thickness passes1%,10%,20%,30%,40% against the independent analytic uniaxial solution; maximum force error<3e−7. Native stress/normal-strain measures and lateral/thickness stretch were checked. See material-selection and coupon reports for primary sources and limits. Coupon verification does not establish crop feasibility.

## D. Contact-onset analysis

Historical skin95927/physical face2138 opens while95928/2139 remains loaded against the upper-right exterior notch. This is local pressure redistribution,not total force disappearance. Physical normal rotations do not prove a detection-normal flip. Native solver-internal root cause remains unproven. Extended exact coverage retains the failure at an interior adjoining-face transition; reversed roles make onset earlier. See the full diagnosis and native per-skin evidence.

## E. Contact recovery

{table}

Two physical candidates and one registered accuracy retry were executed. No correction passes the onset barrier. The native topological partition is complete/nonredundant; no geometry/material change was used. Finite experiment cap is exhausted. A supplementary depth bound passes but cannot overrule missing native pressure support.

## F. Crop nonlinear analysis

Three fresh E1000 sources use licensed ANSYS2024R1,NLGEOM,full Newton,line search,sparse direct,adaptive stepping,all fields at every saved state. Strict CNVTOL,F=0.00001 fixes the coarse global-reaction accuracy defect but not the local pressure-support loss. Maximum native1.5% is a rejected diagnostic. There are219 native crop states,62 accepted in the best single continuous prefix. Zero genuine restarts and zero polymer crop solves. No2%,5%,10%,20%,30%,40% accepted crop state exists.

## G. Mechanical response

Accepted maximum:travel0.032192mm,upper reaction−3.79008491384N,lower+3.79008491169N,nominal stress1.48050191947MPa. Separate curves use exact independently extracted engineering compression and reference-area stress; no material/contact splicing. Initial apparent loading slope{metrics['initial_nominal_loading_slope_MPa']:.8f}MPa over0.01%–0.5%; measured-range monotonic work density{metrics['accepted_prefix_loading_work_density_MJ_m3']:.10f}MJ/m³. These are small-strain E1000 network metrics,not calibrated polymer energy absorption,plateau or densification.

## H. Deformation

True-scale initial,0.5%,1%,1.2575% boundary panels; native UX/UY/magnitude,SXX/SYY/SXY/SEQV,EPEL XX/YY/XY and contact plots are retained. Corner stress averages are display-interpolated only; no midside stress fabrication. Final full fields/contact/reactions repeat identically in two independent licensed read-only processes. The rejected1.260833333% contact neighborhood is explicitly labeled diagnostic. See deformation report and figure inventory.

## I. Numerical acceptance

At the accepted maximum:reaction imbalance5.67378e−10; independent two-sided selected-pair structural force passes1%; max native pair endpoint penetration8.539264e−7mm; certified selected-arc continuous depth≤3.3646502e−6mm,below5e−5mm; minimum analytic TRI6 determinant2.72197937e−6mm²; zero invalid maps. Whole-boundary crossing screening plus native pressure-bearing explanations remains required. Unsupported crossings stop acceptance even when native residual convergence and depth bounds pass. General pore contact remains open,so high-strain internal transfer is unverified.

## J. Physical limitations

Illustrative parameters,no polymer grade,data fitting,temperature/rate,viscoelasticity,hysteresis,plasticity,damage or fracture. Two-dimensional plane stress with1mm reference thickness and provisional dimensions; no3D instability or experimental force prediction. Local E1000 strains exceed global strain and lack physical failure criteria. No mechanical mesh-convergence study or exhaustive neck certification. No basis for paper-quality high-strain or autonomous design-feedback claims.

## K. Performance

{perf['native_processes']} native processes:4 source solves (3 crop,1 coupon),the rest setup/readback. Source wall time{perf['source_wall_seconds']:.3f}s; summed all-native wall time{perf['all_native_wall_seconds']:.3f}s; sampled peak process-tree RSS{perf['peak_tree_RSS_bytes']/2**30:.4f}GiB; retained raw v0610 artifact size{perf['raw_disk_bytes']/2**30:.4f}GiB. Zero new restart launches. No arbitrary RSS cap,no sustained severe paging stop,no disk/health stop. Native failure/coarse supervisor interruption and mechanical rejection remain separate. Resource samples are not whole-system peak-memory claims. Additional freed RAM was available; contact validity,not RAM,limited promotion.

## L. Reproducibility

{tests['active']['tests']} active tests pass with frozen evaluator_v1_1;{tests['archive_total']} archived replay checks pass across{tests['archive_groups']} groups;{tests['licensed']['tests']} licensed evidence checks pass,including{tests['licensed_v0610_new']} new v0610 checks. Categories are separate and overlap; do not sum them as unique scientific validations. Synthetic reference/geometry/monitor tests do not establish licensed mechanics. Licensed tests authenticate actual source fields and preserve scientific HOLDs.

`audit/BASELINE.json` binds source/mesh and historical restart artifacts. Per-source manifests/receipts bind input,setup,material configuration and native output hashes; material law source is `material_selection/MATERIAL.json`. `mechanical_response/BRANCH_SUMMARY.json` binds new RST hashes. `fields/REPEAT_READBACK.json` binds repeated final CSVs. `performance/PERFORMANCE.json` lists every native receipt,path,jobID and measured resource record. Raw DB/RST files remain outside Git. `audit/PROTECTED_HISTORY.json` and Git path inventory verify protected history preservation. See handoff for reproduction commands and artifact index.

## M. Git history

Starting clean master HEAD `{START}`. Coherent phases were committed with descriptive messages; no push,amend or history rewrite. Exact complete hashes/messages through the evidence commit are in `V0_6_10_HANDOFF.md` and `validation/GIT_HISTORY.json`. The final report commit cannot contain its own hash; obtain it with `git log -1` and see the terminal handoff. Clean-tree verification occurs after committing these reports.

## N. Next milestone

Register a new narrowly bounded corner-aware detection/segmentation or complete general-contact experiment with exact nonredundant coverage. Demonstrate native pressure-bearing force transfer through the adjoining-face transition on the actual crop under unchanged gates. Then build the verified polymer from the unloaded database and qualify its complete fresh trajectory progressively through2%,5%,10%,20%,30%,40%,checking new internal contacts. Add physical calibration,multiaxial/cyclic behavior and mesh sensitivity before a predictive/paper dataset. Controlled LLM feedback remains gated on that validated dataset.
""")
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    log=subprocess.check_output(['git','log','--reverse','--format=%H%x09%s',START+'..HEAD'],cwd=REPO,text=True).splitlines()
    commits=[{'hash':line.split('\t',1)[0],'message':line.split('\t',1)[1]} for line in log]
    write_json(RUN/'validation/GIT_HISTORY.json',{'starting_head':START,'through_head':head,'commits':commits,'push_performed':False,'final_report_commit':'Resolve git log -1 after report commit; not self-referential'})
    changed=subprocess.check_output(['git','diff','--name-status',START,'HEAD'],cwd=REPO,text=True).splitlines()
    pending=subprocess.check_output(['git','diff','--name-status','HEAD'],cwd=REPO,text=True).splitlines()
    new=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=REPO,text=True).splitlines()
    write_json(RUN/'validation/FILE_INVENTORY.json',{'through_head':head,'committed_changes_from_start':changed,'tracked_report_phase_changes':pending,'report_phase_paths_pending_commit':new,'raw_native_root':str(BASE),'source_native_inventory':'performance/PERFORMANCE.json','binary_solver_artifacts_in_git':False})
    answers={
        1:str(REPO),2:START,3:'Yes; master was clean at registration.',4:'Yes; audit/BASELINE.json binds the unchanged crop source.',5:'Yes;174746 nodes,79678 quadratic TRI6,semantic SHA77788b5bc2923de31d4b0b66dad909510bb32c96708b38d1b1bfc001e22f8add.',6:'Yes;19 pores and one connected solid.',
        7:'Yes; protected historical data/results/generators/evaluator are unchanged. The shared progress monitor adds an opt-in control with its historical default preserved.',8:'No; zero new original full-specimen solves.',9:'Yes; historical1.2% RST/RDB authenticated against native receipts; no new restart was launched.',10:'docs/pipeline_v0.6.10,experiments/pipeline_v0.6.10/run_001 and raw solver/v0610,including reverse; see FILE_INVENTORY.json.',
        11:'Generic flexible elastomeric polyurethane-like idealization.',12:'No commercial grade is claimed.',13:'Simple objective finite-strain law; E10MPa andν0.45 explicitly illustrative. Manufacturer sources inform the class review only; no coefficients were fitted. See material-selection report.',14:'ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL.',15:'Compressible Neo-Hookean,isochoric I1bar plus quadratic volumetric energy.',16:'E10MPa,ν0.45,μ3.448275862MPa,K33.33333333MPa,d0.06MPa^-1. ANSYS NEO takesμ,d.',17:'Numerical homogeneous coupon agreement through40%; no experimentally supported polymer strain range or crop result.',18:'Yes; finite K,ν0.45,J>0 and lateral/thickness response checked.',19:'Yes; installed2024R1 PLANE183 TRI6,KEYOPT3=3,KEYOPT6=0,1mm reference thickness; native SZZ≈0.',20:'Yes; one licensed source coupon and independent POST1 at1%,10%,20%,30%,40%.',21:'Yes; maximum nominal-force relative error2.484e−7,below1%.',22:'Coupon native normal EPEL matches logarithmic strain; native SYY matches Cauchy stress; reference-area reactions give nominal stress. Crop fields retain native EPEL labels; shear conversion was not separately calibrated.',23:'Yes; CROP_LINEAR_ELASTIC_E1000_V068 is distinct from the defined polymer identity.',24:'Yes; fresh unloaded material setup required. No polymer crop source was launched because contact entry failed.',
        25:'Historical skin95927,physical face2138; strict extended setup equivalent skin95945.',26:'Opposing upper-right exterior-notch arcs,including sourcefaces2138/2139 and targetface2637; not internal pore walls.',27:'Local corner pressure-support loss is evidenced; complete internal solver root cause remains unproven. Arc truncation alone is not supported after extension.',28:'Yes; opening95927/face2138 while adjacent95928/2139 remains loaded.',29:'Partition was investigated; exact native audit shows no missing/duplicated faces after extension. No causal exclusion defect is established.',30:'Geometric coverage is complete for the intended extended arcs; valid pressure support through onset is insufficient.',31:'Forward contiguous arc extension; one strict-equilibrium technical retry; reversed source/target roles as physical candidate2.',32:'Native2024R1 setup and source runs executed; support/syntax acceptance does not imply mechanical validity.',33:'None qualified through the barrier.',34:'Yes at the accepted forward prefix,including1.2575%; independent opposing structural force proof passes. Later unsupported crossing still rejects.',35:'Yes in later diagnostics; all unsupported crossings rejected from first failure onward.',36:'Last accepted forward endpoint penetration8.539264e−7mm and continuous arc depth≤3.3646502e−6mm,both<5e−5mm. Small depth alone cannot excuse missing pressure.',37:'Native open statuses remain possible; no tie or tensile adhesive constraint introduced. No full unloading/separation cycle was validated.',38:'Yes; exact single-pair face partition,no source/target shared nodes and no duplicate GC exposure. Symmetric double constraints were not added.',39:'No; forward accepted through1.2575%,reverse only1.154545455%.',40:'Pressure-bearing support at adjoining corner; future high-strain internal contact transfer; native internal normal/search cause unproven.',
        41:'Yes; three fresh E1000 crop source processes. Zero polymer crop source processes.',42:'Accepted prefixes are continuous fromzero in their own fresh source. Forward62 states;reverse47. Later failed states do not repair earlier failures.',43:'No.',44:'No; native1.5% was reached in forward strict source but rejected.',45:'No.',46:'No.',47:'No.',48:'No.',49:'No.',50:'No.',51:'1.5% in strict forward E1000 source; diagnostic only.',52:'1.2575% E1000 forward; no improvement over historical accepted maximum.',53:'0.032192mm top-platen travel.',54:'62 saved states in the best forward accepted prefix;47 in separate reverse prefix;0 in coarse. Do not splice or sum as one loading trajectory.',55:'Parsed native cutbacks:coarse1,strict0,reverse10;11 across all three separate sources.',56:'Historical1.2% restart remains authenticated; new accepted1.2575% result is LS5/SS8. Its full source includes later rejected states,so no new all-valid restart parent is promoted.',57:'Unmodeled/unsupported corner crossing; two registered physical candidates exhausted. Polymer entry fails. Native reverse later nonconverged at minimum increment; RAM/disk did not stop progress.',
        58:'Yes; separate accepted E1000 branch curves. No polymer crop curve.',59:'Yes; separate accepted E1000 branches.',60:'3.790084913840559N.',61:'1.4805019194689684MPa,reference area2.56mm².',62:'Yes; signed upper/lower native pilot reactions independently read back at all states.',63:'Yes in accepted prefixes; final imbalance5.673778e−10. Coarse initial1.32% imbalance fails.',64:'Yes;174746 native nodes,UX/UY; final repeated exactly.',65:'Yes; native SXX,SYY,SXY,SEQV on47525 corners; no invented midside stresses.',66:'Yes; native EPEL XX,YY,XY on47525 corners; final repeated exactly.',67:'Yes; native status,endpoint pressure/penetration,targets,forces and availability masks. Native farfield absence is preserved.',68:'No closed general-contact pore skins in accepted prefixes. Selected exterior-notch pair engagement is distinct.',69:'No accepted pore closure demonstrated; no minimum pore-area metric is claimed.',70:'No validated buckling/collapse/densification mode established. Local bending is visible.',71:'Yes in accepted prefixes; minimum analytic determinant2.72197937e−6mm² at final accepted state.',72:'Yes; unsupported intersection stops accepted path despite native convergence.',73:f"At final accepted E1000 state native EPEL YY range{fields['elastic_EYY_percentiles'][0]:.10g} to{fields['elastic_EYY_percentiles'][-1]:.10g}; maximum |U|{fields['max_displacement_mm']:.10g}mm. Full other tensor components remain in native CSVs.",74:'No grade/calibration,rate/temperature,viscoelasticity,plasticity,damage/fracture;2D thickness assumptions;no mesh convergence;no accepted high-strain polymer path.',
        75:f"{perf['source_solves']} source processes:3 crop E1000 +1 polymer coupon;17 native processes total,including setup and readback.",76:f"{perf['source_wall_seconds']:.6f}s summed source wall;{perf['all_native_wall_seconds']:.6f}s all native wall. Not CPU time.",77:f"{perf['peak_tree_RSS_bytes']/2**30:.6f}GiB sampled native process-tree peak; no arbitrary RSS cap.",78:'No sustained severe paging stop recorded; system hard-fault counters are proxies,not process-specific pagefile reads.',79:f"{perf['raw_disk_bytes']}bytes ({perf['raw_disk_bytes']/2**30:.6f}GiB) raw v0610 artifacts at ledger creation; no cleanup of meaningful failures.",80:'Zero genuine restart launches; all new source models start unloaded.',81:f"{tests['active']['tests']} active tests,zero skipped/failures/errors.",82:f"{tests['archive_total']} checks across{tests['archive_groups']} replay groups; unchanged archived tests against current linked fixture context,not a restored historical environment.",83:f"{tests['licensed']['tests']} licensed-artifact checks,including23 new v0610; counts overlap active/archive categories and are not summed.",84:'Yes; Git protected-path audit and raw baseline SHA verification pass. No evaluator/generator/canonical geometry/historical result changes.',85:'Coarse recoverable-error monitor stop plus force-accuracy failure; strict converged unsupported crossing; reversed earlier unsupported crossing and later minimum-increment nonconvergence. All preserved.',86:'See validation/FILE_INVENTORY.json for complete versioned path inventory,and performance/PERFORMANCE.json for native directories.',87:'All coherent phases were committed; complete evidence-phase list follows.',88:'Full40-character hashes and exact messages follow and appear in validation/GIT_HISTORY.json. Final report commit is supplied by git log -1/terminal handoff.',89:'The evidence phase was committed clean before report generation. Final report changes are committed,then git status --porcelain is checked; the terminal handoff supplies that observed final result. This report cannot certify its own future commit.',90:'No push performed.',
        91:STATUS,92:'Illustrative and uncalibrated; coupon verified,physical polymer validity unqualified.',93:'No.',94:'No.',95:'No.',96:'Best forward E1000 prefix0.01%–1.2575%,62 saved states; separate reverse prefix to1.154545455%,47 states. Polymer homogeneous coupon numerical response is accepted only in its coupon scope.',97:'All coarse source states and all forward/reverse states after first rejection; native maximum1.5%; all unexecuted polymer targets are plans,not results.',98:'Actual accepted E1000 curves/true-scale fields,localized contact failure evidence,and separately verified illustrative polymer coupon. Explain clearly that30–40% crop target is unmet.',99:'Resolve contact,run fresh polymer crop,measure/fix grade-specific constitutive response and strain/rate/temperature validity,calibrate multiaxially/cyclically as appropriate,verify mesh and dimensional/boundary assumptions.',100:'Continuous accepted high-strain native path,mechanical mesh sensitivity,reproducible full fields,calibrated material,experimental comparison and uncertainty/failure criteria.',101:'Separately register corner-aware supported detection/segmentation or full nonredundant GC treatment; prove native pressure-bearing force transfer through onset on actual crop,then fresh verified polymer continuation.',102:'Mechanically accepted,physically qualified multi-design dataset with stable metrics/uncertainty and controlled validation gates. No LLM optimization or design feedback was performed.'}
    questions=read(RUN/'protocol/HANDOFF_QUESTIONS.json')['questions'];assert set(answers)=={q['number'] for q in questions}
    write_json(RUN/'validation/HANDOFF_ANSWERS.json',{'status':STATUS,'answers':[dict(q,answer=answers[q['number']]) for q in questions]})
    text=['# v0.6.10 handoff','',result,'','## Dr. Wang summary','',
        'The approved crop was used for three real reference-material compression attempts. Extending the contact patch and reversing its roles did not resolve the corner crossing: the best mechanically accepted compression remains1.2575%. We established and independently verified an explicitly illustrative polymer law through40% on a homogeneous coupon,but the cropped polymer run remains blocked by contact qualification. The figures show real accepted crop states. No30–40% crop response or calibrated polymer prediction is claimed. The next milestone is a new supported corner-contact treatment followed by a fresh polymer crop trajectory.','',
        '## Independent scientific statuses','', '| Status | Disposition |','|---|---|']
    text.extend(f'| `{k}` | {v} |' for k,v in statuses.items())
    text+=['','## All 102 handoff questions','']
    for q in questions:text.extend([f"**{q['number']}. {q['question']}**",'',answers[q['number']],''])
    text+=['## Exact commits through evidence phase','',f'Starting clean HEAD `{START}`. Evidence through `{head}`. The final report commit follows this list and is supplied in the terminal handoff. No push or history rewrite.','']
    text.extend(f"- `{c['hash']}` — {c['message']}" for c in commits)
    text+=['','## Evidence index and reproduction','',f'Active repository: `{REPO}`. Raw artifacts: `{BASE}`. Versioned run: `{RUN}`.','',
        'The raw root contains immutable source inputs,DB/RST/restart files,native logs and complete all-state scientific CSVs. Git contains compact native receipts,selected small output records,topology tables,qualification JSONs,plots and source scripts. Retained binaries are deliberately outside Git. Per-file native artifact hashes come from execution receipts; source/mesh/material references and RST hashes are cross-bound in audit/readback/branch manifests.','',
        '- `audit/BASELINE.json`, `audit/PROTECTED_HISTORY.json`: source/mesh/restart authentication and protected paths.',
        '- `material_selection/MATERIAL.json`, `SOURCE_REVIEW.json`; `material_coupon/QUALIFICATION.json`, `NATIVE_COUPON_RESPONSE.csv`, `COUPON_RESPONSE.png`: exact illustrative law and separate coupon evidence.',
        '- `protocol/`: original budgets,accuracy/supervisor corrections,reversed candidate,continuous geometry,polymer gate and final stop.',
        '- `track_B_progressive_compression/` and `reverse/track_B_progressive_compression/`: native/continuous/final mechanical gates; final suffix `_mechanical_qualification.json` governs promotion.',
        '- `mechanical_response/ALL_NATIVE_CHECKPOINTS.csv`, `BRANCH_SUMMARY.json`, `METRICS.json`: all219 actual crop states,branch identity and accepted-prefix metrics.',
        '- `fields/REPEAT_READBACK.json`: two identical native tensor/displacement/reaction/contact exports at accepted LS5/SS8.',
        '- `figures/FIGURE_INVENTORY.json`: actual accepted/rejected-state figure sources and hashes.',
        '- `performance/PERFORMANCE.json`: all17 actual native process paths,runtimes,source/setup/readback classification,unique launcher IDs and receipt hashes.',
        '- `verification/TEST_SUMMARY.json`, XML/logs and archived manifest: separate active/archive/licensed checks.',
        '- `validation/SCIENTIFIC_STATUSES.json`, `HANDOFF_ANSWERS.json`, `FILE_INVENTORY.json`, `GIT_HISTORY.json`: independent status and handoff records.',
        '- `validation/EXPERIMENT_PROVENANCE.json`: explicit material-configuration SHA for every source experiment,cross-bound to input,source manifest,native receipt,RST and mesh. The E1000 property index is retrospective documentation of unchanged historical material,not a parameter change.','',
        'Use `.venv/Scripts/python.exe` in the active repository. The scripts intentionally refuse to recreate existing native directories. Reproduction requires a separately registered new run and isolated raw root; never overwrite preserved evidence. Sequence: `scripts.v0610_common` registration; `scripts.v0610_material` prepare/execute/post/execute-post/qualify; `scripts.v0610_crop` setup/unified/trial/export/force/qualify; `--strict` selects the accuracy retry; `scripts.v0610_reverse` repeats the second isolated candidate; `scripts.v0610_geometry SOURCE --branch reverse` adds final geometry. `scripts.v0610_final_fields prepare/run --index 1` then2 and `compare` gives final repeated readback. `scripts.v0610_results` produces actual-data plots. `scripts.v0610_report` writes reports. These names identify this run; do not rerun mutation/preparation actions over existing directories.','',
        'Tests: set EVALUATOR_PATH to `validation/evaluators/evaluator_v1_1.py`,run pytest `tests`; run `scripts.replay_geometry_archives --output NEW_OUTPUT`; run pytest on `validation/ansys_v066_integration.py` through `ansys_v069_integration.py` plus `ansys_v0610_integration.py`. Licensed integration checks require retained local native artifacts; software-only tests do not. Read-only checks do not require a new source solve.','',
        'No automated rerun or additional native job is left running. The material-gated polymer framework is present for a future qualified contact result; it was not executed and establishes no polymer crop acceptance.']
    document('V0_6_10_HANDOFF.md','\n'.join(text))
    print('Wrote9 required reports,35 independent statuses and102 complete answers',flush=True)


if __name__=='__main__':report()
