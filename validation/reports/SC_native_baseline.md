# SC Native-Scheduler Baseline (v0.15)

Date: 2026-08-16 · OCELOT native `get_next_step()` scheduler, production entry point `validation/backend.run_ocelot`

## smoke (0.5 m drift, 500 fC)

| | σx [µm] | σz [µm] | εnx |
|---|---|---|---|
| SC OFF | 725.315 | 302.024 | 0.0802 |
| SC ON | 2436.133 | 1594.948 | 0.1198 |
| Δ | +1710.8 | +1292.9 | +0.0396 |

(v0.14 manual ref @500 fC: σx 725→2436 µm +236%, σz→1595 µm +428% — manual applies SC beyond coverage and with nominal tail zstep; see SC_integration_audit §9-11)

## charge scan

| Q [fC] | σx [µm] | σz [µm] | εnx |
|---|---|---|---|
| 0 | 725.315 | 302.024 | 0.0802 |
| 10 | 787.372 | 357.164 | 0.0810 |
| 50 | 1003.635 | 543.421 | 0.0874 |
| 100 | 1230.029 | 725.959 | 0.0936 |
| 500 | 2436.133 | 1594.948 | 0.1198 |
| 1000 | 3438.521 | 2268.761 | 0.1485 |

σx(Q) monotonic: True

## convergence (500 fC)

N (mesh 63, step 1): 1e4/5e4/1e5; mesh 33/63/127; step 1/5/10 — see terminal log (tables printed above).

## full beamline (100 fC, 63³, 5e4, dz=0.001)

| | σx [µm] | σz [µm] | σδ [e-3] | εnx |
|---|---|---|---|---|
| SC OFF | 1996.205 | 474.022 | 2.9394 | 0.0804 |
| SC ON | 2557.325 | 524.873 | 4.6937 | 0.1293 |

provenance: seed=42, scheduler=ocelot_native, coverage=[0.0, 0.777], apply_count=777
