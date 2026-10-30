# v0.6.4 actual nonlinear telemetry

Actual ANSYS2024R1 accepted NLDIAG,CONT,ITER; NLDIAG,NRRE,ON,2;
NLDIAG,EFLG,ON,2; and NLHIST NSOL upper-pilot UY/RF. Contact CND identifies
42 native columns, each load/substep/iteration/time block, pair2/3 active
counts, native chatter, penetration/gap, computed normal stiffness and force.
Pair counts do not identify which individual elements switched. Positive
penetration / negative gap and far-field pinball meanings remain distinguished.

Native v241 NR files are ASCII, with node IDs and DOF codes1,2,6 (FX,FY,MZ).
Streaming localization checks unique complete node IDs and finite values,
excludes platen/internal nodes from specimen localization, and retains32
largest translational residuals. Native component magnitudes do not establish
signed physical forces. The independent rectangle norm agrees within half
the CNVV header's last printed digit. An initial overprecise assertion failed
and is retained separately; mechanical tolerances were not relaxed.

NR/EFLG ring limits are2 each. ANSYS rotates these within each new job; the
last surviving snapshots are retained with metadata/hashes. Historical files
are never rotated. Full retained diagnostic size: 354129610bytes,
within the2GiB diagnostic budget. Small cap256MiB. Actual1s resource samples
are separate from nonlinear history; NLHIST data are converged-substep data,
not per-iteration mechanical results. Trial CND/NR output is explicitly
NONLINEAR_DIAGNOSTIC_ONLY and ineligible for LLM ranking. A native equilibrium
announcement does not turn an iteration record into a qualified field export.

The native file-rotation race exposed in an early small control is preserved
as an operationally invalid receipt. The monitor now tolerates disappearing
ring files and safely terminates owned processes on monitor exceptions or
cancellation. Its unique linearized repeat was executed. The primary full job-name
command warning is retained: the frozen deck attempted FILNAME in PREP7;
actual compression.* outputs are bound using the native current-jobname log
and exact receipt hashes. No native result was renamed, no frozen input was
rewritten and no full job was relaunched for this naming issue. The later
conditional repair addresses the separately evidenced checkpoint/memory
problem and correctly assigns its jobname at Begin level.

Official references are adjacent-release syntax references; installed-release
support is established by the actual small v241 runs:
[NLDIAG](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_NLDIAG.html),
[NLHIST](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_cmd/Hlp_C_NLHIST.html).
