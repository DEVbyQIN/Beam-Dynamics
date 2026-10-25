"""Paper SC coefficients by checked positive quadrature, without interpolation.

See alpha_coefficients_physics_note.md for definitions, tail bounds and scope.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
import numpy as np

KEYS = ('x', 'y', 'z', 'xx', 'yy', 'zz', 'xy', 'xz', 'yz')
RATIO_RANGE = (1e-6, 1e6)
RELATIVE_CHECK = 5e-11
TAIL_RELATIVE_BOUND = 2**3.5 * (np.exp(-36.) + np.exp(-54.))
_POWERS = np.array([(3,1,1), (1,3,1), (1,1,3), (5,1,1), (1,5,1),
                    (1,1,5), (3,3,1), (3,1,3), (1,3,3)], float)
_RECORD = ContextVar('ag_alpha_record', default=None)


@dataclass
class EvaluationRecord:
    calls: int = 0
    minimum: float = np.inf
    maximum: float = -np.inf
    max_order_difference: float = 0.
    max_order: int = 0

    def as_dict(self):
        return dict(method='composite_log_Gauss_Legendre',
                    numerical_ratio_range=list(RATIO_RANGE), calls=self.calls,
                    actual_ratio_min=self.minimum if self.calls else None,
                    actual_ratio_max=self.maximum if self.calls else None,
                    relative_refinement_limit=RELATIVE_CHECK,
                    max_relative_refinement_observed=self.max_order_difference,
                    max_order_used=self.max_order,
                    relative_tail_bound=float(TAIL_RELATIVE_BOUND),
                    clipped_calls=0, scope='all coefficient requests, including ODE trial stages',
                    physical_model_acceptance=False)


@contextmanager
def record_evaluations():
    record = EvaluationRecord()
    token = _RECORD.set(record)
    try:
        yield record
    finally:
        _RECORD.reset(token)


def _ratios(kx, ky):
    try:
        if np.ndim(kx) or np.ndim(ky):
            raise ValueError
        x, y = float(kx), float(ky)
    except (ValueError, TypeError, OverflowError):
        raise ValueError('alpha kx/ky must be scalar ratios') from None
    if (not np.isfinite([x,y]).all() or min(x,y)<RATIO_RANGE[0]
            or max(x,y)>RATIO_RANGE[1]):
        raise ValueError(f'alpha kx/ky outside validated numerical range {RATIO_RANGE}: '
                         f'kx={x}, ky={y}; no clipping or extrapolation')
    return x, y


@lru_cache(maxsize=4)
def _rule(order):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    nodes.setflags(write=False); weights.setflags(write=False)
    return nodes, weights


def _integral(log_axes, log_coefficients, order):
    lo, hi = log_axes.min()-18., log_axes.max()+18.
    edges = np.linspace(lo, hi, int(np.ceil((hi-lo)/2.))+1)
    nodes, weights = _rule(order)
    half = np.diff(edges)/2.
    u = ((edges[:-1,None]+edges[1:,None])/2.+half[:,None]*nodes).ravel()
    w = (half[:,None]*np.broadcast_to(weights, (half.size,order))).ravel()
    denominator = np.logaddexp(2*u[None,:], 2*log_axes[:,None])
    log_f = log_coefficients[:,None]+2*u[None,:]-.5*_POWERS@denominator
    return np.exp(log_f)@w


@lru_cache(maxsize=256)
def _evaluate(x, y):
    a = np.log([x,y,1.]); lx, ly = a[:2]
    c = np.array([2*lx,2*ly,lx+ly,np.log(1.5)+4*lx,
                  np.log(1.5)+4*ly,np.log(3.)+lx+ly,
                  np.log(4.)+2*lx+2*ly,2*lx,2*ly])
    previous = _integral(a,c,16)
    for order in (32,64,128):
        current = _integral(a,c,order)
        if not np.isfinite(current).all() or np.any(current<=0):
            raise RuntimeError('alpha quadrature produced a nonpositive/nonfinite coefficient')
        difference = float(np.max(np.abs(current-previous)/current))
        if difference <= RELATIVE_CHECK:
            return tuple(current), difference, order
        previous = current
    raise RuntimeError(f'alpha quadrature failed refinement check at kx={x}, ky={y}: {difference}')


def compute_all_alpha(kx, ky):
    """Return all nine dimensionless coefficients; invalid inputs fail explicitly."""
    x, y = _ratios(kx,ky)
    values, difference, order = _evaluate(x,y)
    record = _RECORD.get()
    if record is not None:
        record.calls += 1
        record.minimum = min(record.minimum,x,y)
        record.maximum = max(record.maximum,x,y)
        record.max_order_difference = max(record.max_order_difference,difference)
        record.max_order = max(record.max_order,order)
    return dict(zip(KEYS,values))  # copy: callers cannot poison the exact-key cache


alpha_at = compute_all_alpha


def get_alpha_interpolators():
    """Legacy initialization hook; scalar component calls remain compatible.

    No interpolation table is built. Production uses alpha_at directly.
    """
    _rule(16); _rule(32)
    def component(key):
        return lambda x,y: np.array([[compute_all_alpha(x,y)[key]]])
    return {key:component(key) for key in KEYS}
