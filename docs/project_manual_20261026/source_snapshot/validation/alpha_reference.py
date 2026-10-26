"""Independent scalar adaptive reference for paper Eqs.(21)-(29).

No imports from the production evaluator. Integrate infinite log intervals,
scale each positive integrand, and retain QUADPACK's numerical error estimate.
55-digit original-s anchors provide a second independent check.
"""
import warnings
import numpy as np
from scipy.integrate import quad, IntegrationWarning


def adaptive_alpha_reference(kx, ky):
    axes=np.log([kx,ky,1.])
    exponents=[(3,1,1),(1,3,1),(1,1,3),(5,1,1),(1,5,1),
               (1,1,5),(3,3,1),(3,1,3),(1,3,3)]
    factors=[kx*kx,ky*ky,kx*ky,1.5*kx**4,1.5*ky**4,3*kx*ky,
             4*kx*kx*ky*ky,kx*kx,ky*ky]
    values=[];errors=[]
    for factor,powers in zip(factors,exponents):
        def log_integrand(u):
            return np.log(factor)+2*u-.5*sum(p*np.logaddexp(2*u,2*a)
                                            for a,p in zip(axes,powers))
        shift=max(log_integrand(u) for u in axes)
        def integrand(u):
            return np.exp(log_integrand(u)-shift)
        cuts=[-np.inf,*sorted(set(axes)),np.inf]
        with warnings.catch_warnings():
            warnings.simplefilter('error',IntegrationWarning)
            parts=[quad(integrand,a,b,epsabs=1e-12,epsrel=1e-12,limit=200)
                   for a,b in zip(cuts[:-1],cuts[1:])]
        total=sum(v for v,_ in parts)
        values.append(np.exp(shift)*total)
        errors.append(sum(e for _,e in parts)/total)
    return np.array(values),max(errors)
