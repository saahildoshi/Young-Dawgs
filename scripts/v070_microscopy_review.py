"""Inspect real downloaded annotations and render UNAPPROVED reference candidates."""
from pathlib import Path
import hashlib,io,json,shutil,urllib.request,zipfile
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,Rectangle
from scripts.v070_correction_setup import CORRECTION,DOC
from scripts.v070_protocol import write,read,sha

DOWNLOADS=Path(r'C:\Users\sd22446\Downloads')
FIBER_ROOT=DOWNLOADS/'Annotated images of microscopy images from carbon fibre composites_1_all'
PARTICLE_IMAGES=DOWNLOADS/'AugmentedImages.zip'
PARTICLE_MASKS=DOWNLOADS/'AugmentedMasks.zip'
FIBER_ARCHIVE=FIBER_ROOT/'Data sets.zip'
PARTICLE_PHASES={0:('Unassigned / unknown','#ff00ff'),1:('Ni matrix','#d6d9df'),2:('Porosity / void','#161616'),3:('WC particles','#168f83'),4:('Dilution band','#e5ad35'),5:('Reprecipitated carbides','#8c58b1')}
FIBER_PHASES={0:('Polymer matrix','#d6d9df'),1:('Carbon fiber cross-sections','#168f83'),2:('Void','#161616')}


def array(z,name):return np.array(Image.open(io.BytesIO(z.read(name))))
def counts(a):return {str(int(k)):int(v) for k,v in zip(*np.unique(a,return_counts=True))}
def fractions(a):return {k:v/a.size for k,v in counts(a).items()}
def colorize(a,phases):
    out=np.empty(a.shape+(3,),np.uint8)
    for label,(_,color) in phases.items():out[a==label]=[int(color[i:i+2],16) for i in [1,3,5]]
    if not set(np.unique(a))<=set(phases):raise ValueError('Unknown phase cannot be silently remapped')
    return out


def fetch_metadata():
    dest=CORRECTION/'sources';dest.mkdir(exist_ok=True)
    url='https://zenodo.org/api/records/17315241';p=dest/'ZENODO_17315241.json'
    if not p.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'YoungDawgs microscopy reference review'})
        with urllib.request.urlopen(req,timeout=30) as r:p.write_bytes(r.read())
    meta=read(p);expected={x['key']:x for x in meta['files']};ledger=[]
    for path in [PARTICLE_IMAGES,PARTICLE_MASKS]:
        actual='md5:'+hashlib.md5(path.read_bytes()).hexdigest();assert actual==expected[path.name]['checksum']
        ledger.append({'path':str(path),'bytes':path.stat().st_size,'SHA256':sha(path),'MD5':actual,'published_checksum_verified':True})
    for path in [DOWNLOADS/'Annotated images of microscopy images from carbon fibre composites_1_all.zip',FIBER_ARCHIVE,FIBER_ROOT/'READ ME.txt']:
        ledger.append({'path':str(path),'bytes':path.stat().st_size,'SHA256':sha(path),'published_checksum_verified':None})
    shutil.copyfile(FIBER_ROOT/'READ ME.txt',dest/'4TU_READ_ME.txt')
    write(dest/'SOURCE_ARCHIVES.json',{'local_archives':ledger,'NiWC_license':meta['metadata']['license'],'fiber_license':{'license':'CC0_1.0','source':'https://research.utwente.nl/en/datasets/annotated-images-of-microscopy-images-from-carbon-fibre-composite-2/'},
        'pixel_scale_um':{'NiWC':None,'fiber':None},'scale_reason':'Neither selected image metadata nor the supplied README establishes micrometers per pixel. Magnification and nominal radius are not adopted as calibration.',
        'particle_phase_mapping_status':'INFERRED_RAW_ONE_BASED_IDS_FROM_PUBLISHED_CLASS_ORDER_AND_PAIRED_VISUAL_CHECK;author export legend not bundled. Native labels preserved.',
        'particle_phase_mapping_basis':'Published model order matrix,porosity,carbide,dilution band,reprecipitated carbides uses zero-based indices;downloaded masks contain labels1..5. Raw0 is retained as unknown,not assumed matrix.',
        'fiber_phase_mapping_status':'AUTHOR_README_EXPLICIT_0_MATRIX_1_FIBER_2_VOID',
        'annotation_limits':{'NiWC':'Human labels;source images are augmented512px crops,not raw acquisition;geometric distortion variants excluded from selection.',
            'fiber':'Semi-automatic annotation uses detected centers and perfect average-radius circles;void minimum-threshold segmentation. Supplied annotations are not exact physical fiber contours.'}})


