"""Explicit native far-field availability plus independent quadratic separation."""
from types import SimpleNamespace
import numpy as np
from .contact_setup import platen_plan


def quadratic_range(values):
    """Whole-edge extrema for values ordered I,J,midside."""
    v=np.asarray(values);a=2*(v[:,0]+v[:,1]-2*v[:,2]);b=4*v[:,2]-3*v[:,0]-v[:,1];c=v[:,0]
    t=np.divide(-b,2*a,out=np.full_like(a,np.nan),where=a!=0)
    middle=np.where((t>0)&(t<1),a*t*t+b*t+c,np.nan)
    return np.nanmin(np.column_stack([v[:,:2],middle]),axis=1),np.nanmax(np.column_stack([v[:,:2],middle]),axis=1)


def validate_inventory(status,values,model,element_count):
    expected=model['contact_elements'];available={};offset=element_count
    for pair,group in [(1,'bottom'),(2,'top')]:
        rows=status[status[:,0]==pair];offset+=2
        if len(rows)!=expected[group] or not np.array_equal(rows[:,1],np.arange(offset+1,offset+expected[group]+1)):raise ValueError('Incomplete/incorrect native contact-status inventory')
        if not np.isin(rows[:,2],[0,1,2,3]).all():raise ValueError('Invalid native whole-element contact status')
        actual=values[values[:,0]==pair];stored=rows[rows[:,2]>0]
        if len(actual)!=len(stored) or not np.array_equal(actual[:,:3],stored):raise ValueError('Contact records do not match native nonfarfield status inventory')
        available[group]=len(stored);offset+=expected[group]
    if len(status)!=sum(expected.values()) or len(values)!=sum(available.values()):raise ValueError('Extra contact pair/record')
    return available


def certify_farfield_separation(mesh,deformed,model,status,top_uy,tolerance=1e-8):
    width=model['config']['width'];height=model['config']['height'];plan=platen_plan(mesh,SimpleNamespace(height=height));records=[]
    for pair,group in [(1,'bottom'),(2,'top')]:
        rows=status[status[:,0]==pair];mask=rows[:,2]==0;edges=np.asarray(plan[group]['edges'])[mask]
        if not len(edges):records.append({'pair':group,'native_farfield_elements':0,'minimum_certified_axis_separation_mm':None});continue
        xy=np.asarray(deformed)[edges];xmin,xmax=quadratic_range(xy[:,:,0]);ymin,ymax=quadratic_range(xy[:,:,1])
        vertical=ymin if pair==1 else height+top_uy-ymax
        outside=np.maximum(-.05*width-xmax,xmin-1.05*width)
        separation=np.maximum(vertical,outside)
        if not np.all(separation>tolerance):raise ValueError('Native farfield edge is not independently separated from the finite platen')
        records.append({'pair':group,'native_farfield_elements':len(edges),'minimum_certified_axis_separation_mm':float(separation.min()),
            'minimum_signed_normal_clearance_mm':float(vertical.min()),'outside_finite_platen_edges':int(np.sum(outside>tolerance)),
            'tolerance_mm':tolerance,'method':'Analytic quadratic coordinate extrema with floating-point guard; positive normal clearance OR whole edge outside finite target x range',
            'missing_records':'Native whole-element ETABLE NMISC19 status0; pressure/gap/FY not stored and not filled with invented values'})
    return records
