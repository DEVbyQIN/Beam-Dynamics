"""Independent reference for the fixed-reference RF mathematical contract.

No production module is imported. Definitions and limits are documented in
rf_gaussian_reference_physics_note.md. This is not a tracking backend.
"""
import math
import mpmath as mp
import numpy as np

FIELDS = ('A_m2', 'B', 'C_m', 'mean_delta', 'chirp_per_m', 'sigma_delta',
          'sigma_uncorrelated_delta', 'eps_nz_mm_mrad', 'D_m2',
          'variance_nonlinear_delta', 'phase_rms_rad', 'H_linear_per_m')


def gaussian_reference(*, sigma_z_m, sigma_delta, covariance_m=0., beta,
                       gamma, energy_total_eV, voltage_V, frequency_Hz, phase_rad,
                       normalization_beta_gamma=None, method='quadrature', dps=65):
    """Centered moments of a joint Gaussian after the prescribed time kick.

    The quadrature directly integrates the time-domain gain and its residual
    after linear regression. The analytic method independently uses the
    Gaussian characteristic function. The linear method is the tangent map.
    """
    if method not in ('quadrature', 'analytic', 'linear'):
        raise ValueError('unknown reference method')
    with mp.workdps(dps):
        m = lambda value: mp.mpf(str(value))
        s, sd, C, b, g, E, V, f, phi = map(m, (sigma_z_m, sigma_delta,
            covariance_m, beta, gamma, energy_total_eV, voltage_V, frequency_Hz, phase_rad))
        if not all(mp.isfinite(x) for x in (s, sd, C, b, g, E, V, f, phi)):
            raise ValueError('nonfinite reference input')
        if s <= 0 or sd < 0 or not 0 < b < 1 or g <= 1 or E <= 0 or f <= 0:
            raise ValueError('invalid reference input')
        area_variance = sd**2-C**2/s**2
        if area_variance < 0:
            raise ValueError('Gaussian covariance is not positive semidefinite')
        bg = b*g if normalization_beta_gamma is None else m(normalization_beta_gamma)
        omega = 2*mp.pi*f
        q, amplitude = omega/(b*mp.mpf('299792458')), V/(b*b*E)
        phase_rms = q*s
        tangent = amplitude*q*mp.cos(phi)

        def gain(x):
            delta_t = -s*x/(b*mp.mpf('299792458'))
            return V*(mp.sin(phi-omega*delta_t)-mp.sin(phi))/(b*b*E)

        def expect(fn):
            density = lambda x: mp.exp(-x*x/2)/mp.sqrt(2*mp.pi)
            return mp.quad(lambda x: fn(x)*density(x), [-mp.inf, -4, 0, 4, mp.inf])

        if method == 'linear':
            mean_gain, slope, nonlinear = mp.mpf(0), tangent, mp.mpf(0)
        elif method == 'quadrature':
            mean_gain = expect(gain)
            slope = expect(lambda x: x*gain(x))/s
            nonlinear = expect(lambda x: (gain(x)-mean_gain-slope*s*x)**2)
        else:
            t = phase_rms**2
            mean_gain = amplitude*mp.sin(phi)*mp.expm1(-t/2)
            slope = amplitude*q*mp.cos(phi)*mp.exp(-t/2)
            # Even/odd Hermite residuals, nonnegative and stable at small t.
            nonlinear = amplitude**2*(mp.sin(phi)**2*mp.expm1(-t)**2/2
                +mp.cos(phi)**2*mp.exp(-t)*(mp.sinh(t)-t))
        if nonlinear < 0:
            raise ArithmeticError('insufficient precision for nonnegative residual variance')
        h = C/s**2+slope
        residual = area_variance+nonlinear
        A = s*s
        B = residual+A*h*h
        values = dict(A_m2=A, B=B, C_m=A*h, mean_delta=mean_gain,
            chirp_per_m=h, sigma_delta=mp.sqrt(B), sigma_uncorrelated_delta=mp.sqrt(residual),
            eps_nz_mm_mrad=bg*s*mp.sqrt(residual)*10**6, D_m2=A*residual,
            variance_nonlinear_delta=nonlinear, phase_rms_rad=phase_rms, H_linear_per_m=tangent)
        return dict(method=method, dps=dps, values={k:float(v) for k,v in values.items()},
                    high_precision={k:mp.nstr(v,dps) for k,v in values.items()})


