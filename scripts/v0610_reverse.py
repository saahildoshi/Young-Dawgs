"""Isolated second candidate, enabled only by a prospective role-exchange record."""
import argparse
from scripts import v0610_common as common,v0610_crop as crop

def configure():
    root=common.RUN;protocol=common.read(root/'protocol/CANDIDATE_002_REVERSED_ROLES.json')
    if protocol['method']!='REVERSED_ROLES':raise ValueError('Unregistered second candidate')
    common.BASE=common.BASE/'reverse';common.BASE.mkdir(exist_ok=True)
    common.RUN=root/'reverse';common.RUN.mkdir(exist_ok=True)
    if not (common.RUN/'protocol/PROTOCOL.json').exists():common.write_json(common.RUN/'protocol/PROTOCOL.json',common.read(root/'protocol/PROTOCOL.json'))
    crop.BASE=common.BASE;crop.RUN=common.RUN;crop.ROLE_REVERSED=True

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','setup-run','verify-setup','prepare-unified','unified-run','verify-unified','prepare-trial','trial-run','export-prepare','export-run','force-prepare','force-run','qualify']);a=p.parse_args();configure()
    actions={'setup-run':lambda:common.execute('track_B_pair_setup_002',timeout=900),'verify-setup':crop.verify_setup,'prepare-unified':crop.prepare_unified,'unified-run':lambda:common.execute('track_B_pair_unified_setup_001',timeout=900),'verify-unified':crop.verify_unified,'prepare-trial':crop.prepare_trial,'trial-run':lambda:common.execute(crop.TRIAL,cores=8),'export-prepare':crop.export_prepare,'export-run':lambda:common.execute(crop.TRIAL+'_post1_all_v2',solve=False,timeout=1800),'force-prepare':crop.force_prepare,'force-run':lambda:common.execute(crop.TRIAL+'_pair_force_scan_001',solve=False,timeout=900),'qualify':crop.qualify,'prepare':crop.prepare}
    actions[a.action]()
