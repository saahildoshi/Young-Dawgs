# v0.6.10 validation

## A. Executive summary

The highest independently accepted crop compression remains **1.2575%**, at 0.032192 mm top-platen travel, with upper/lower reactions −3.790084913840559/+3.790084911690149 N and nominal compression stress 1.4805019194689684 MPa. This is a new forward-contact E1000 reference run that reproduces the historical maximum; it does not extend it. **30% and 40% crop compression were not achieved.**

The illustrative polymer coupon passed through 40%. No polymer crop source solve was launched because neither registered contact candidate passed the 1.2675% onset gate. The finite campaign stopped at its two-candidate limit with machine time remaining. Local-fixture parent matching did not block either direct crop trial.

Scientific status: `HOLD_CONTACT_ONSET__POLYMER_CROP_NOT_EXECUTED__THIRTY_PERCENT_NOT_ACHIEVED`.

## B. Scientific scope

Existing central256 crop only:2.56×2.56 mm,1mm reference thickness,19 original pores,one solid,174746 nodes,79678 TRI6. No original full specimen,3D,manufacturing,batch FEM or LLM optimization was performed. Canonical geometry,generators,frozen evaluator and historical result directories are unchanged.

## C. Material model

An explicitly illustrative flexible elastomeric polyurethane-like idealization uses compressible Neo-Hookean W=μ/2(I1bar−3)+(J−1)²/d, E10MPa,ν0.45,μ3.448275862MPa,K33.33333333MPa,d0.06MPa⁻¹. No grade,temperature,rate or experimental calibration is assigned. ANSYS NEO accepts μ,d,not C10,d. The installed2024R1 PLANE183 TRI6 plane-stress coupon with KEYOPT6=0 and1mm reference thickness passes1%,10%,20%,30%,40% against the independent analytic uniaxial solution; maximum force error<3e−7. Native stress/normal-strain measures and lateral/thickness stretch were checked. See material-selection and coupon reports for primary sources and limits. Coupon verification does not establish crop feasibility.

## D. Contact-onset analysis

Historical skin95927/physical face2138 opens while95928/2139 remains loaded against the upper-right exterior notch. This is local pressure redistribution,not total force disappearance. Physical normal rotations do not prove a detection-normal flip. Native solver-internal root cause remains unproven. Extended exact coverage retains the failure at an interior adjoining-face transition; reversed roles make onset earlier. See the full diagnosis and native per-skin evidence.

## E. Contact recovery

| E1000 source | Native states | Native maximum | Accepted prefix states | Accepted maximum | First rejection |
|---|---:|---:|---:|---:|---:|
| `track_B_pair5_arc_trial_001` | 34 | 1.18106% | 0 | none | 0.05000% |
| `track_B_pair5_arc_strict_001` | 91 | 1.50000% | 62 | 1.2575000% | 1.26083% |
| `reverse/track_B_pair5_arc_trial_001` | 94 | 1.46232% | 47 | 1.1545455% | 1.15909% |

Two physical candidates and one registered accuracy retry were executed. No correction passes the onset barrier. The native topological partition is complete/nonredundant; no geometry/material change was used. Finite experiment cap is exhausted. A supplementary depth bound passes but cannot overrule missing native pressure support.

## F. Crop nonlinear analysis

Three fresh E1000 sources use licensed ANSYS2024R1,NLGEOM,full Newton,line search,sparse direct,adaptive stepping,all fields at every saved state. Strict CNVTOL,F=0.00001 fixes the coarse global-reaction accuracy defect but not the local pressure-support loss. Maximum native1.5% is a rejected diagnostic. There are219 native crop states,62 accepted in the best single continuous prefix. Zero genuine restarts and zero polymer crop solves. No2%,5%,10%,20%,30%,40% accepted crop state exists.

## G. Mechanical response

Accepted maximum:travel0.032192mm,upper reaction−3.79008491384N,lower+3.79008491169N,nominal stress1.48050191947MPa. Separate curves use exact independently extracted engineering compression and reference-area stress; no material/contact splicing. Initial apparent loading slope119.82004470MPa over0.01%–0.5%; measured-range monotonic work density0.0093904110MJ/m³. These are small-strain E1000 network metrics,not calibrated polymer energy absorption,plateau or densification.

