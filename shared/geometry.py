"""Validate one contiguous, explicitly positioned beamline without editing it."""
import math
from numbers import Real


def validate_geometry(cfg):
    """Return the shared geometry contract; raise ValueError on ambiguity.

    Coordinates are metres. Only 64 ULP of floating-point accumulation is
    tolerated, not a physical gap. See geometry_contract.md.
    """
    def fail(message):
        raise ValueError('Beamline geometry: ' + message)

    def number(value, label):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            fail(f'{label} must be a finite number; got {value!r}')
        return float(value)

    def same(a, b):
        return abs(a-b) <= 64*math.ulp(max(1., abs(a), abs(b)))

    if not isinstance(cfg, dict) or not isinstance(cfg.get('lattice'), dict):
        fail('configuration requires a lattice mapping')
    elements = cfg['lattice'].get('elements')
    if not isinstance(elements, list) or not elements:
        fail('lattice.elements must be a nonempty ordered list')
    cursor = 0.; names = set(); rows = []; samples = []
    for i, e in enumerate(elements):
        if not isinstance(e, dict) or not all(k in e for k in ('name','type','z_start','length')):
            fail(f'element[{i}] requires name, type, z_start and length')
        name, kind = e['name'], e['type']
        if not isinstance(name, str) or not name.strip() or name in names:
            fail(f'element[{i}] has an empty or duplicate name: {name!r}')
        names.add(name)
        if kind not in ('cathode','sample','drift','solenoid','rf_cavity'):
            fail(f'{name}: unsupported type {kind!r}')
        start = number(e['z_start'], f'{name}.z_start')
        length = number(e['length'], f'{name}.length')
        if start < 0 or length < 0:
            fail(f'{name}: z_start and length must be nonnegative')
        if kind in ('cathode','sample') and length != 0:
            fail(f'{name}: {kind} must have zero length')
        if kind in ('solenoid','rf_cavity') and length == 0:
            fail(f'{name}: {kind} must have positive length; use physics switches to disable RF')
        if not same(start, cursor):
            reason = 'gap' if start > cursor else 'overlap/out-of-order element'
            fail(f'{name}: {reason}; z_start={start:.17g} m, expected {cursor:.17g} m; '
                 'update the adjacent drift/element positions together')
        if kind == 'cathode':
            if i != 0:
                fail(f'{name}: cathode must be the first element at 0 m')
        if kind == 'sample':
            samples.append(i)
            if i != len(elements)-1:
                fail(f'{name}: sample must be the last element')
        end = start+length
        if not math.isfinite(end):
            fail(f'{name}: nonfinite element end')
        rows.append(dict(name=name, type=kind, z_start_m=start, z_end_m=end, length_m=length))
        # OCELOT assembles by lengths. Check against that actual convention.
        cursor += length
    if len(samples) != 1 or cursor <= 0:
        fail('require exactly one terminal zero-length sample and positive beamline length')
    output = cfg.get('output', {})
    if not isinstance(output, dict):
        fail('output must be a mapping')
    probes = output.get('z_diagnostics_mm', [])
    if not isinstance(probes, (list, tuple)):
        fail('output.z_diagnostics_mm must be a list of positions in mm')
    for i, value in enumerate(probes):
        pos = number(value, f'output.z_diagnostics_mm[{i}]')/1000.
        if (pos < 0 and not same(pos, 0.)) or (pos > cursor and not same(pos, cursor)):
            fail(f'diagnostic {value!r} mm is outside [0, {cursor*1000:.17g}] mm')
    return dict(sample_m=cursor, rf_entrances_m=[r['z_start_m'] for r in rows if r['type']=='rf_cavity'],
                elements=rows, convention='ordered contiguous explicit geometry; no automatic repair',
                coordinate_tolerance='64 ULP at max(1 m, coordinate magnitude)')
