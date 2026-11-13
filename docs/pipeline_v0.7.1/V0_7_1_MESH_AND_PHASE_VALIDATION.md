# Structured mesh and phase validation

Ten focused software checks passed, including independent asymmetric-fixture orientation, shared material-edge nodes, full-domain counts, exact phase areas, refinement and rejected porous/undefined labels. Actual reference H1 and H2 meshes have66049/65536 and263169/262144 nodes/elements. Each of the four selected generated seed0 arrays also passed H1 mesh validation. Native1 is material1 matrix-like solid, native5 is material2 reinforcement-like solid. No pixel is removed and no contact joins phases. Image row0 remains at physical y near1mm; element nodes are counterclockwise from the bottom-left corner.

Refinement subdivides pixels without changing the staircase interface. Mesh archives and individual proof manifests retain source hashes, material counts, boundary sets and mesh identities. Native import/material/field qualification follows the analytical benchmark stage; software checks alone are not licensed solver evidence.