def compare_references(first, second):
    """Relative differences of independently evaluated high-precision moments."""
    with mp.workdps(85):
        out = {}
        for key in FIELDS:
            a, b = mp.mpf(first['high_precision'][key]), mp.mpf(second['high_precision'][key])
            out[key] = float(abs(a-b)/max(abs(a),abs(b),mp.mpf('1e-80')))
        return out


def time_kick_on_cloud(zeta_m, delta, *, beta, energy_total_eV, voltage_V,
                       frequency_Hz, phase_rad):
    """Independent direct time formula, deliberately not production's trig identity."""
    zeta, delta = np.asarray(zeta_m,float), np.asarray(delta,float)
    delta_t = -zeta/(float(beta)*299792458.)
    relative_energy = float(voltage_V)*(np.sin(float(phase_rad)-2*np.pi*float(frequency_Hz)*delta_t)
                                      -math.sin(float(phase_rad)))
    return delta+relative_energy/(float(beta)**2*float(energy_total_eV))


def cloud_moments(zeta, delta, beta_gamma, weights=None):
    """Independent centered moments; determinant from regression residual."""
    zeta, delta = np.asarray(zeta,float), np.asarray(delta,float)
    if zeta.shape != delta.shape or zeta.ndim != 1 or not zeta.size:
        raise ValueError('cloud arrays must be nonempty matching vectors')
    w = np.ones(zeta.size) if weights is None else np.abs(np.asarray(weights,float))
    if w.shape != zeta.shape or not np.isfinite([zeta,delta,w]).all() or np.sum(w)<=0:
        raise ValueError('invalid cloud or weights')
    w = w/np.sum(w)
    mz, md = np.sum(w*zeta), np.sum(w*delta)
    z, d = zeta-mz, delta-md
    A, B, C = np.sum(w*z*z), np.sum(w*d*d), np.sum(w*z*d)
    if A <= 0:
        raise ValueError('positive longitudinal variance required')
    h = C/A
    residual = d-h*z
    W = np.sum(w*residual*residual)
    return dict(A_m2=float(A),B=float(B),C_m=float(C),mean_delta=float(md),mean_zeta_m=float(mz),
        chirp_per_m=float(h),sigma_delta=float(np.sqrt(B)),
        sigma_uncorrelated_delta=float(np.sqrt(W)),D_m2=float(A*W),
        eps_nz_mm_mrad=float(beta_gamma*np.sqrt(A*W)*1e6))


def iid_clt_halfwidth95(zeta, delta, beta_gamma):
    """Single-cloud approximate iid/CLT halfwidth, not a convergence guarantee.

    The influence function uses regression residuals to avoid subtracting
    nearly equal determinant contributions. Assumes equal iid weights.
    """
    zeta, delta = np.asarray(zeta,float), np.asarray(delta,float)
    z, d = zeta-np.mean(zeta), delta-np.mean(delta)
    A, B, C = np.mean(z*z), np.mean(d*d), np.mean(z*d)
    h, residual = C/A, d-C/A*z
    W = np.mean(residual*residual)
    if A<=0 or B<=0 or W<=0 or z.size<3:
        raise ValueError('nondegenerate cloud needed for CLT estimate')
    epsilon = beta_gamma*np.sqrt(A*W)*1e6
    influence = dict(
        sigma_delta=(d*d-B)/(2*np.sqrt(B)),
        chirp_per_m=z*residual/A,
        sigma_uncorrelated_delta=(residual*residual-W)/(2*np.sqrt(W)),
        eps_nz_mm_mrad=.5*epsilon*((z*z-A)/A+(residual*residual-W)/W),
    )
    return {key:float(1.959963984540054*np.std(value,ddof=1)/np.sqrt(z.size))
            for key,value in influence.items()}


