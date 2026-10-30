"""Selective native records and bounded read-only exports for v0.6.5."""
from pathlib import Path
import re
from .microstructure_pilot import database_resume,stage_block,vector_fields


SELECTIVE_OUTPUT = ['OUTRES,ERASE','OUTRES,ALL,NONE'] + [
    'OUTRES,'+item+',LAST' for item in ['NSOL','RSOL','STRS','EPEL','CONT','MISC']]
OUTPUT_AUXILIARY = ['OUTPR,ALL,NONE','OSRESULT,ERASE','RESCONTROL,DEFINE,ALL,LAST,1','OUTRES,STAT','RESCONTROL,STATUS']


def chunked_vectors(node_count,prefix,chunk_size=250000):
    if node_count<1 or chunk_size<1:raise ValueError('Positive node/chunk sizes required')
    block=min(node_count,chunk_size)
    arrays=['IDS','UXV','UYV']
    lines=['ALLSEL,ALL']+[f'*DIM,{a},ARRAY,{block}' for a in arrays]
    lines += [f'*CFOPEN,{prefix}_displacements,csv','*VWRITE',"('node,ux_mm,uy_mm')",
              f'*DO,IBEG,1,{node_count},{block}',f'NLEN=MIN({block},{node_count}-IBEG+1)',
              '*VLEN,NLEN','*VFILL,IDS(1),RAMP,IBEG,1',
              '*VLEN,NLEN','*VGET,UXV(1),NODE,IBEG,U,X',
              '*VLEN,NLEN','*VGET,UYV(1),NODE,IBEG,U,Y',
              '*VLEN,NLEN','*VWRITE,IDS(1),UXV(1),UYV(1)',"(F12.0,2(',',E24.16))",'*ENDDO','*CFCLOS']
    lines += [f'*DEL,{a}' for a in arrays]
    arrays=['IDS','MASKV','SYV','SEQV','EYV','EXV']
    lines += [f'*DIM,{a},ARRAY,{block}' for a in arrays]
    lines += [f'*CFOPEN,{prefix}_stress,csv','*VWRITE',"('node,syy_MPa,seqv_MPa,elastic_eyy,elastic_exx')",
              'ESEL,S,TYPE,,1','CMSEL,S,CORNERS',f'*DO,IBEG,1,{node_count},{block}',
              f'NLEN=MIN({block},{node_count}-IBEG+1)','*VLEN,NLEN','*VFILL,IDS(1),RAMP,IBEG,1',
              '*VLEN,NLEN','*VGET,MASKV(1),NODE,IBEG,NSEL']
    for name,item,component in [('SYV','S','Y'),('SEQV','S','EQV'),('EYV','EPEL','Y'),('EXV','EPEL','X')]:
        lines += ['*VLEN,NLEN','*VMASK,MASKV(1)',f'*VGET,{name}(1),NODE,IBEG,{item},{component}']
    lines += ['*VLEN,NLEN','*VMASK,MASKV(1)','*VWRITE,IDS(1),SYV(1),SEQV(1),EYV(1),EXV(1)',
              "(F12.0,4(',',E24.16))",'*ENDDO','*CFCLOS','ALLSEL,ALL']
    return lines+[f'*DEL,{a}' for a in arrays]


def read_only_input(database,result_base,model,strain,*,chunk_size=250000):
    result_base=Path(result_base).resolve().as_posix()
    if "'" in result_base:raise ValueError('Unsupported result path')
    block=stage_block(1,strain,model,{})
    block=block[block.index('SOLVE')+1:]
    vectors=vector_fields(model['specimen_nodes'],'stage001')
    start=next(i for i in range(len(block)) if block[i:i+len(vectors)]==vectors)
    block=block[:start]+chunked_vectors(model['specimen_nodes'],'stage001',chunk_size)+block[start+len(vectors):]
    lines=['/BATCH','/CLEAR,START',database_resume(database).strip(),'/FILNAME,readonly','/GOPR']
    for line in block:
        if line=='SET,LAST':
            lines += ["FILE,'"+result_base+"',rst",'/OUTPUT,result_sets,txt','SET,LIST','/OUTPUT','SET,1,1']
        elif line=='SAVE,pilot_partial,db':lines.append('/COM,READ_ONLY_GATE_FAILED')
        else:lines.append(line)
    lines+=['/EXIT,NOSAVE']
    text='\n'.join(lines)+'\n'
    if re.search(r'^\s*(?:SOLVE|SAVE\s*,)',text,re.I|re.M):raise ValueError('Read-only export contains mutation')
    return text
