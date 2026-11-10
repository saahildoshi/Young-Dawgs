import numpy as np
from scipy import ndimage as ndi

def generate_microstructure(seed,parameters=None):
    rng=np.random.default_rng(seed);yy,xx=np.mgrid[:256,:256];out=np.zeros((256,256),np.uint8);count=0
    for _ in range(3000):
        radius=rng.uniform(6,11);x,y=rng.uniform(radius+2,254-radius,2)
        candidate=(xx-x)**2+(yy-y)**2<=radius*radius
        if np.any(candidate&ndi.binary_dilation(out,iterations=2)):continue
        out[candidate]=1;count+=1
        if count==40:break
    return out