def tabulated_sampler_reference(*, sigma_z_m, sigma_delta, beta, gamma,
                                energy_total_eV, voltage_V, frequency_Hz,
                                phase_rad, order=16):
    """Population induced by linear inversion of the 500-node +/-5-sigma CDF.

    Independently integrate the resulting piecewise-uniform density, not the
    production generator or invert_cdf. The source/version identifying that
    sampler must be saved by the study; this is not a universal PIC model.
    Initial delta is independent Gaussian. No initial correlation is assumed.
    """
    grid=np.linspace(-5.,5.,500)
    pdf=np.exp(-grid*grid/2)
    mass=.5*(pdf[:-1]+pdf[1:])*np.diff(grid)
    mass/=mass.sum()
    nodes,legendre_weights=np.polynomial.legendre.leggauss(order)
    x=(grid[:-1,None]+grid[1:,None])/2+np.diff(grid)[:,None]*nodes/2
    weights=(mass[:,None]*legendre_weights/2).ravel()
    zeta=(x*float(sigma_z_m)).ravel()
    gain=time_kick_on_cloud(zeta,np.zeros(zeta.size),beta=beta,
        energy_total_eV=energy_total_eV,voltage_V=voltage_V,
        frequency_Hz=frequency_Hz,phase_rad=phase_rad)
    measured=cloud_moments(zeta,gain,beta*gamma,weights)
    A=measured['A_m2'];h=measured['chirp_per_m']
    nonlinear=measured['sigma_uncorrelated_delta']**2
    W=float(sigma_delta)**2+nonlinear
    B=W+A*h*h
    measured.update(B=B,sigma_delta=float(np.sqrt(B)),
        sigma_uncorrelated_delta=float(np.sqrt(W)),D_m2=A*W,
        eps_nz_mm_mrad=float(beta*gamma*np.sqrt(A*W)*1e6),
        variance_nonlinear_delta=nonlinear,
        input_sigma_z_m=float(np.sqrt(A)))
    return dict(values=measured,order=order,grid_nodes=500,truncation_sigma=5.,
                density='piecewise uniform induced by linearly inverted trapezoidal CDF')


def sampler_interval_reference(*, sigma_z_m, sigma_delta, beta, gamma,
                               energy_total_eV, voltage_V, frequency_Hz,
                               phase_rad, dps=65):
    """High-precision exact interval integrals for the sampler population.

    Independent of the double-precision GL evaluation. Grid and Gaussian
    endpoint values are evaluated in high precision; differences from the
    floating-point production CDF remain roundoff, not bitwise identity.
    """
    with mp.workdps(dps):
        m=lambda value:mp.mpf(str(value))
        s,sd,b,g,E,V,f,phi=map(m,(sigma_z_m,sigma_delta,beta,gamma,
                                  energy_total_eV,voltage_V,frequency_Hz,phase_rad))
        step=mp.mpf(10)/499
        half=step/2
        grid=[-5+i*step for i in range(500)]
        mids=[(x+y)/2 for x,y in zip(grid[:-1],grid[1:])]
        masses=[(mp.exp(-x*x/2)+mp.exp(-y*y/2))*step/2 for x,y in zip(grid[:-1],grid[1:])]
        total=mp.fsum(masses)
        masses=[w/total for w in masses]
        k=2*mp.pi*f*s/(b*mp.mpf('299792458'))
        amp=V/(b*b*E)
        def sinc(x):return mp.sin(x)/x if x else mp.mpf(1)
        def cosine_expect(q):
            return mp.fsum(w*mp.cos(q*x)*sinc(q*half) for w,x in zip(masses,mids))
        F1,F2=cosine_expect(k),cosine_expect(2*k)
        sinc_prime=(k*half*mp.cos(k*half)-mp.sin(k*half))/(k*half)**2
        xsin=mp.fsum(w*(x*mp.sin(k*x)*sinc(k*half)-half*mp.cos(k*x)*sinc_prime)
                    for w,x in zip(masses,mids))
        A=s*s*mp.fsum(w*(x*x+half*half/3) for w,x in zip(masses,mids))
        mean=amp*mp.sin(phi)*(F1-1)
        C=amp*mp.cos(phi)*s*xsin
        gain_variance=amp*amp*(mp.sin(phi)**2*((1+F2)/2-F1*F1)+mp.cos(phi)**2*(1-F2)/2)
        nonlinear=gain_variance-C*C/A
        if nonlinear < 0:raise ArithmeticError('insufficient sampler reference precision')
        W=sd*sd+nonlinear
        B=W+C*C/A
        values=dict(A_m2=A,B=B,C_m=C,mean_delta=mean,chirp_per_m=C/A,
            sigma_delta=mp.sqrt(B),sigma_uncorrelated_delta=mp.sqrt(W),
            eps_nz_mm_mrad=b*g*mp.sqrt(A*W)*10**6,D_m2=A*W,
            variance_nonlinear_delta=nonlinear,input_sigma_z_m=mp.sqrt(A))
        return dict(method='high_precision_exact_piecewise_uniform_intervals',dps=dps,
            values={k:float(v) for k,v in values.items()},
            high_precision={k:mp.nstr(v,dps) for k,v in values.items()})
