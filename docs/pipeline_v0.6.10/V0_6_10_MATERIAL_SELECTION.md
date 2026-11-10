# Provisional polymer selection

| Class | Relevant behavior | Decision |
|---|---|---|
| Flexible TPU | Grade-dependent elasticity, plasticity, hysteresis and rate effects require data | No grade or fitted coefficients claimed |
| Polyurethane elastomer | Recoverable deformation is a possible idealization; rate and hysteresis remain material-specific | Representative flexible-elastomer class only |
| Silicone elastomer | Hyperelastic idealization is plausible but grade and multiaxial data are absent | No material-specific prediction |
| Rigid thermoplastic | Yield/permanent deformation may require plasticity; not interchangeable with an elastic law | Not selected for initial feasibility |

The selected model is **ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL**, a generic compressible Neo-Hookean elastomer idealization. No commercial polymer grade, experimental dataset, temperature or strain rate is assigned. E=10MPa and nu=0.45 define mu=3.448275862MPa and K=33.33333333MPa, with ANSYS d=0.06MPa^-1. The exact energy is W=mu/2*(I1bar-3)+(J-1)^2/d. ANSYS NEO takes mu,d, not Mooney-Rivlin C10,d.

The modest compressibility is explicit; no unsupported plane-stress mixed u-P option is used. Coupon tests must verify the installed release and analytical uniaxial response through40%. This range is a numerical benchmark, not experimental validation or a material failure limit. Local strut strains may exceed global compression and remain exploratory. No hysteresis, viscosity, plasticity, fracture or damage is represented. Old E1000 results remain a different material branch.

Model definition reference: [ANSYS hyperelasticity](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_mat/aQw8sq22dldm.html). Element reference: [PLANE183](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/ans_elem/Hlp_E_PLANE183.html). Native2024R1 inventories and solves, rather than adjacent-release pages alone, establish installed behavior.
