"""Draft MAPDL field exporter; numeric acceptance is handled separately."""


def field_export_macro(node_count, contact):
    lines=['! DRAFT_UNVERIFIED: validate *GET/ETABLE output against installed release',
           '/POST1','ALLSEL,ALL','SET,LAST','*GET,NSETS,ACTIVE,0,SET,NSET','SET,FIRST',
           '*CFOPEN,nodal_fields,csv','*VWRITE',
           "('set,pseudo_time,node,ux_mm,uy_mm,syy_MPa,seqv_MPa,elastic_eyy')",'*DO,JJ,1,NSETS',
           '*GET,TNOW,ACTIVE,0,SET,TIME','ESEL,S,TYPE,,1',f'*DO,NN,1,{node_count}',
           '*GET,UXV,NODE,NN,U,X','*GET,UYV,NODE,NN,U,Y','*GET,SYV,NODE,NN,S,Y',
           '*GET,SEQV,NODE,NN,S,EQV','*GET,EYV,NODE,NN,EPEL,Y',
           '*VWRITE,JJ,TNOW,NN,UXV,UYV,SYV,SEQV,EYV',
           "(F8.0,',',E16.8,',',F12.0,5(',',E16.8))",'*ENDDO','ALLSEL,ALL',
           '*IF,JJ,LT,NSETS,THEN','SET,NEXT','*ENDIF','*ENDDO','*CFCLOS']
    if contact:
        lines+=['SET,FIRST','*CFOPEN,contact_fields,csv','*VWRITE',
                "('set,pseudo_time,pair,element,status,pressure_MPa,penetration_mm,gap_mm')",
                '*DO,JJ,1,NSETS','*GET,TNOW,ACTIVE,0,SET,TIME',
                '*DO,PAIR,1,2','*IF,PAIR,EQ,1,THEN','CMSEL,S,BOTTOM_CONTACT','*ELSE','CMSEL,S,TOP_CONTACT','*ENDIF',
                'ETABLE,ERAS','ETABLE,CSTAT,CONT,STAT','ETABLE,CPRES,CONT,PRES',
                'ETABLE,CPEN,CONT,PENE','ETABLE,CGAP,CONT,GAP','*GET,NCONTACT,ELEM,0,COUNT','EID=0',
                '*DO,KK,1,NCONTACT','EID=ELNEXT(EID)',
                '*GET,STATV,ELEM,EID,ETAB,CSTAT','*GET,PRESV,ELEM,EID,ETAB,CPRES',
                '*GET,PENV,ELEM,EID,ETAB,CPEN','*GET,GAPV,ELEM,EID,ETAB,CGAP',
                '*VWRITE,JJ,TNOW,PAIR,EID,STATV,PRESV,PENV,GAPV',
                "(F8.0,',',E16.8,',',F4.0,',',F12.0,4(',',E16.8))",'*ENDDO','ALLSEL,ALL','*ENDDO',
                '*IF,JJ,LT,NSETS,THEN','SET,NEXT','*ENDIF','*ENDDO','*CFCLOS']
    return '\n'.join(lines+['ALLSEL,ALL','FINISH'])+'\n'
