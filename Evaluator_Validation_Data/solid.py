import numpy as np

# Phase definitions
SOLID = 1
VOID = 0

# Fully solid image (256x256)
solid_img = np.ones((256, 256), dtype=np.uint8)

# Fully void image (256x256)
void_img = np.zeros((256, 256), dtype=np.uint8)
