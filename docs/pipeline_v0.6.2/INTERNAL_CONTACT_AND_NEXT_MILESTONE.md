# Internal contact and the next controlled pilot

The demonstrated contacts are rigid platen versus deformable specimen.
Internal self-contact is UNQUALIFIED_NOT_CONFIGURED_NOT_DEMONSTRATED.

The authenticated source geometry has 412 pore loops plus its external
boundary. These identify potential free surfaces, not valid contact pairs.
Do not create contact across shared edges of connected continuum triangles,
duplicate platen pairs, or pair adjacent segments at a connected corner.

Official CONTA172 documentation describes both pair-based interactions and
GCGEN general contact, including interaction within surfaces. This establishes
a candidate capability, not a demonstrated v241 project configuration. Before
applying it to the full specimen, verify the installed release's GCGEN/GCDEF
rules and test initially separated deformable surfaces that actually close.
Record nonadjacent surface selection, exclusions, initial gap, pressure,
contact-element forces, penetration and convergence. No such internal-contact
demonstration executed in this milestone.

Next, retrieve the original selected fine_new generated/mesh.npz and verify
its semantic mesh SHA256 against e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc.
Recheck its exact source, 2,766,505 nodes, 1,261,670 TRI6, 412 pores, coordinate
scale and registered quality requirements without remeshing. Import-only MAPDL
verification must precede any pilot. Measure model-specific memory/disk and
license-size feasibility; array lower bounds do not establish solver capacity.

After these gates, register one conservative full-specimen platen-contact
pilot with bounded resources. Stop at the first nonconverged increment and
retain achieved fields. Mechanical mesh convergence, internal contact at larger
strains, contact sensitivity, material calibration and prior cumulative
small-pore fidelity HOLD remain separate research requirements.

Controlled cross-design comparisons require consistent source/mesh acceptance,
material/thickness/contact/loading, valid outputs and suitable refinement
evidence. A paper-quality dataset also requires calibrated assumptions,
replicates and uncertainty. The first LLM-guided iteration additionally needs
a reviewed feedback schema and explicit invalid-result handling; never label
an input/resource/numerical failure as poor physical design. No autonomous
controller, batch study, manufacturing qualification or 3D work is authorized.

References (v242 comparison documentation; v241 help was inaccessible):

- [CONTA172](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_CONTA172.html)
- [PLANE183](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_PLANE183.html)
- [TARGE169](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_TARGE169.html)
- [ETABLE averaging and output methods](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_ETABLE.html)
