"""Researcher-authored simple procedural controls, not experimental LLM responses."""
import numpy as np
from scipy import ndimage as ndi


def particle(seed,parameters=None):
    rng=np.random.default_rng(seed);yy,xx=np.mgrid[:256,:256];out=np.zeros((256,256),np.uint8);count=0
    for _ in range(3000):
        radius=rng.uniform(6,11);x,y=rng.uniform(radius+2,254-radius,2)
        candidate=(xx-x)**2+(yy-y)**2<=radius*radius
        if np.any(candidate&ndi.binary_dilation(out,iterations=2)):continue
        out[candidate]=1;count+=1
        if count==40:break
    return out


def fiber(seed,parameters=None):
    rng=np.random.default_rng(seed);yy,xx=np.mgrid[:256,:256];out=np.zeros((256,256),np.uint8);count=0
    for _ in range(3000):
        length=rng.uniform(40,70);width=rng.uniform(4,7);angle=rng.normal(np.deg2rad(25),np.deg2rad(25));x,y=rng.uniform(40,216,2)
        dx=xx-x;dy=-(yy-y);along=dx*np.cos(angle)+dy*np.sin(angle);normal=-dx*np.sin(angle)+dy*np.cos(angle)
        candidate=normal**2+np.maximum(np.abs(along)-length/2,0)**2<=(width/2)**2
        if np.any(candidate&ndi.binary_dilation(out,iterations=2)):continue
        out[candidate]=1;count+=1
        if count==18:break
    return out
