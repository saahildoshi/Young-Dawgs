"""One registered wider context replay, isolated from the first local attempt."""
import argparse
from scripts import v069_local as local

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['extract','vector_readback','execute','baseline','post','qualify']);p.add_argument('--name');a=p.parse_args()
    local.BASE=local.BASE/'expanded';local.BASE.mkdir(exist_ok=True)
    local.RUN=local.RUN/'expanded';local.RUN.mkdir(parents=True,exist_ok=True)
    local.ROI=[2.15,2.56,1.85,2.45]
    if a.action=='execute':local.execute(a.name)
    else:getattr(local,a.action)()
