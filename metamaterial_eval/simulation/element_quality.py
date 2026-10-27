"""Independent corner geometry and whole-reference-domain TRI6 map checks.

For TRI6 order (I,J,K,IJ,JK,KI), det(dx/dr,dx/ds) is quadratic in r,s.
Its extrema on r>=0,s>=0,r+s<=1 occur at vertices, stationary edge points,
or an interior stationary point. Enumerate those, rather than sample a grid.
This is an analytic polynomial test evaluated in floating point with a scaled
roundoff guard, not formal interval arithmetic or a proof about arbitrary CAD.
"""
import numpy as np


def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def corner_metrics(points):
    p=np.asarray(points,dtype=float)
    if p.ndim==2:p=p[None,:,:]
    if p.ndim!=3 or p.shape[1:]!=(3,2) or not np.isfinite(p).all():
        raise ValueError('Require finite triangle corner coordinates (n,3,2)')
    u=p[:,1]-p[:,0];v=p[:,2]-p[:,0];det=cross(u,v)
    lengths=np.linalg.norm(p-np.roll(p,-1,axis=1),axis=2)
    angles=[]
    for k in range(3):
        a=p[:,(k+1)%3]-p[:,k];b=p[:,(k+2)%3]-p[:,k]
        angles.append(np.degrees(np.arctan2(np.abs(cross(a,b)),np.sum(a*b,axis=1))))
    angles=np.asarray(angles).T
    denominator=np.sum(lengths**2,axis=1)
    q=np.divide(2*np.sqrt(3)*det,denominator,out=np.zeros_like(det),where=denominator>0)
    aspect=np.divide(lengths.max(axis=1)**2,det,out=np.full_like(det,np.inf),where=det>0)
    return {'angles_deg':angles,'minimum_angle_deg':angles.min(axis=1),
            'edge_lengths':lengths,'signed_determinant':det,'signed_area':det/2,
            'quality':q,'aspect_ratio':aspect,'positive_orientation':det>0}


def quadratic_mapping(points):
    p=np.asarray(points,dtype=float)
    if p.ndim==2:p=p[None,:,:]
    if p.ndim!=3 or p.shape[1:]!=(6,2) or not np.isfinite(p).all():
        raise ValueError('Require finite TRI6 coordinates (n,6,2) in I,J,K,IJ,JK,KI order')
    p=p-p[:,0:1]  # translation avoids cancellation from the global origin
    a0=-p[:,1]+4*p[:,3];ar=4*p[:,1]-8*p[:,3]
    ass=-4*p[:,3]+4*p[:,4]-4*p[:,5]
    b0=-p[:,2]+4*p[:,5];br=ass;bs=4*p[:,2]-8*p[:,5]
    c0=cross(a0,b0);cr=cross(ar,b0)+cross(a0,br);cs=cross(ass,b0)+cross(a0,bs)
    crr=cross(ar,br);crs=cross(ar,bs)+cross(ass,br);css=cross(ass,bs)
    def value(r,s):return c0+cr*r+cs*s+crr*r*r+crs*r*s+css*s*s
    candidates=[c0,value(1,0),value(0,1)]
    for linear,quad,rbase,sbase,rdir,sdir in [(cr,crr,0,0,1,0),(cs,css,0,0,0,1),
             (cr-cs+crs-2*css,crr-crs+css,0,1,1,-1)]:
        t=np.divide(-linear,2*quad,out=np.full_like(c0,np.nan),where=quad!=0)
        v=value(rbase+rdir*t,sbase+sdir*t)
        candidates.append(np.where((t>0)&(t<1),v,np.nan))
    hdet=4*crr*css-crs**2
    stationary_r=np.divide(crs*cs-2*css*cr,hdet,out=np.full_like(c0,np.nan),where=hdet!=0)
    stationary_s=np.divide(crs*cr-2*crr*cs,hdet,out=np.full_like(c0,np.nan),where=hdet!=0)
    inside=(stationary_r>0)&(stationary_s>0)&(stationary_r+stationary_s<1)
    candidates.append(np.where(inside,value(stationary_r,stationary_s),np.nan))
    values=np.asarray(candidates)
    minimum=np.nanmin(values,axis=0);maximum=np.nanmax(values,axis=0)
    coefficients=np.column_stack([c0,cr,cs,crr,crs,css])
    # Bernstein coefficients bound the polynomial everywhere and provide an
    # additional sufficient positivity check independent of extremum locations.
    bernstein=np.column_stack([c0,c0+cr+crr,c0+cs+css,c0+cr/2,c0+cs/2,c0+(cr+cs+crs)/2])
    derivative_scale=np.maximum(np.sum(a0*a0+b0*b0+ar*ar+ass*ass+bs*bs,axis=1),np.finfo(float).tiny)
    guard=128*np.finfo(float).eps*derivative_scale
    corners=p[:,:3];expected=(corners+np.roll(corners,-1,axis=1))/2
    midpoint_error=np.linalg.norm(p[:,3:]-expected,axis=2).max(axis=1)
    return {'determinant_min':minimum,'determinant_max':maximum,'roundoff_guard':guard,
            'positive_over_reference_triangle':minimum>guard,
            'bernstein_lower_bound':bernstein.min(axis=1),
            'bernstein_positive_with_guard':bernstein.min(axis=1)>guard,
            'max_midpoint_error':midpoint_error,'coefficients':coefficients,
            'method':'analytic_quadratic_extrema_over_closed_reference_triangle',
            'limitation':'floating point with scaled guard; no formal interval arithmetic; no sampled positivity claim'}


def quality_summary(corners,mapping=None,minimum_angle=10.):
    angles=corners['minimum_angle_deg']
    result={'elements':int(len(angles)),'min_angle_deg':float(angles.min()),
            'below_angle_gate':int(np.sum(angles<minimum_angle)),
            'min_quality':float(corners['quality'].min()),'mean_quality':float(corners['quality'].mean()),
            'min_signed_corner_determinant':float(corners['signed_determinant'].min())}
    if mapping is not None:
        result['quadratic_mapping']={'method':mapping['method'],'limitation':mapping['limitation'],
            'minimum_determinant':float(mapping['determinant_min'].min()),
            'invalid_or_uncertified_elements':int(np.sum(~mapping['positive_over_reference_triangle'])),
            'bernstein_uncertified_elements':int(np.sum(~mapping['bernstein_positive_with_guard'])),
            'maximum_midpoint_error_mm':float(mapping['max_midpoint_error'].max())}
    return result
