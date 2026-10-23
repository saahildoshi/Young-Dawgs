"""Local opposing-boundary width qualification for each proposed chord.

Source/chord projection events divide bounded, single-valued boundary graphs
into affine slabs. The maximum width loss over the qualifying parts of each
slab is evaluated at interval endpoints. This covers a registered finite set of
directions and width horizon; it is not a universal continuous-neck theorem.
"""
import math
import time
import numpy as np
import shapely
from shapely import box
from ..protected.model import signed_area

DIRECTIONS=((1.,0.),(math.sqrt(.5),math.sqrt(.5)),(0.,1.),(-math.sqrt(.5),math.sqrt(.5)))


def frames(model):
    if not hasattr(model,'_c1_width_frames'):
        orient=np.array([np.sign(signed_area(x))*(1 if r['role']=='shell' else -1) for x,r in zip(model.xy,model.rings)])
        model._c1_width_frames=[]
        for direction in DIRECTIONS:
            d=np.asarray(direction);n=np.array([-d[1],d[0]])
            u=model.segments[:,:,0]*n[0]+model.segments[:,:,1]*n[1]
            v=model.segments[:,:,0]*d[0]+model.segments[:,:,1]*d[1]
            model._c1_width_frames.append((d,n,u,v,orient[model.owner]))
    return model._c1_width_frames


def qualifying_intervals(a,b,limit):
    """Closed t-subinterval where affine a+(b-a)t <= limit."""
    if a<=limit and b<=limit:return [(0.,1.)]
    if a>limit and b>limit:return []
    t=float(np.clip((limit-a)/(b-a),0,1))
    return [(0.,t)] if a<=limit else [(t,1.)]


def affine_loss(old,new,limit):
    intervals=qualifying_intervals(*old,limit)+qualifying_intervals(*new,limit)
    delta=np.asarray(old)-np.asarray(new)
    choices=[(float(delta[0]+t*(delta[1]-delta[0])),float(t)) for interval in intervals for t in interval]
    return max(choices,default=(0.,.5))


def _unique(values,tol):
    a=np.sort(np.asarray(values,float));return a[np.r_[True,np.diff(a)>tol]]


