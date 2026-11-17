# Historical porous metamaterial presentation model

Recommended file: **POROUS_METAMATERIAL_PRINT_READY.stl**, imported in millimeters at100% size. It is **165×165×5mm**: the authenticated central256×256 crop enlarged to160mm, plus a2.5mm external frame. Place either flat face on the bed. Every void passes through the full5mm thickness; there is **no backing plate**.

The source is preserved Design9, seed1, from the1024×1024 historical compression geometry. Solid1 is material; void0 is open space. The historical canonical array already included a documented15-pixel add-only repair. This export does not change any internal source pixel or rerun porous mechanics.

Three files are supplied:

- **POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl**: faithful full specimen,160×160×5mm,412 enclosed through-pores. Its0.15625mm pixel steps and thin details are less conservative for a0.4mm nozzle. Retain it for full-field reference and rescale only uniformly if using a larger printer.
- **POROUS_METAMATERIAL_ORIGINAL.stl**: faithful central crop,160×160×5mm,19 enclosed through-pores and16 void pockets open at the boundary.
- **POROUS_METAMATERIAL_PRINT_READY.stl**: the same crop with an external frame,165×165×5mm. All19 interior pores remain open; the frame encloses the16 boundary pockets, producing35 through-pores. The frame adds1625mm² of solid cross-section outside the original field. It does not fill the internal pores or widen internal struts.

Use a printer-specific PLA profile. The actual generic check used a0.4mm nozzle,0.45mm extrusion width,0.2mm layers, two walls, four top/bottom layers,15% infill, no supports and no adhesion structure. The model has no overhangs requiring support. Choose temperature, cooling, adhesion and speed from the real printer/filament profile. Allow extra bed margin if adding a brim, and remove it carefully from the holes.

The crop has0.625mm source pixel steps. Most structural members are much wider, but narrow taper tips remain. The recorded skeleton-width proxy has a4.375mm fifth percentile and0.625mm minimum; it is not an exact minimum-neck guarantee. External reinforcement supports the edges without changing internal geometry. Inspect each layer, especially narrow connectors. [Prusa's modeling guidance](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135) explains why nozzle/extrusion width limits small features.

The installed Dremel CuraEngine actually sliced the recommended model into25 layers on a hypothetical220×220×250mm bed. Independent G-code checks found one significant connected first-layer body, all35 pore centers clear, no extrusion into pore cores, on-bed placement, no support paths, and approximately99.463% nominal first-layer solid coverage. The omitted fraction reflects slicer treatment of boundaries and small details, not an edit to the source STL. See **POROUS_METAMATERIAL_PRINT_READY_SLICER_PREVIEW.png** and **POROUS_METAMATERIAL_STL_VALIDATION.json**.

**Reslice for the actual printer; no physical print has been made or verified.** Generic audit G-code is not a printer-ready deliverable. Handle the finished object by its frame and avoid bending thin members. The display scale and5mm thickness are presentation choices, not the historical simulation dimensions, a new3D material reconstruction, or a validated mechanical specimen.
