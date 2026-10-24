# Software documentation evidence

The installed mesher is Gmsh 4.15.0. Consulted its distributed official Python API
docstrings for geo.addPoint/addLine/addCurveLoop/addPlaneSurface,
mesh.field.add/setNumbers/setNumber/setAsBackgroundMesh,
mesh.generate/getNodes/getElements and option.setNumber. Exercised actual APIs on
rectangles, holes, thin ligaments, rejected geometries and the authenticated1024
fixture. Gmsh types 9 (TRI6) and 8 (quadratic line) are checked at runtime.
SecondOrderLinear=1 preserves straight original boundaries and midpoint placement.

Requests for the official web manual https://gmsh.info/doc/texinfo/gmsh.html and
v261 ANSYS PLANE183/CONTA172 element help returned proxy403. No workaround or
claim of successful web consultation is made. Starting references for a licensed
Windows review are:

- https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/ans_elem/Hlp_E_PLANE183.html
- https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/ans_elem/Hlp_E_CONTA172.html
- https://ansyshelp.ansys.com/public/views/secured/corp/v261/en/ans_elem/Hlp_E_TARGE169.html
- https://mapdl.docs.pyansys.com/
- https://mechanical.docs.pyansys.com/

Downloaded the official ansys-mapdl-core0.72.1 wheel from PyPI, without installing
or claiming an ANSYS runtime. Read distributed command documentation for ET,
KEYOPT, E/EN, ESURF, TSHAP and R. This confirms general command-record interfaces,
not target-release element compatibility, contact normals in ANSYS, plane-stress
contact thickness scaling, result item availability or nonlinear convergence.
The generated APDL is DRAFT_UNVERIFIED. Match documentation to the actually
installed release before using it, inspect inventory/normals/defaults, and execute
rectangle tests first. No ANSYS version is installed or verified here.
