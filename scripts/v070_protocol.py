"""Register the small cross-family pilot before any LLM generator submission."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.7.0/run_001'
DOC=REPO/'docs/pipeline_v0.7.0'
REQUEST=Path(r'C:\Users\sd22446\.codex\attachments\7c06318b-2b77-4983-bec9-b5667bb0fda6\Pasted text.txt')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def register():
    RUN.mkdir(parents=True,exist_ok=False);DOC.mkdir(parents=True,exist_ok=False)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'initial_working_tree_clean':not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip(),
        'request_sha256':sha(REQUEST),'families':['particle','fiber'],'shape':[256,256],'dtype':'uint8',
        'phases':{'0':{'role':'matrix','physical_solid':True},'1':{'role':'reinforcement','physical_solid':True}},
        'reference_kind':'EXPLICIT_SYNTHETIC_PROCEDURAL_PILOT_NOT_EXPERIMENTAL','physical_pixel_scale':None,
        'conditions':['A_image_only','B_image_descriptors','C_image_descriptors_one_feedback'],
        'independent_trials_per_family_condition':2,'development_seeds':list(range(100,110)),'heldout_seeds':list(range(10)),
        'heldout_extra_seeds_reserved_not_used':list(range(10,20)),'feedback_revisions':1,'initial_calls':12,'maximum_calls':16,
        'fresh_chat_per_initial_trial':True,'feedback_same_chat_as_C_initial':True,'mode':'REGULAR_CHATGPT_CHAT_ONLY_NO_CODEX_NO_WORK',
        'model_identity':'Record exposed UI identity; no inference of backend/version','reasoning':'Keep initial visible configuration constant; record it',
        'generation_timeout_seconds_per_seed':10,'module_timeout_seconds':180,'module_memory_limit':'No arbitrary cap; bounded small arrays and supervised worker timeout',
        'runtime_parameters':{},'generator_dependencies':['numpy','scipy','skimage','PIL','math','random','collections','itertools'],
        'hard_validity':{'both_families':['shape256x256','uint8','labels0and1','nonempty_both_phases','matrix_largest_component_fraction>=0.99','matrix_percolates_x_and_y','reinforcement_components>=2'],
            'connectivity':4,'boundary':'finite_nonperiodic','reinforcement_percolation_required':False,'all_fibers_instance_identifiable_required':False},
        'visible_metrics':{'particle':['fraction','object_count','diameter_mean_px','diameter_std_px','aspect_mean'],
            'fiber':['fraction','axial_mean_deg','alignment','component_span_mean_px','component_width_mean_px']},
        'holdout_metrics':{'particle':['nearest_neighbor_mean_px','nearest_neighbor_cv','interface_density','S2_x_8','S2_y_8'],
            'fiber':['S2_x_8','S2_y_8','interface_density','branched_component_fraction','matrix_lcc']},
        'normalization_scales':{'fraction':.2,'object_count':40,'diameter_mean_px':20,'diameter_std_px':5,'aspect_mean':2,
            'axial_mean_deg':90,'alignment':1,'component_span_mean_px':60,'component_width_mean_px':8,'nearest_neighbor_mean_px':40,
            'nearest_neighbor_cv':1,'interface_density':.1,'S2_x_8':.2,'S2_y_8':.2,'branched_component_fraction':1,'matrix_lcc':1},
        'scoring':'Per-metric absolute error / frozen scale; axial error shortest modulo180. Equal-weight mean within visible and hidden groups; missing required metric makes group unavailable with coverage reported. Validity separate.',
        'diversity':['unique_array_hashes','pairwise_foreground_Jaccard_distance','pairwise_Hamming_fraction','rotation_translation_canonical_component_shape_hashes'],
        'statistical_unit':'Independent LLM generated script; seeds nested; descriptive pilot only; no p values',
        'baseline':'Human/Codex-authored explicitly non-experimental-LLM baseline, source not shown to experimental ChatGPT',
        'feedback_confound':'Additional interaction/iteration opportunity; no equal-attempt no-feedback control in this pilot',
        'campaign_limits':{'wall_hours':8,'new_ANSYS_jobs':0,'max_feedback_per_C_trial':1,'repair_calls':0},
        'protected':['historical experiments','canonical data','porous generators','frozen evaluator','native mechanics','Git history'],'push':False}
    write(RUN/'protocol/PROTOCOL.json',protocol)
    write(RUN/'references/SOURCE_REVIEW.json',{'repository_audit':'Only porous/trabecular targets found; no prepared particle/fiber composite segmentation.',
        'reviewed':[{'title':'Optical Microscopy Dataset of Al10Cu–7.5 wt.% B4C Composites','url':'https://data.mendeley.com/datasets/9t8pzw2995/1','doi':'10.17632/9t8pzw2995.1','license':'CC BY4.0','decision':'Experimental images include porosity and particle pullout; two-phase segmentation would conflate void and reinforcement without independent validation. Deferred, not used as target.'},
            {'title':'Dataset_Multiscale homogenization of additively manufactured short fiber reinforced polymers','url':'https://zenodo.org/records/8197569','doi':'10.5281/zenodo.8197569','files_GB':[11.3,12.4],'decision':'Real segmented3D microtomography;23.7GB archives and constituent/section interpretation outside this bounded2D pilot. Not downloaded; no pixel-scale claim.'},
            {'title':'A Fully Annotated Synthetic Dataset of Fiber Microstructures','url':'https://zenodo.org/records/17856003','doi':'10.5281/zenodo.17856003','decision':'Credible synthetic candidate; cross-sectional elliptical representation and large dataset not adopted as independent longitudinal short-fiber reference.'}],
        'selection':'Locally authored synthetic validation targets permitted by request; images and algorithms openly retained, algorithms never supplied to experimental model. This does not validate reconstruction of real micrographs.'})
    (DOC/'V0_7_0_PROTOCOL.md').write_text('# v0.7.0 registered cross-family pilot\n\nTwo explicit synthetic reference families: particle inclusions and short fibers in a continuous solid matrix. Phase0=matrix,phase1=reinforcement; neither is void. 256×256 uint8; finite boundaries; unknown physical scale. Historical porous/evaluator/mechanics artifacts remain unchanged. No ANSYS work.\n\nTwo independent fresh regular ChatGPT chats per family per A(image),B(image+descriptors),C(B+one feedback) condition:12 initial calls,4 C revisions,16 calls maximum. Ten development seeds100–109;10 held-out seeds0–9 frozen before calls. No repair calls or parameter tuning on held-out data. Exact UI-exposed model/configuration recorded; unavailable version/tokens/cost remain unavailable. No Codex/Work chats for experimental prompts.\n\nSeparate hard validity,visible descriptor errors,hidden descriptor errors and diversity; fixed scales and lists are in protocol/PROTOCOL.json. Matrix connected/percolating; reinforcement particles/fibers need not percolate. Independent script is the experimental unit; seeds are nested replicates. C receives more interaction opportunity; no causal feedback-only or significance claim. One reference per family gives a synthetic pilot,not broad experimental-material generalization.\n',encoding='utf-8')
    print('Registered',RUN,flush=True)


if __name__=='__main__':register()
