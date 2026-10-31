"""Bounded native general-contact vectors, preserving far-field absence."""

GC_COLUMNS=['element','status','pi_MPa','pj_MPa','pmean_MPa','peni_mm','penj_mm','fy_N','target_i','target_j','i','j','mid','fx_N']


def general_contact_vectors(model,prefix,chunk_size=250000):
    maximum=model['user_model_elements'];block=min(maximum,chunk_size)
    def arrays(names):return [f'*DIM,{a},ARRAY,{block}' for a in names]
    def deletes(names):return [f'*DEL,{a}' for a in names]
    names=['GID','GSEL','GST']
    lines=['CMSEL,S,'+model['general_contact_component']]+arrays(names)+[
        f'*CFOPEN,{prefix}_gc_status,csv','*VWRITE',"('element,status')",f'*DO,IBEG,1,{maximum},{block}',
        f'NLEN=MIN({block},{maximum}-IBEG+1)','*VLEN,NLEN','*VFILL,GID(1),RAMP,IBEG,1',
        '*VLEN,NLEN','*VGET,GSEL(1),ELEM,IBEG,ESEL','*VLEN,NLEN','*VMASK,GSEL(1)',
        '*VGET,GST(1),ELEM,IBEG,ETAB,CNSTAT','*VLEN,NLEN','*VMASK,GSEL(1)','*VWRITE,GID(1),GST(1)',
        "(F12.0,',',F4.0)",'*ENDDO','*CFCLOS']+deletes(names)
    lines+=['CMSEL,S,'+model['general_contact_component'],'ESEL,R,ETAB,CNSTAT,1,3']
    lines += ['*GET,NGCF,ELEM,0,COUNT',f'*CFOPEN,{prefix}_gc_fields,csv','*VWRITE',"('"+','.join(GC_COLUMNS)+"')",'*IF,NGCF,GT,0,THEN']
    labels=[('GPI','LPI','SMISC',1),('GPJ','LPJ','SMISC',2),('GPM','LPM','SMISC',5),('GGI','LGI','NMISC',5),('GGJ','LGJ','NMISC',6),('GFY','LFY','NMISC',22),('GTI','LTI','NMISC',23),('GTJ','LTJ','NMISC',24),('GFX','LFX','NMISC',21)]
    lines += [f'ETABLE,{label},{item},{seq}' for name,label,item,seq in labels]
    names=['GID','GSEL','GST']+[x[0] for x in labels]+['GNI','GNJ','GNM']
    lines+=arrays(names)+[f'*DO,IBEG,1,{maximum},{block}',f'NLEN=MIN({block},{maximum}-IBEG+1)',
        '*VLEN,NLEN','*VFILL,GID(1),RAMP,IBEG,1','*VLEN,NLEN','*VGET,GSEL(1),ELEM,IBEG,ESEL']
    for name,item,component in [('GST','ETAB','CNSTAT')]+[(x[0],'ETAB',x[1]) for x in labels]+[('GNI','NODE',1),('GNJ','NODE',2),('GNM','NODE',3)]:
        lines+=['*VLEN,NLEN','*VMASK,GSEL(1)',f'*VGET,{name}(1),ELEM,IBEG,{item},{component}']
    lines+=['*VLEN,NLEN','*VMASK,GSEL(1)',
        '*VWRITE,GID(1),GST(1),GPI(1),GPJ(1),GPM(1),GGI(1),GGJ(1),GFY(1),GTI(1),GTJ(1),GNI(1),GNJ(1),GNM(1),GFX(1)',
        "(F12.0,',',F4.0,6(',',E24.16),5(',',F12.0),',',E24.16)",'*ENDDO']+deletes(names)+['*ENDIF','*CFCLOS','ALLSEL,ALL']
    return lines+['CMSEL,S,'+model['general_contact_component'],'ESEL,R,ETAB,CNSTAT,1,3','*GET,NGCF,ELEM,0,COUNT',
        f'*CFOPEN,{prefix}_gc_balance,csv','*VWRITE',"('assembled_contact_fx_N,assembled_contact_fy_N')",'*IF,NGCF,GT,0,THEN','NSEL,ALL','FSUM,,CONT',
        '*GET,GFSX,FSUM,0,ITEM,FX','*GET,GFSY,FSUM,0,ITEM,FY','*VWRITE,GFSX,GFSY',"(E24.16,',',E24.16)",'*ENDIF','*CFCLOS','ALLSEL,ALL']