## H. Deformation

True-scale initial,0.5%,1%,1.2575% boundary panels; native UX/UY/magnitude,SXX/SYY/SXY/SEQV,EPEL XX/YY/XY and contact plots are retained. Corner stress averages are display-interpolated only; no midside stress fabrication. Final full fields/contact/reactions repeat identically in two independent licensed read-only processes. The rejected1.260833333% contact neighborhood is explicitly labeled diagnostic. See deformation report and figure inventory.

## I. Numerical acceptance

At the accepted maximum:reaction imbalance5.67378e−10; independent two-sided selected-pair structural force passes1%; max native pair endpoint penetration8.539264e−7mm; certified selected-arc continuous depth≤3.3646502e−6mm,below5e−5mm; minimum analytic TRI6 determinant2.72197937e−6mm²; zero invalid maps. Whole-boundary crossing screening plus native pressure-bearing explanations remains required. Unsupported crossings stop acceptance even when native residual convergence and depth bounds pass. General pore contact remains open,so high-strain internal transfer is unverified.

## J. Physical limitations

Illustrative parameters,no polymer grade,data fitting,temperature/rate,viscoelasticity,hysteresis,plasticity,damage or fracture. Two-dimensional plane stress with1mm reference thickness and provisional dimensions; no3D instability or experimental force prediction. Local E1000 strains exceed global strain and lack physical failure criteria. No mechanical mesh-convergence study or exhaustive neck certification. No basis for paper-quality high-strain or autonomous design-feedback claims.

## K. Performance

17 native processes:4 source solves (3 crop,1 coupon),the rest setup/readback. Source wall time2589.231s; summed all-native wall time3202.795s; sampled peak process-tree RSS3.4935GiB; retained raw v0610 artifact size15.2235GiB. Zero new restart launches. No arbitrary RSS cap,no sustained severe paging stop,no disk/health stop. Native failure/coarse supervisor interruption and mechanical rejection remain separate. Resource samples are not whole-system peak-memory claims. Additional freed RAM was available; contact validity,not RAM,limited promotion.

## L. Reproducibility

818 active tests pass with frozen evaluator_v1_1;475 archived replay checks pass across9 groups;175 licensed evidence checks pass,including23 new v0610 checks. Categories are separate and overlap; do not sum them as unique scientific validations. Synthetic reference/geometry/monitor tests do not establish licensed mechanics. Licensed tests authenticate actual source fields and preserve scientific HOLDs.

`audit/BASELINE.json` binds source/mesh and historical restart artifacts. Per-source manifests/receipts bind input,setup,material configuration and native output hashes; material law source is `material_selection/MATERIAL.json`. `mechanical_response/BRANCH_SUMMARY.json` binds new RST hashes. `fields/REPEAT_READBACK.json` binds repeated final CSVs. `performance/PERFORMANCE.json` lists every native receipt,path,jobID and measured resource record. Raw DB/RST files remain outside Git. `audit/PROTECTED_HISTORY.json` and Git path inventory verify protected history preservation. See handoff for reproduction commands and artifact index.

## M. Git history

Starting clean master HEAD `3fda931f857730e2abef04cfd5f04ef08378f7fb`. Coherent phases were committed with descriptive messages; no push,amend or history rewrite. Exact complete hashes/messages through the evidence commit are in `V0_6_10_HANDOFF.md` and `validation/GIT_HISTORY.json`. The final report commit cannot contain its own hash; obtain it with `git log -1` and see the terminal handoff. Clean-tree verification occurs after committing these reports.

## N. Next milestone

Register a new narrowly bounded corner-aware detection/segmentation or complete general-contact experiment with exact nonredundant coverage. Demonstrate native pressure-bearing force transfer through the adjoining-face transition on the actual crop under unchanged gates. Then build the verified polymer from the unloaded database and qualify its complete fresh trajectory progressively through2%,5%,10%,20%,30%,40%,checking new internal contacts. Add physical calibration,multiaxial/cyclic behavior and mesh sensitivity before a predictive/paper dataset. Controlled LLM feedback remains gated on that validated dataset.