def inspect():
    fetch_metadata();d=CORRECTION/'screening';d.mkdir(exist_ok=True)
    with zipfile.ZipFile(PARTICLE_IMAGES) as iz,zipfile.ZipFile(PARTICLE_MASKS) as mz:
        names=sorted(n for n in iz.namelist() if n.endswith('_HorizontalFlip.bmp'));records=[]
        for name in names:
            mn=name.replace('AugmentedImages/','AugmentedMasks/');a=array(mz,mn)
            records.append({'image':name,'mask':mn,'phase_fractions':fractions(a),'source_augmentation':'HorizontalFlip only;no elastic/grid distortions'})
        assert len(names)==45 and all(r['mask'] in mz.namelist() for r in records)
        fig,axes=plt.subplots(9,10,figsize=(15,14),layout='constrained')
        for k,r in enumerate(records):
            for j,picture in enumerate([array(iz,r['image']),colorize(array(mz,r['mask']),PARTICLE_PHASES)]):
                ax=axes[k//5,(k%5)*2+j];ax.imshow(picture);ax.axis('off');ax.set_title(f'P{k+1:02d} '+('SEM' if j==0 else 'labels'),fontsize=8)
        fig.suptitle('Ni-WC: all45 geometry-preserving source crops and native masks; not45 independent specimens\nNative labels retained; colors are review display only',fontsize=12);fig.savefig(d/'PARTICLE_SCREEN.png',dpi=120);plt.close(fig)
        write(d/'PARTICLE_SCREEN_INDEX.json',records)
    with zipfile.ZipFile(FIBER_ARCHIVE) as z:
        records=[]
        for name in sorted(n for n in z.namelist() if n.startswith('Test data set/Images/') and not n.endswith('/')):
            mn=name.replace('/Images/','/Masks/').rsplit('.',1)[0]+'.png';a=array(z,mn)
            records.append({'image':name,'mask':mn,'phase_fractions':fractions(a),'source':'Unaugmented test tile;material subtype not resolved by README filename map'})
        fig,axes=plt.subplots(8,8,figsize=(13,13),layout='constrained')
        for k,r in enumerate(records):
            for j,picture in enumerate([array(z,r['image']),colorize(array(z,r['mask']),FIBER_PHASES)]):
                ax=axes[k//4,(k%4)*2+j];ax.imshow(picture);ax.axis('off');ax.set_title(f'F{k+1:02d} '+('micrograph' if j==0 else 'labels'),fontsize=8)
        fig.suptitle('Carbon composite: all32 original test tiles;transverse sections,not longitudinal fibers\nMatrix(gray),carbon fiber(teal),void(black). Native256px,no resizing.',fontsize=12);fig.savefig(d/'FIBER_TEST_SCREEN.png',dpi=120);plt.close(fig)
        write(d/'FIBER_TEST_SCREEN_INDEX.json',records)
        originals=sorted(n for n in z.namelist() if n.startswith('Data set I/Original data set/Masks/') and not n.endswith('/'))
        rr=[]
        for name in originals:
            a=array(z,name);rr.append({'mask':name,'image':name.replace('/Masks/','/Images/').rsplit('.',1)[0]+'.tif','phase_fractions':fractions(a)})
        # Candidate pool covers known C/PEEK material and keeps nontrivial void.
        voids=[r for r in rr if .005<=r['phase_fractions'].get('2',0)<=.10]
        target=np.median([[r['phase_fractions'].get(str(k),0) for k in range(3)] for r in voids],axis=0)
        ranked=sorted(voids,key=lambda r:np.linalg.norm(np.array([r['phase_fractions'].get(str(k),0) for k in range(3)])-target))
        write(d/'FIBER_DATASET_I_SCREEN.json',{'count':len(rr),'eligible_nontrivial_void_count':len(voids),'selection':'Nearest native-tile phase-fraction vector to median among0.5%-10%void. This proposes candidates,not a representative volume certification.','ranked_candidates':ranked[:12],'phase_fraction_population':rr})
        fig,axes=plt.subplots(3,8,figsize=(13,5.8),layout='constrained')
        for k,r in enumerate(ranked[:12]):
            for j,picture in enumerate([array(z,r['image']),colorize(array(z,r['mask']),FIBER_PHASES)]):
                ax=axes[k//4,(k%4)*2+j];ax.imshow(picture);ax.axis('off');ax.set_title(f'K{k+1:02d} '+('C/PEEK' if j==0 else 'labels'),fontsize=8)
        fig.suptitle('Known-material alternative: original DatasetI,C/PEEK,nominal fiber radius3pixels\nTop12 phase-fraction-near-median candidates with retained void annotations',fontsize=11);fig.savefig(d/'FIBER_CPEEK_SCREEN.png',dpi=130);plt.close(fig)
    print('Prepared original-image/annotation screening sheets;no targets frozen',flush=True)


def candidate(identifier,family,image_archive,mask_archive,image_member,mask_member,material,reason,crop=None):
    d=CORRECTION/'candidates'/identifier;d.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(image_archive) as iz,zipfile.ZipFile(mask_archive) as mz:
        original_image=iz.read(image_member);original_mask=mz.read(mask_member)
    (d/('source_image'+Path(image_member).suffix)).write_bytes(original_image)
    (d/('source_mask'+Path(mask_member).suffix)).write_bytes(original_mask)
    image=np.array(Image.open(io.BytesIO(original_image)));mask=np.array(Image.open(io.BytesIO(original_mask)))
    if image.shape[:2]!=mask.shape:raise ValueError('Image and mask not aligned by dimensions')
    if crop is None:crop=[0,0,256,256]
    x0,y0,x1,y1=crop;im=image[y0:y1,x0:x1];labels=mask[y0:y1,x0:x1]
    if labels.shape!=(256,256):raise ValueError('Proposed native evaluation grid must be256x256')
    phases=PARTICLE_PHASES if family=='particle' else FIBER_PHASES
    rgb=colorize(labels,phases)
    Image.fromarray(image).save(d/'SOURCE_MICROGRAPH.png');Image.fromarray(mask).save(d/'SOURCE_LABELS.png')
    Image.fromarray(im).save(d/'PROPOSED_MICROGRAPH_256.png');Image.fromarray(labels).save(d/'PROPOSED_NATIVE_LABELS_256.png');Image.fromarray(rgb).save(d/'PROPOSED_PHASE_DISPLAY_256.png')
    np.save(d/'PROPOSED_NATIVE_LABELS_256.npy',labels)
    write(d/'CANDIDATE.json',{'candidate_id':identifier,'family':family,'status':'PROPOSED_NOT_APPROVED_NOT_FROZEN','primary_target':False,
        'source_dataset':'https://zenodo.org/records/17315241' if family=='particle' else 'https://doi.org/10.4121/bf11171a-1f57-4a8a-9768-757850d13665',
        'attribution':'Mutahar Safdar(2025),Zenodo17315241,CC BY4.0' if family=='particle' else 'Merit Fernhout(2023),4TU,CC0_1.0',
        'material':material,'source_image_archive':str(image_archive),'source_mask_archive':str(mask_archive),'source_image_member':image_member,'source_mask_member':mask_member,
        'image_member_sha256':hashlib.sha256(original_image).hexdigest(),'mask_member_sha256':hashlib.sha256(original_mask).hexdigest(),
        'source_image_shape':list(image.shape),'source_label_shape':list(mask.shape),'crop_xyxy_end_exclusive':crop,'proposed_shape':[256,256],
        'processing':'Exact same native pixel crop for image and categorical annotation;no resizing,no intensity threshold,no cleanup,no label merging',
        'source_augmentation':'Supplied HorizontalFlip version;no elastic/grid transform' if family=='particle' else 'Original unaugmented dataset tile',
        'phase_map':{str(k):{'meaning':name,'display_color':color} for k,(name,color) in phases.items()},
        'phase_mapping_evidence':'Raw1..5 alignment with publication class order is inferred and visually checked;author export legend absent. Raw0 retained unknown.' if family=='particle' else 'Explicit author READ ME.txt:0=matrix,1=fiber,2=void',
        'physical_um_per_pixel':None,'scale_evidence':'No calibrated physical pixel scale established from the supplied tile/metadata. Pixel ruler only;do not infer scale from magnification or fiber radius.',
        'source_phase_pixels':counts(mask),'proposed_phase_pixels':counts(labels),'source_phase_fractions':fractions(mask),'proposed_phase_fractions':fractions(labels),
        'boundary_touching_labels_in_proposed_roi':sorted(set(int(k) for k in np.r_[labels[0],labels[-1],labels[:,0],labels[:,-1]])),
        'all_source_labels_retained_in_crop':set(np.unique(mask))==set(np.unique(labels)),
        'interpretation':'Transverse fiber sections;no longitudinal fiber length/orientation inference' if family=='fiber' else 'Ni-WC particle degradation morphology with multiple annotated material regions',
        'annotation_quality':'Human annotation;gradient/phase-boundary uncertainty and augmentation dependence remain.' if family=='particle' else 'Semi-automatic perfect-radius circle fiber masks and minimum-threshold voids;approximate,not true exact contours.',
        'selection_rationale':reason,'representativeness_limit':'Single field/crop is not certified as an RVE or independent specimen;no LLM accuracy result is being selected.'})
    return d


def proposed_candidates():
    records=read(CORRECTION/'screening/PARTICLE_SCREEN_INDEX.json')
    # P11 includes all five annotated labels and an interior pore,unlike some
    # lower-magnification examples with ambiguous black image-edge strips.
    primary=records[10]
    with zipfile.ZipFile(PARTICLE_MASKS) as z:mask=array(z,primary['mask'])
    target=np.array([np.mean(mask==k) for k in range(1,6)]);best=None
    for y in range(0,257,8):
        for x in range(0,257,8):
            roi=mask[y:y+256,x:x+256]
            if set(np.unique(roi))!=set(np.unique(mask)):continue
            error=float(np.abs(np.array([np.mean(roi==k) for k in range(1,6)])-target).sum())
            item=(error,y,x)
            if best is None or item<best:best=item
    if best is None:raise ValueError('No256px crop preserves all source labels')
    error,y,x=best
    p1=candidate('P1_NiWC_multiphase','particle',PARTICLE_IMAGES,PARTICLE_MASKS,primary['image'],primary['mask'],
        'Directed-energy-deposited Ni-WC metal matrix composite',
        f'P11 in45-tile review:interior annotated pore and matrix,carbide,dilution,reprecipitate all present. Among8px-grid native256 crops retaining every source label,this ROI minimizes L1 source-to-ROI phase-fraction change ({error:.6g}). Only one partial coarse carbide is sampled;not a size-distribution/RVE reference.',[x,y,x+256,y+256])
    alt=records[12]
    p2=candidate('P2_NiWC_lower_magnification','particle',PARTICLE_IMAGES,PARTICLE_MASKS,alt['image'],alt['mask'],
        'Directed-energy-deposited Ni-WC metal matrix composite',
        'P13 in45-tile review,600x-source geometry-preserving tile. Alternative broader field;central native256 region. All observed material labels kept;source contains no label2 pore annotation.',[128,128,384,384])
    known=read(CORRECTION/'screening/FIBER_DATASET_I_SCREEN.json')['ranked_candidates'][0]
    f1=candidate('F1_CPEEK_transverse_with_void','fiber',FIBER_ARCHIVE,FIBER_ARCHIVE,known['image'],known['mask'],
        'Carbon-fiber reinforced PEEK (DatasetI explicitly identified as C/PEEK in author README)',
        'K01 inknown-material screening. Unaugmented DatasetI tile closest to median phase-fraction vector among0.5%-10%void fields. Known polymer identity;many small transverse sections and nonzero pore annotation. Entire native256 field retained;3px nominal fiber radius limits contour detail.')
    alt=read(CORRECTION/'screening/FIBER_TEST_SCREEN_INDEX.json')[28]
    f2=candidate('F2_carbon_transverse_larger_sections','fiber',FIBER_ARCHIVE,FIBER_ARCHIVE,alt['image'],alt['mask'],
        'Carbon-fiber thermoplastic composite;test set includes C/PEEK and C/LM-PEAK. Filename-to-polymer subtype not established from supplied README.',
        'F29 inthe32-original-test-tile review. Larger nominal7px-radius transverse fiber sections with retained void annotation and no crop/resizing. More readable individual sections,but exact selected polymer subtype is unresolved.')
    render_reviews()
    write(CORRECTION/'review/CANDIDATE_INDEX.json',{'references_approved':False,'main_experiment_started':False,'recommended_review_pair':[p1.name,f1.name],
        'alternatives':[p2.name,f2.name],'particle_phase_mapping_needs_export_legend_confirmation':True,
        'candidates':{p.name:{'manifest_sha256':sha(p/'CANDIDATE.json'),'relative_path':str(p.relative_to(CORRECTION))} for p in [p1,p2,f1,f2]}})
    print('Prepared4 proposed candidates and2 compact approval sheets;STOP before any new LLM experiment',flush=True)


def render_reviews():
    root=CORRECTION/'candidates'
    for name,paths in [('PRIMARY_REFERENCE_REVIEW.png',[root/'P1_NiWC_multiphase',root/'F1_CPEEK_transverse_with_void']),
                       ('ALTERNATIVE_REFERENCE_REVIEW.png',[root/'P2_NiWC_lower_magnification',root/'F2_carbon_transverse_larger_sections'])]:
        fig=plt.figure(figsize=(16,10.5));grid=fig.add_gridspec(4,4,height_ratios=[1,.21,1,.21],hspace=.16,wspace=.04)
        fig.subplots_adjust(left=.045,right=.995,bottom=.025,top=.89)
        for row,path in enumerate(paths):
            axes=[fig.add_subplot(grid[2*row,col]) for col in range(4)]
            c=read(path/'CANDIDATE.json');im=np.array(Image.open(path/'SOURCE_MICROGRAPH.png'));roi=np.array(Image.open(path/'PROPOSED_MICROGRAPH_256.png'));labels=np.array(Image.open(path/'PROPOSED_NATIVE_LABELS_256.png'))
            phases=PARTICLE_PHASES if c['family']=='particle' else FIBER_PHASES;rgb=colorize(labels,phases)
            if roi.ndim==2:roi=np.repeat(roi[:,:,None],3,axis=2)
            overlay=np.round(.65*roi.astype(float)+.35*rgb).astype(np.uint8)
            for ax,picture,title in zip(axes,[im,roi,rgb,overlay],['Supplied scientific micrograph','Proposed native256px field','Supplied categorical annotation','Micrograph + annotation overlay']):
                ax.imshow(picture,interpolation='nearest');ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([])
            x0,y0,x1,y1=c['crop_xyxy_end_exclusive'];axes[0].add_patch(Rectangle((x0-.5,y0-.5),x1-x0,y1-y0,fill=False,edgecolor='#e23636',linewidth=1.8))
            axes[0].set_ylabel(c['candidate_id'].replace('_',' '),fontsize=10)
            axes[1].plot([10,74],[242,242],color='white',linewidth=4);axes[1].plot([10,74],[242,242],color='black',linewidth=2)
            axes[1].text(42,232,'64 pixels',ha='center',color='white',fontsize=8,bbox={'facecolor':'black','alpha':.65,'pad':1,'edgecolor':'none'})
            present=[k for k in phases if str(k) in c['proposed_phase_pixels']]
            legend=[Patch(facecolor=phases[k][1],edgecolor='#777',label=f'{k}: {phases[k][0]}') for k in present]
            note=fig.add_subplot(grid[2*row+1,:]);note.axis('off');note.legend(handles=legend,loc='upper center',ncol=3,fontsize=9,frameon=False,borderaxespad=0)
            text='Native IDs preserved. Ni-WC class names inferred from published order;export legend not bundled.' if c['family']=='particle' else 'Author-defined three phases retained. Transverse fiber sections;circle-based annotations are approximate.'
            note.text(.5,-.02,text+' Physical pixel calibration unavailable.',ha='center',va='top',fontsize=9)
        fig.suptitle('PROPOSED REFERENCES - USER APPROVAL REQUIRED',fontsize=17,y=.975)
        fig.text(.5,.935,'Real microscopy + supplied annotations | red box = proposed region | no resizing or phase merging',ha='center',fontsize=12)
        out=CORRECTION/'review';out.mkdir(exist_ok=True);fig.savefig(out/name,dpi=160);plt.close(fig)
    write(CORRECTION/'review/FIGURE_HASHES.json',{p.name:sha(p) for p in (CORRECTION/'review').glob('*.png')})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','candidates','render'],default='inspect',nargs='?');a=p.parse_args()
    if a.action=='inspect':inspect()
    elif a.action=='candidates':proposed_candidates()
    else:render_reviews()