def chord_width_gate(model,ri,vertex_ids,xy,settings):
    started=time.perf_counter();allow=settings['numeric_allowance'];horizon=settings['qualifying_width']
    chord=np.array([xy[0],xy[-1]],float);hull=shapely.MultiPoint(xy).convex_hull
    result={'passed':True,'failed_constraints':[],'directions':[],'worst_one_sided_loss':0.,'witnesses':[],
            'qualifying_width':horizon,'numeric_allowance':allow,'uncertainty_restores_source':True}
    if hull.geom_type!='Polygon':
        result.update(reason='Collinear source/chord has no material change',seconds=time.perf_counter()-started);return result
    # Radius includes the independently registered displacement ceiling, so a
    # formerly wider gap that becomes qualifying cannot escape the query.
    radius=horizon+math.sqrt(.5)+allow
    x0,y0,x1,y1=hull.bounds;indices=np.sort(model.tree.query(box(x0-radius,y0-radius,x1+radius,y1+radius),predicate='intersects'))
    owned_global=set(map(int,model.offsets[ri]+vertex_ids[:-1]));owned=np.array([int(i) in owned_global for i in indices])
    crossings=shapely.intersection(shapely.LineString(xy),shapely.LineString(chord))
    extra=shapely.get_coordinates(crossings)
    for direction_index,(d,n,all_u,all_v,orient) in enumerate(frames(model)):
        if [0,45,90,135][direction_index] not in settings['directions_degrees']:continue
        u=all_u[indices];v=all_v[indices];du=u[:,1]-u[:,0];dv=v[:,1]-v[:,0]
        cu=chord[:,0]*n[0]+chord[:,1]*n[1];cv=chord[:,0]*d[0]+chord[:,1]*d[1]
        pu=xy[:,0]*n[0]+xy[:,1]*n[1]
        row={'direction_degrees':[0,45,90,135][direction_index],'slabs':0,'affected_slabs':0,'bounded_sections':0,'qualifying_sections':0,'wide_or_open_sections':0,'ambiguous_slabs':0}
        if abs(cu[1]-cu[0])<=allow:
            # A genuinely noncollinear chain with projection excursion cannot
            # be certified by a single replacement graph in this frame.
            if pu.max()-pu.min()>allow:
                row['ambiguous_slabs']=1;result['failed_constraints'].append('width_projection_not_single_valued')
            result['directions'].append(row);continue
        low,high=min(cu),max(cu)
        if pu.min()<low-allow or pu.max()>high+allow:
            row['ambiguous_slabs']=1;result['failed_constraints'].append('width_projection_not_single_valued')
            result['directions'].append(row);continue
        events=list(u.ravel())+[low,high]+list(pu)
        if len(extra):events.extend(extra[:,0]*n[0]+extra[:,1]*n[1])
        events=_unique([x for x in events if low-allow<=x<=high+allow],allow)
        left=events[:-1];right=events[1:];valid=right-left>allow;left=left[valid];right=right[valid];mid=(left+right)/2
        row['slabs']=len(mid)
        if not len(mid):result['directions'].append(row);continue
        active=(np.minimum(u[:,0],u[:,1])[None,:]<=mid[:,None])&(mid[:,None]<np.maximum(u[:,0],u[:,1])[None,:])&(np.abs(du)[None,:]>allow)
        safe_du=np.where(abs(du)>allow,du,1.)
        positions=v[:,0][None,:]+(mid[:,None]-u[:,0][None,:])*dv[None,:]/safe_du[None,:]
        own_active=active&owned[None,:];count=own_active.sum(axis=1)
        if np.any(count!=1):
            row['ambiguous_slabs']=int(np.count_nonzero(count!=1));result['failed_constraints'].append('width_projection_not_single_valued')
            result['directions'].append(row);continue
        own_ix=own_active.argmax(axis=1);old_mid=positions[np.arange(len(mid)),own_ix]
        new_mid=cv[0]+(mid-cu[0])*(cv[1]-cv[0])/(cu[1]-cu[0])
        affected=np.abs(old_mid-new_mid)>allow;row['affected_slabs']=int(affected.sum())
        for k in np.flatnonzero(affected):
            others=active[k]&~owned
            for sign in [-1,1]:
                eligible=others & ((positions[k]-old_mid[k])*sign>allow)
                if not eligible.any():row['wide_or_open_sections']+=1;continue
                distance=np.where(eligible,(positions[k]-old_mid[k])*sign,np.inf);j=int(np.argmin(distance))
                # Piecewise-affine source and candidate widths, evaluated on
                # one-sided slab closures; no finite raster sample proves this.
                ts=np.array([left[k],right[k]])
                old=v[own_ix[k],0]+(ts-u[own_ix[k],0])*dv[own_ix[k]]/safe_du[own_ix[k]]
                opposing=v[j,0]+(ts-u[j,0])*dv[j]/safe_du[j]
                new=cv[0]+(ts-cu[0])*(cv[1]-cv[0])/(cu[1]-cu[0])
                widths=(opposing-old)*sign;candidate_widths=(opposing-new)*sign
                row['bounded_sections']+=1
                if min(*widths,*candidate_widths)>horizon+allow:row['wide_or_open_sections']+=1;continue
                row['qualifying_sections']+=1
                if min(*widths,*candidate_widths)<-allow:
                    result['failed_constraints'].append('width_opposing_boundary_order_uncertain');continue
                loss,t=affine_loss(widths,candidate_widths,horizon)
                solid_positive=bool(orient[indices[own_ix[k]]]*(-du[own_ix[k]])>0)
                phase='solid' if (solid_positive if sign>0 else not solid_positive) else 'void'
                if loss>allow:
                    result['failed_constraints'].append('qualifying_'+phase+'_width_loss')
                    # Keep the extremal affine closure and an interior sample;
                    # a projection-event endpoint can have two one-sided values.
                    cutoff=float(left[k]+t*(right[k]-left[k]));source_width=float(widths[0]+t*(widths[1]-widths[0]));new_width=float(candidate_widths[0]+t*(candidate_widths[1]-candidate_widths[0]))
                    witness={'direction_degrees':row['direction_degrees'],'phase':phase,'projection_slab':[float(left[k]),float(right[k])],
                        'one_sided_cut':cutoff,'source_width_limit':source_width,'candidate_width_limit':new_width,'loss_limit':loss,
                        'source_segment':int(indices[own_ix[k]]),'opposing_segment':int(indices[j]),
                        'source_xy':model.segments[indices[own_ix[k]]].tolist(),'opposing_xy':model.segments[indices[j]].tolist(),
                        'mid_slab_cut':float(mid[k]),'mid_slab_width_before':float(distance[j]),
                        'mid_slab_width_after':float((positions[k,j]-new_mid[k])*sign),
                        'interpretation':'Affine one-sided slab supremum; event coordinate itself can have different closed-set section topology.'}
                    if len(result['witnesses'])<8:result['witnesses'].append(witness)
                    result['worst_one_sided_loss']=max(result['worst_one_sided_loss'],loss)
        result['directions'].append(row)
    result['failed_constraints']=sorted(set(result['failed_constraints']));result['passed']=not result['failed_constraints'];result['seconds']=time.perf_counter()-started
    return result
