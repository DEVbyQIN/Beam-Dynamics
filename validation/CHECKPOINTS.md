
# ═══════════════════════════════════════════════════════════════════════
# STATUS: R56 LONGITUDINAL ITEM — RESOLVED (2026-08-01)
# ═══════════════════════════════════════════════════════════════════════
# Root cause: the shared momentum deviation delta_p = Δp/p0 was assigned
# directly to OCELOT's native sixth coordinate p_oc = ΔE/(c·p0).
# Adapter (validation/backend.py::run_ocelot):
#   input  : p_oc = beta0 * delta_p
#   kick   : rparticles[5] += beta0 * d_delta_p
#   output : reported delta_p = p_oc / beta0
# Result: σ_z/σ_t agreement at the sample plane < 1% (previously ~2.3×);
# full-beamline σ_z/σ_t promoted from diagnostic to quantitative (5%).
#
# Historical entries below that reference "OCELOT frozen", "1/beta",
# "R56 ... deferred", or "R56 ... open item" are SUPERSEDED by this status
# and are retained for provenance only — do not treat them as current.
# ═══════════════════════════════════════════════════════════════════════

## [drift] 2026-08-01 15:31
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.29879675226900554, 'sigma_y_um': 0.15982838313672834, 'sigma_z_um': 181.87838664078194, 'eps_nx_mm_mrad': 0.2464934624766771, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-01 15:31
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-01 15:31
  OCELOT: thin longitudinal kick, dδ/dz=+61034793838687690752.00 m^-1, sigma_delta=2.92e-3 (matches momentum-chirp reference)
  AG: continuous RF region, h=-310.9 m^-2, sigma_delta=28.10e-3, H_eff=+93.7 m^-1 (~0.0× reference)
  OPEN ITEM: AG rf_chirp_rate uses γ^3 (not γ) → different σ_δ growth and longitudinal defocusing (transverse RF force) not present in the OCELOT kick. Do NOT tune; needs physics decision.
  sigma_z: OCELOT frozen (no tau transport, known); AG grows via chirp.

## [rf] 2026-08-01 15:32
  OCELOT: thin longitudinal kick, dδ/dz=-9.78 m^-1, sigma_delta=2.93e-3 (matches momentum-chirp reference)
  AG: continuous RF region, h=-310.9 m^-2, sigma_delta=28.10e-3, H_eff=+93.7 m^-1 (-9.6× reference)
  OPEN ITEM: AG rf_chirp_rate uses γ^3 (not γ) → different σ_δ growth and transverse RF defocusing not present in the OCELOT kick. Do NOT tune; needs a physics decision.
  sigma_z: OCELOT frozen (no tau transport, known); AG grows via chirp.

## [drift] 2026-08-01 15:32
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3403887830670988, 'sigma_y_um': 0.5700120347139312, 'sigma_z_um': 180.59628047354664, 'eps_nx_mm_mrad': 0.34466167137940185, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-01 15:32
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-01 15:32
  OCELOT: thin longitudinal kick, dδ/dz=-9.78 m^-1, sigma_delta=2.92e-3 (matches momentum-chirp reference)
  AG: continuous RF region, h=-310.9 m^-2, sigma_delta=28.10e-3, H_eff=+93.7 m^-1 (-9.6× reference)
  OPEN ITEM: AG rf_chirp_rate uses γ^3 (not γ) → different σ_δ growth and transverse RF defocusing not present in the OCELOT kick. Do NOT tune; needs a physics decision.
  sigma_z: OCELOT frozen (no tau transport, known); AG grows via chirp.

## [longitudinal-transport] 2026-08-01
  ROOT CAUSE: OCELOT tau "frozen" = beam-energy unit bug, not SecondTM.
  generate_parray(energy=E_keV/1000=0.1) -> 0.1 GeV TOTAL (gamma=195.7, beta~1)
  -> drift R56 = -L/(beta^2 gamma^2) ~ -1.3e-5 (9e4x too small) -> tau invisible.
  FIX (Option A): energy = (E_keV+511)*1e-6 GeV (6.11e-4) -> gamma=1.1957,
    R56=-1.164, native tau_f = tau_i + R56*delta works (verified 2327um).
  AG uses spatial z, R56_z=+L/gamma^2; OCELOT tau, R56_tau=-L/(beta^2 gamma^2);
  mapped spatial transport differs by 1/beta - flagged for validation.
  No hidden manual correction; native OCELOT transport preferred.

## [drift] 2026-08-01 16:42
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.6099655144894097, 'sigma_y_um': 0.6003845774093295, 'sigma_z_um': 167.74547867139705, 'eps_nx_mm_mrad': 0.294376741182338, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [rf] 2026-08-01 16:42
  OCELOT: thin longitudinal kick, dδ/dz=-9.78 m^-1, sigma_delta=2.96e-3 (matches momentum-chirp reference)
  AG: continuous RF region, h=-310.9 m^-2, sigma_delta=28.10e-3, H_eff=+93.7 m^-1 (-9.6× reference)
  OPEN ITEM: AG rf_chirp_rate uses γ^3 (not γ) → different σ_δ growth and transverse RF defocusing not present in the OCELOT kick. Do NOT tune; needs a physics decision.
  sigma_z: OCELOT frozen (no tau transport, known); AG grows via chirp.

## [drift] 2026-08-01 16:44
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.2701122803801473, 'sigma_y_um': 0.44709052513388714, 'sigma_z_um': 168.61470342081154, 'eps_nx_mm_mrad': 0.2970824963782701, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-01 16:44
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-01 16:44
  OCELOT: thin longitudinal kick, dδ/dz=-9.78 m^-1, sigma_delta=2.95e-3 (matches momentum-chirp reference)
  AG: continuous RF region, h=-310.9 m^-2, sigma_delta=28.10e-3, H_eff=+93.7 m^-1 (-9.6× reference)
  OPEN ITEM: AG rf_chirp_rate uses γ^3 (not γ) → different σ_δ growth and transverse RF defocusing not present in the OCELOT kick. Do NOT tune; needs a physics decision.
  OCELOT sigma_z now transports natively (energy fix); σ_δ kick ~2.9e-3 drives σ_z via R56 in the downstream drift.

## [longitudinal-transport-implementation] 2026-08-01
  IMPLEMENTED: OCELOT beam energy fix energy=(E_keV+511)*1e-6 GeV (total) across
  framework backend + all GPT模拟 route/benchmark files; sigma_tau=sigma_z/beta.
  Removed manual tau override in GPT模拟/bug/ued_beamline.py (native OCELOT R56).
  No OCELOT physics modified, no custom R56, no hidden correction.
  RESULTS: drift OCELOT sigma_z 299->315um (native transport works);
    rf OCELOT sigma_z 298->1114um (kick + R56); sigma_delta maintained
    (drift 0.04%; rf kick 2.95e-3 matches reference). Solenoid unchanged (0.40%).
  Changelog: CHANGELOG_longitudinal_transport.md

## [drift] 2026-08-01 22:20
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.12704274078725672, 'sigma_y_um': 0.170309107464647, 'sigma_z_um': 2.1204327122855466, 'eps_nx_mm_mrad': 0.08737106294094402, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-01 22:20
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-01 22:20
  OCELOT: thin longitudinal kick, dδ/dz=-9.78 m^-1, sigma_delta=2.95e-3 (matches momentum-chirp reference)
  AG: continuous RF region, h=-310.9 m^-2, sigma_delta=0.10e-3, H_eff=+0.3 m^-1 (-0.0× reference)
  OPEN ITEM: AG rf_chirp_rate uses γ^3 (not γ) → different σ_δ growth and transverse RF defocusing not present in the OCELOT kick. Do NOT tune; needs a physics decision.
  OCELOT sigma_z now transports natively (energy fix); σ_δ kick ~2.9e-3 drives σ_z via R56 in the downstream drift.

## [drift] 2026-08-01 22:49
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.1718043457475445, 'sigma_y_um': 0.7697429941398992, 'sigma_z_um': 1.4147540445451403, 'eps_nx_mm_mrad': 0.19123683815962964, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-01 22:50
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-01 22:50
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=535 um (PASS)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [rf-standardization] 2026-08-01
  IMPLEMENTED Option A (thin-lens in both, transverse RF kept in both):
  - AG: continuous chirp/acceleration disabled; apply_rf_thin_lens(H=-9.78)
    at z_rf (existing AG function); RF transverse force kept (ef_rf).
  - OCELOT: longitudinal kick + transverse kick x'+=K_trans*x, K_trans=-2.68 m^-1
    (Panofsky-Wenzel, AG-consistent). Added to validation/backend.py,
    GPT模拟/ued_beamline_v2.py.
  RESULTS (test_rf): sigma_delta AG 2.953 vs OCELOT 2.946e-3 (0.24% PASS);
    sigma_x 542 vs 535 um (2.8% PASS). Full-beamline unified compare:
    sigma_x 1251.7 vs 1259.9 (0.65%), sigma_delta both 2.95e-3.
  DEFERRED: sigma_z compression magnitude ~1/beta (OCELOT R56=-L/(beta^2 gamma^2)
    vs exact -L/(beta gamma^2)); AG 477 vs GPT 1107 um at sample. Documented,
    not fixed (user decision).

## [drift] 2026-08-03 17:00
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.22160884979612466, 'sigma_y_um': 0.39296896233198914, 'sigma_z_um': 1.7004844603205358, 'eps_nx_mm_mrad': 0.08294943696211397, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 17:00
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 17:00
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=535 um (PASS)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [drift] 2026-08-03 17:09
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.14691950421169578, 'sigma_y_um': 0.5161522061370406, 'sigma_z_um': 1.1537212119168365, 'eps_nx_mm_mrad': 0.16581678155733576, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 17:09
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1915.3 sy=1917.7 um
  AG(off) vs OCELOT sigma_x max dev = 0.36% (<1% PASS) | AG(on) = 390.16% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 17:09
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=542 um (PASS)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [drift] 2026-08-03 17:09
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.1127544845453477, 'sigma_y_um': 0.7554260003121684, 'sigma_z_um': 1.1526463449952002, 'eps_nx_mm_mrad': 0.009862080646881233, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 17:09
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1915.3 sy=1917.7 um
  AG(off) vs OCELOT sigma_x max dev = 0.36% (<1% PASS) | AG(on) = 390.16% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 17:10
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=542 um (PASS)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [drift] 2026-08-03 17:38
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.17174508479895925, 'sigma_y_um': 0.44835657065972806, 'sigma_z_um': 1.8294696903326784, 'eps_nx_mm_mrad': 0.15558367400478407, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 17:38
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 17:38
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=535 um (PASS)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [drift] 2026-08-03 19:30
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 29.299455128657463, 'sigma_y_um': 0.32358879564281207, 'sigma_z_um': 2.059233178386511, 'eps_nx_mm_mrad': nan, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: FAIL (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 19:30
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=2034.1 sy=2727.6 um
  AG(off) vs OCELOT sigma_x max dev = 29.30% (<1% PASS) | AG(on) = 400.44% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 19:30
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.965e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=534 um (FAIL)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [drift] 2026-08-03 20:19
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 29.299455128657463, 'sigma_y_um': 0.32358879564281207, 'sigma_z_um': 2.059233178386511, 'eps_nx_mm_mrad': nan, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: FAIL (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 20:19
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=2034.1 sy=2727.6 um
  AG(off) vs OCELOT sigma_x max dev = 29.30% (<1% PASS) | AG(on) = 400.44% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 20:19
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.965e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=534 um (FAIL)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [drift] 2026-08-03 20:37
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3153789820877234, 'sigma_y_um': 0.28892308804232353, 'sigma_z_um': 2.253476965205138, 'eps_nx_mm_mrad': 0.3370803427228065, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 20:37
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 20:37
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=542 vs OCELOT=535 um (PASS)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [geometry-refactor] 2026-08-01
  lattice.elements = ONLY geometry source (name/type/z_start/length/parameters);
  removed solenoid:/rf_cavity: sections. Multi-instance solenoids/RF supported
  (removed next() assumptions in backend adapters). No physics change.
  Verified: AG bit-identical (1e-15); OCELOT solenoid/rf bit-identical (1e-12);
  drift OCELOT <=0.66% = pre-existing unseeded-MC noise (first generate_parray
  per process). All tests PASS. Reverted a seed-before-generate_parray attempt
  (double seed(42) caused spurious x-x' correlation).
  Changelog: CHANGELOG_geometry_refactor.md

## [drift] 2026-08-03 21:20
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.33746111448910016, 'sigma_y_um': 0.3399482596623116, 'sigma_z_um': 95.2096710692012, 'eps_nx_mm_mrad': 0.10017553451896813, 'sigma_delta_e3': 2854.2248309188917}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: FAIL (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 21:20
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 21:20
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [full] 2026-08-03 21:20
  full beamline: sample devs — σ_x 51.58%, σ_y 23.95%, σ_δ 0.23%, ε_nx 0.14%, ε_ny 0.09% (FAIL)
  R56 diag: σ_z AG 477 vs OCELOT 1114 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [full] 2026-08-03 21:58
  full beamline: sample devs — σ_x 0.13%, σ_y 0.07%, σ_δ 0.16%, ε_nx 0.30%, ε_ny 0.13% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 1115 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-03 22:11
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.13402773299218995, 'sigma_y_um': 0.25733149381807197, 'sigma_z_um': 95.17603346380264, 'eps_nx_mm_mrad': 0.1547990237712882, 'sigma_delta_e3': 2854.2248309188917}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: FAIL (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-03 22:11
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-03 22:11
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [full] 2026-08-03 22:11
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.23%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 1114 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-03 22:23
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.5810635423457002, 'sigma_y_um': 0.19268252341831665, 'sigma_z_um': 95.20539655085784, 'eps_nx_mm_mrad': 0.6003545000103752, 'sigma_delta_e3': 2854.2248309188917}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: FAIL (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [drift] 2026-08-04 08:05
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.2547608289110394, 'sigma_y_um': 0.23029661603099802, 'sigma_z_um': 2.259078650588078, 'eps_nx_mm_mrad': 0.2460874220300468, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [drift] 2026-08-04 08:14
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.6100028693434523, 'sigma_y_um': 0.4481548653633526, 'sigma_z_um': 1.6152334319928932, 'eps_nx_mm_mrad': 0.6240702676309259, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-04 08:15
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-04 08:15
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.946e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [full] 2026-08-04 08:15
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.23%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 1114 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [physics-switches + full-beamline] 2026-08-01
  Added shared physics_switches (rf_longitudinal_kick=true, rf_transverse_kick=false)
  read identically by both adapters (run_ag/run_ocelot via switches param).
  - transverse OFF: longitudinal thin-lens kick retained, NO RF transverse force.
  - transverse ON: existing K_trans implementation (unchanged).
  - test_rf switch check: AG σ_x 1118.9->542.4 (OFF->ON, -51.5%),
    OCELOT 1119.6->535.3 (-52.2%); both read same switch.
  NEW validation/test_full_beamline.py (full lattice cathode->sample, transverse OFF):
  - sample-plane PASS: σ_x 0.26%, σ_y 0.39%, σ_δ 0.23%, ε_nx 0.14%, ε_ny 0.09%.
  - σ_z/σ_t diag only: AG 477 vs OCELOT 1114 um (57%, R56 open item).
  - report: validation/reports/full_beamline_validation.md
  Fix during dev: rf_elems must be section-filtered (was applying RF lens in the
  drift section after switch refactor).

## [full] 2026-08-04 10:52
  full beamline: sample devs — σ_x 0.08%, σ_y 0.56%, σ_δ 0.30%, ε_nx 0.37%, ε_ny 0.76% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 1120 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [r56-convention-audit] 2026-08-01
  AUDIT RESOLVED (classification B — input delta-variable convention mismatch):
  OCELOT rparticles[5] = dE/(c*p0) (NOT Δp/p), documented at
  cpbd/beam/generator.py:51 & particle.py:20; drift R56 = -L/(β²γ²)
  (r_matrix.py:81) is EXACT for the pair (τ=c*t, p=dE/(c*p0)).
  AG uses δ_p = Δp/p0 with R56_z = L/γ² (exact).
  Framework feeds same number to both → OCELOT physical δ_p off by 1/β.
  Measured: raw slope = R56_tm = -1.163624 (rel err 1e-5); formal conversion
  Δz = -β0·Δτ, δ_p = p_oc/β0 closes to 0.2%; naive residual 0.826 = 1/β-1.
  Affected: σ_z/σ_t only. Unaffected: σ_x/σ_y/ε/σ_δ-kick.
  PROPOSED (not implemented): OCELOT adapter only — feed p_oc=β0·σ_δ,
  kick ×β0, report σ_δ/β0. Tests: validation/test_r56_convention.py,
  reports/R56_convention_resolution.md.

## [drift] 2026-08-04 19:11
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.15087141488858455, 'sigma_y_um': 0.39602675900924217, 'sigma_z_um': 1.9912641108281603, 'eps_nx_mm_mrad': 0.10854221837519602, 'sigma_delta_e3': 0.04340612024633554}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [rf] 2026-08-04 19:11
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.942e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1119 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1119->535 um (both read physics_switches.rf_transverse_kick)
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [full] 2026-08-04 19:11
  full beamline: sample devs — σ_x 0.07%, σ_y 0.34%, σ_δ 0.04%, ε_nx 0.02%, ε_ny 0.30% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 1117 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-04 19:27
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.16045989190426416, 'sigma_y_um': 0.17169630901194127, 'sigma_z_um': 1.3472964329971815, 'eps_nx_mm_mrad': 0.1356574364016766, 'sigma_delta_e3': 0.043406120246349426}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [rf] 2026-08-04 19:29
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.953e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1119 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1119->535 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [full] 2026-08-04 19:32
  full beamline: sample devs — σ_x 0.07%, σ_y 0.09%, σ_δ 0.30%, ε_nx 0.50%, ε_ny 0.41% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 475 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [full] 2026-08-04 19:35
  full beamline: sample devs — σ_x 0.71%, σ_y 0.54%, σ_δ 0.49%, ε_nx 0.05%, ε_ny 0.44% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 474 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [r56-variable-adapter] 2026-08-01
  IMPLEMENTED (classification B fix, adapter-only):
  - run_ocelot: feed p_oc=β0·δ_p, kick ×β0 (in _ocelot_rf_kick), report σ_δ_p
    = std(p_oc)/β0; meta: longitudinal_native_coordinate/conversion_beta/
    rf_kicks_applied. Same 3 conversions in GPT模拟/ued_beamline_v2.py.
  - output_schema: sigma_delta_e3 documented as Δp/p0.
  - tests: drift Test2 (σ_δ_p semantic 0.043% PASS) + analytic σ_z ref;
    rf Test3 (kick residual 2.7e-14, chirp 0.016%) + routing {0,0,1,1} PASS;
    full σ_z/σ_t promoted to quantitative.
  RESULTS: rf σ_z 1112.8→476.3 (AG 477.0); full σ_z 0.68% PASS, waist Δz=0.6mm;
    drift σ_z 1.99%→1.35%; σ_δ_p unchanged semantics. AG invariant 0.0.
  Residual: few-µm deviation at compression waist (higher-order, explained).
  Changelog: CHANGELOG_r56_variable_adapter.md; report:
  reports/r56_adapter_implementation.md + r56_adapter_before_after.json.

## [drift] 2026-08-04 19:41
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.04948557457106704, 'sigma_y_um': 0.31166027713221534, 'sigma_z_um': 1.7054370442093503, 'eps_nx_mm_mrad': 0.03277744017422265, 'sigma_delta_e3': 0.043406120246349426}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z: OCELOT frozen (no tau transport, known), AG grows via R56
  verdict: PASS (transverse) — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-04 19:41
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-04 19:41
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.924e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  DEFERRED: σ_z compression magnitude differs ~1/β (OCELOT R56 convention -L/(β²γ²) vs exact -L/(βγ²)); do not fix here.

## [full] 2026-08-04 19:41
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.98%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 diag: σ_z AG 477 vs OCELOT 471 um (open item)
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-05 09:42
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.20498097996601883, 'sigma_y_um': 0.4125870256791445, 'sigma_z_um': 2.091282660937579, 'eps_nx_mm_mrad': 0.129238505617598, 'sigma_delta_e3': 0.043406120246349426}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.33%
  R56 adapter σ_δ_p semantic: 0.043% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-05 09:42
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-05 09:42
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.924e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-05 09:43
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.98%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 471 um (1.17%, PASS), waist Δz=0.6 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [r56-doc-cleanup] 2026-08-01
  Doc/validation-reference cleanup only (no physics/adapter change):
  - test_full_beamline.py: σ_z/σ_t docstring+checkpoint now quantitative
    (R56 resolved), removed "open item" verdict text.
  - test_drift.py: removed stale "OCELOT tau frozen"; plotted analytic ref now
    uses σ_z(z)=√(σ_z0²+(z·σ_δ_p/γ²)²) (was constant 300µm).
  - test_rf.py: removed deferred 1/β wording from docstring/note/checkpoint.
  - CHECKPOINTS.md: STATUS RESOLVED banner at top; old R56 entries marked
    superseded (retained, not deleted).
  Verified: all 4 acceptance tests PASS; AG arrays unchanged; OCELOT only
  regenerated MC noise; no SC/RF/R56/seed/backend changes.

## [drift] 2026-08-05 21:40
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.10258555643253171, 'sigma_y_um': 0.41090750121309616, 'sigma_z_um': 1.2798324295058479, 'eps_nx_mm_mrad': 0.08650181807549762, 'sigma_delta_e3': 0.043406120246349426}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.47%
  R56 adapter σ_δ_p semantic: 0.043% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-05 21:40
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-05 21:40
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.924e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-05 21:40
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.98%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 471 um (1.17%, PASS), waist Δz=0.6 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-06 10:55
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.43301417903757716, 'sigma_y_um': 0.7039260117123852, 'sigma_z_um': 1.2994156746116554, 'eps_nx_mm_mrad': 0.27476842355856385, 'sigma_delta_e3': 0.043406120246349426}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.46%
  R56 adapter σ_δ_p semantic: 0.043% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-06 10:55
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-06 10:55
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.924e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-06 10:55
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.98%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 471 um (1.17%, PASS), waist Δz=0.6 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [gpt-lattice-single-source] 2026-08-05
  GPT main route refactored: ued_beamline_v2.py builds from lattice.elements
  ONLY (build_lattice_from_shared(cfg, active_types)); hardcoded drifts
  (0.100/0.240/0.355/0.777) removed; step semantics via STEP_ACTIVE;
  multi-instance solenoid/RF supported; RF kick per instance at own z_start;
  transverse gated by shared switch; module importable (main() guard).
  Verified (validation/test_gpt_route_equivalence.py PASS):
  A geometry exact match; B step routing (0/0/N_rf/N_rf, runtime σ_δ gating,
  total length 777mm every step); C sample regression <2% (σ_x 0.65%,
  σ_z 0.43%, σ_δ_p 0.43%); D baseline run_all + r56 unchanged, AG unchanged,
  config SHA dd8ada3d4cb2 unchanged. No physics/R56/SC/random/param changes.
  Reports: gpt_route_lattice_equivalence.md, gpt_route_geometry.json,
  gpt_route_before_after.json, review_summary_gpt_lattice.png;
  CHANGELOG_gpt_lattice_single_source.md.

## [drift] 2026-08-08 12:26
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.47889966582113885, 'sigma_y_um': 0.3071841772479801, 'sigma_z_um': 1.9474872884866767, 'eps_nx_mm_mrad': 0.4992211367450183, 'sigma_delta_e3': 0.043406120246349426}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.19%
  R56 adapter σ_δ_p semantic: 0.043% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-08 12:26
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1989.4 sy=1991.9 um
  AG(off) vs OCELOT sigma_x max dev = 0.40% (<1% PASS) | AG(on) = 390.73% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-08 12:26
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.924e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1120 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1120->535 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-08 12:26
  full beamline: sample devs — σ_x 0.26%, σ_y 0.39%, σ_δ 0.98%, ε_nx 0.14%, ε_ny 0.09% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 471 um (1.17%, PASS), waist Δz=0.6 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.12-architecture-governance] 2026-08-08
  AUDIT phase (no physics change, 7 reports in validation/reports/v0.12_*.md):
  - dataflow/hardcoding/module-responsibility/data-contract/maintainability/
    architecture/regression audits completed.
  IMPLEMENTED (A-class + safe B-class only):
  - shared/constants.py: single physical-constants source (A1);
    params/reference/backend import from it (values identical).
  - backend.py meta += provenance (git commit, timestamp, lattice_hash,
    python, coordinate convention) — traceability (Phase 9).
  - validation/config_check.py + test_config_consistency.py: Level-1
    read-only config consistency (Phase 7/10); added to run_all.
  - YAML comment: sigma_delta semantics clarified to δ_p (B4, value
    unchanged, config SHA unchanged dd8ada3d4cb2).
  NOT modified: AG core, OCELOT core/R56, RF equations, SC, seeds policy,
    lattice geometry, config values, test thresholds.
  VERIFIED: 6/6 tests PASS + r56 unchanged; AG bit-identical to v0.10;
  full-beamline σ_z 477.001/471.497 (1.17%), σ_δ_p 0.98%.
  OPEN (recorded, not touched): γ/β/p0 derivation still duplicated (~12
  sites, B2); rparticles magic indices (B2); seed(42) not configurable (B1);
  backend.py adapter+physics mixing (debt); GPT route monolith (debt).

## [drift] 2026-08-10 10:25
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-10 10:25
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-10 10:25
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-10 10:25
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.13-preSC-maintainability] 2026-08-10
  Debt convergence (no physics change):
  - shared/beam_physics.py: BeamReference single γ/β/p0/velocity source;
    migrated params.derived, reference, beam_result, ued_beamline_v2,
    run_shared, tests (task 1).
  - shared/ocelot_coords.py: named rparticles access (I_X..I_P, set/add_*);
    removed magic indices from business code (task 2); test_r56 unchanged
    (frozen independent reference).
  - random configurable: config random.seed=42; generate_parray seed,
    px/py/delta seed+1 (independent, avoids x-px correlation); verified
    same-seed twice → bit-identical (task 3).
  VERIFIED: 6/6 tests PASS + r56 bit-identical; AG bit-identical
  (σ_x 1984.191, σ_z 477.001); OCELOT now deterministic (σ_x 1996.2,
  within thresholds); config SHA changed (random key added; physics values
  unchanged); lattice hash unchanged.

## [drift] 2026-08-10 22:09
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-10 22:09
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-10 22:10
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-10 22:10
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.14-sc-audit] 2026-08-10
  SC 接入审计 + P0 修复（纯数据流，SC 物理零改动）:
  - P0 根因: OCELOT tracking_step() 只应用 transfer maps，PhysProc
    (SpaceCharge) 只在 track() 的 counter 机制中触发——生产代码全用
    tracking_step → SC 从未执行（历史"SC ON/OFF 重合"疑点根因）。
  - 修复: backend.py / ued_beamline_v2.py / sc_audit_diagnostics.py 循环内
    复刻 counter 机制（每 step×dz 在 map 后触发 apply）+ mesh/step 从 config
    传入（原值相同，数值不变）。SC OFF 路径与旧代码逐位一致。
  - 验证: 修复后 smoke +236% (σx 725→2436µm @500fC)，charge 0-1000fC 单调，
    N/mesh 收敛（±0.6%），step≤5 建议；6/6 测试 PASS + R56 不变；
    no-SC 与 v0.13 逐位一致 (hash e041d6ae9fb7a0d2)；AG 位级不变。
  - P1 记录（未改）: AG SC 电荷语义 Ne·e vs config charge_fC（8 vs 100 fC，
    弱 12.5 倍，修复将改变 SC ON 数值）；SC state 双来源与 HARD FAIL 设计。

## [drift] 2026-08-10 22:40
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-10 22:40
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-10 22:40
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-10 22:40
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-12 18:46
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-12 18:46
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-12 18:46
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-12 18:46
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.14.1-scheduler-equivalence] 2026-08-12
  SC scheduler production 修复（manual counter → OCELOT native get_next_step）:
  - characterization: validation/test_sc_scheduler_equivalence.py（T1-T7 + production acceptance A-F）
    T1-T4 事件级等价（rparticles maxdiff ≤4e-16 浮点末位）；T5 尾段丢失+名义 zstep、
    T6 区间外触发（80 vs 40 事件）、T7 生产 lattice 覆盖 [0,0.422) vs [0,0.777)
    → manual counter clone 退役（非一般等价）
  - production 修复: validation/backend.py::run_ocelot / GPT模拟/ued_beamline_v2.py::run_beamline
    SC ON → native get_next_step() loop（== ocelot track() 核心）；SC OFF → 原 tracking_step
    循环逐字保留（位级不变）
  - stop anchor: SC ON 时 runtime sequence 保留 cathode/sample 零长 marker（来自
    lattice.elements，无硬编码），PhysProc attach 为 cathode→sample，SC 覆盖 [0, 0.777)；
    SC OFF sequence 不变（已验证带/不带 marker 位级一致 maxdiff=0.0）
  - metadata（SC ON 只读）: sc_scheduler=ocelot_native / sc_apply_count /
    sc_coverage_start_m / sc_coverage_stop_m / sc_events
  - 验收 A-F 全 PASS: coverage==sample(z_start)、apply_count=777、step=1/5 事件与
    native reference 一致（777/156）、尾段不丢（z=0.453 zstep=0.003）、区间外无 apply、
    SC OFF 数组 hash 7790fd9c2a2b 与修改前位级一致（样品值 1996.205/474.022）
  - 回归: run_all 6/6 PASS + r56 表征不变（slope −1.163624、残差 2.11e-3、naive 0.826）
  - 主路由 step4: SC effect DETECTED（max Δσ_x 54.71% @100 fC，native 调度）
  - 注: hash e041d6ae9fb7a0d2 的计算对象未在文档/代码中记录，无法复现；
    以修改前/后数组位级对比（7790fd9c2a2b）作为 no-SC 保持的直接证据
  - v0.14 smoke/charge/convergence 数值标注为 manual-scheduler characterization
    （sc_audit_diagnostics.py 保留 manual 复刻），非 native production baseline

## [v0.14.1-scheduler-hash-definition] 2026-08-12
  canonical no-SC regression hash 正式定义（替代无法复现的 e041d6ae9fb7a0d2）:
    SHA1( contiguous bytes of
          [z_mm, sigma_x_um, sigma_y_um, sigma_z_um,
           eps_nx_mm_mrad, eps_ny_mm_mrad, sigma_delta_e3] )[:12]
    run_ocelot SC OFF, config seed 42, N=5e4, dz=0.001, full beamline
    canonical value = 7790fd9c2a2b
  实现与断言位于 validation/test_sc_scheduler_equivalence.py production_acceptance F.

## [drift] 2026-08-12 19:38
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-12 19:39
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-12 19:39
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-12 19:39
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.14.1-ag-charge-semantics] 2026-08-12
  AG SC 电荷语义修复（Ne = Q/e，与 n_particles 解耦）:
  - 根因: AG SC 力 ∝ Ne·e（beam_dynamics_6d.py:379 fb=η·Ne·e/...）；
    之前 adapter 注入 Ne=beam.n_particles=5e4 → 等效 8 fC，比 config 100 fC 弱 12.5 倍
  - 修复（仅 adapter 层）: validation/backend.py::run_ag 与 AG/run_shared.py
    Ne_phys = abs(Q_C)/E_SI（≈6.24e5 @100 fC）；AG 核心/SC 公式未改；
    SC OFF 路径 Ne 强制 0 → 位级不变
  - 新增测试: validation/test_ag_charge_semantics.py
    Test1 charge semantics: Q=10/50/100/500/1000 fC → ag_ne_phys==Q/e（rel=0.0）、
    σx(Q) 单调 2202→12106 µm（Q=100 fC 时 SC ON σx=3656.8 µm，旧 bug 值明显更小）
    Test2 n_particles invariance: Q=100 fC，n=1e4/5e4/1e5 → SC ON 位级一致、
    SC OFF 位级一致且 sample σx=1984.191/σz=477.001（v0.13 基线精确保持）
  - 回归: run_all 6/6 PASS + r56 不变；AG SC OFF 位级不变

## [drift] 2026-08-12 20:06
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-12 20:06
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-12 20:07
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-12 20:07
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.14.1-sc-runtime-state-contract] 2026-08-12
  SC runtime state contract（Task 3，统一状态机 + HARD FAIL + 双状态源消除）:
  - 新模块 shared/sc_state.py: SCState（requested/available/configured/attached/
    apply_count/effective）+ HARD FAIL（import/构造/attach 失败、apply_count==0、
    coverage != cathode→sample 均 raise；禁止 silent fallback）
  - backend.run_ocelot: SC ON 直接 import/构造/attach（无 except ImportError: pass）；
    tracking 后 verify_final(0.0, sample.z_start)（lattice.elements 派生，无硬编码）；
    meta 统一 to_meta()（sc_requested/sc_effective/...）
  - GPT 主路由: 顶部 import 去 try/except；sc_requested_from(cfg,step)=
    config.enabled AND step>=4（step=capability，config=requested）；
    main 单次运行（r_uni 消除）→ 终端显示与 saved sc_enabled 不可能不一致；
    meta 记录 requested+effective
  - AG meta 对齐: physical_charge_C / physical_electron_number（正式 contract）+
    sc_requested/sc_effective；ag_ne_phys 保留 alias（非正式）
  - 测试 validation/test_sc_runtime_state.py A-F 全 PASS:
    A requested=False → effective=False + canonical hash 7790fd9c2a2b
    B requested=True → 六态全真 + coverage [0,0.777]
    C import 不可用 → HARD FAIL（sys.modules=None 模拟，ModuleNotFoundError）
    D apply_count==0 → HARD FAIL（RuntimeError: "SC did not run"）
    E step/config 双源统一（step1-3 永不自动 SC；step4 由 config 决定；runtime 验证）
    F saved JSON sc_enabled == sc_effective
  - 回归: Task1 scheduler equivalence（A-F PASS）、Task2 charge semantics（PASS）、
    run_all 6/6、r56 不变

## [drift] 2026-08-16 20:56
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699752, 'sigma_y_um': 0.6342565055448941, 'sigma_z_um': 1.8000933557025134, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=1.75% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-16 20:56
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-16 20:57
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.953e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-16 20:57
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.46%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 477 vs OCELOT 474 um (0.63%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.15-native-sc-baseline] 2026-08-16
  native SC 基线 + 收敛固化 + AG vs OCELOT 四级比较（阶段 1-5）:
  - 新增 validation/sc_native_diagnostics.py（生产入口 run_ocelot，0.5m drift 同 v0.14 口径）:
    smoke @500fC: OFF 725.3/302.0 → ON 2436.1/1594.9（+236%/+428%，与 v0.14 manual 逐位一致——
    T1 全覆盖场景等价性的数值确认）
    charge 单调: 725→787→1004→1230→2436→3439 µm ✓
    收敛: N ±0.3%（2444/2436/2439）、mesh ±0.6%（33³:2425/63³:2436/127³:2439）、
    step≤5（step5:+1.5% step10:+7.5%）
  - full beamline @100 fC native 基线（首次）: σx 1996.2→2557.3（+28%）、
    σz 474.0→524.9（+11%）、σδ 2.94→4.69e-3（+60%）、εnx 0.080→0.129（+61%）
  - 收敛参数固化: config 注释（N=5e4/mesh=63³/step≤5 + baseline 数值；仅注释，SHA 不变）
  - AG vs OCELOT 四级比较（SC_AG_vs_OCELOT_comparison.md + 曲线图）:
    方向/趋势一致；量级差异显著——横向 +84% vs +28%，纵向 σz +380% vs +11%
    隔离实验（0.5m drift）: AG 纵向 SC 约为 OCELOT 2.5 倍（+1088% vs +428%），
    AG σδ 在纯 drift 不变 → full beamline σδ +385% 为 RF chirp 反馈环
    （SC→σz↑→chirp→σδ↑→R56→σz↑）；εnx 差异为模型能力（AG 0% vs OCELOT +61%）
    **禁止调参拟合；纵向差异列 v0.15 第 2 轮（证据链核对）**
  - 证据链初稿: reports/SC_physics_evidence_chain.md（Kelisani 2023/Luiten 2004/
    van Oudheusden 2010 锚点，主项已锚定，括号项/α 表待论文全文核对）

## [v0.15-ag-longitudinal-fix] 2026-08-16
  AG 纵向模型修复（红线区，用户批准）:
  - 根因: AG theta_z 缺 1/γ² 相对论因子（粒子纵向斜率 Δz'=δ/γ²；论文 Eq.6 发射度
    力 F^em=(Λ²−σ'²)/σ 中 Λz=σδ/γ²）。AG 原 θz=εnz/(βγσz)≈σδ → 纵向膨胀高估 ~γ²
    （100 keV ×1.45、5 MeV ×106；论文案例 σz 0.923mm vs 论文图 ~0.05mm 目视裁决）
  - 修复（AG/beam_dynamics_6d.py theta_z 一行）: eps_geo=εnz/(p0·γ²)=εnz/(γ³β)；
    横向 theta_x/y 未动；SC 公式/R56/RF/solenoid 未动
  - 验收: 论文案例（5 MeV/1nC/10cm）σz 0.923→0.0348mm（OCELOT 0.037、论文图 ~0.05 ✓）、
    σx 1452µm vs OCELOT 1455µm（0.2%）；项目 100 keV no-SC σz 477.001→474.018
    （与 OCELOT 474.022 差 0.0008%）；SC ON 纵向仍由 Fs_z 主导（2289µm，下一轮核对）
  - AG baseline 重固化: σx=1984.191 不变、σz=474.018（test_ag_charge_semantics 更新）
  - 回归: test_ag_charge_semantics PASS（n_particles 位级不变性保持）；run_all/r56 见后

## [drift] 2026-08-16 22:22
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-16 22:22
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-16 22:23
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-16 22:23
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-08-18 20:18
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-18 20:19
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-18 20:19
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-18 20:20
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.15-P0-implementation] 2026-08-16
  P0-1/P0-2 公式修复实施（Kelisani Eq.3 阻尼 + Eq.24-25 αxx/αyy 1/2 因子）:
  - P0-1 RESOLVED: beam_dynamics_6d.py:967 damping γγ'/(γ²β²)→γ'/(γ³β²)
    （论文 Eq.3, p0=γβ；当前 γ'=0 baseline 位级不变；guard: 旧系数=γ²×论文）
  - P0-2 RESOLVED: :106/:111 αxx/αyy 分子 3.0→1.5（论文 Eq.24-25 含 1/2；
    kx=ky=1 → αxx=3/10；code vs paper 积分 rel~1e-13；仅 Gaussian 括号项，
    ellipsoid 路径不受影响）
  - 新测试: test_ag_acceleration_damping.py（人工 γ'≠0，D_corr/D_paper=1.0 精确）、
    test_ag_alpha_coefficients.py（解析值+直接积分+对称性）
  - 回归: run_all 6/6、r56 −1.163624、hash 7790fd9c2a2b、AG no-SC 1984.191/474.018
    位级、SC ON（ellipsoid）逐位不变

## [v0.15-D2-sc-model-gaussian] 2026-08-16
  生产 SC ON 模型切换 ellipsoid → gaussian（Benchmark 4 决策）:
  - 依据: Benchmark 4（0.5m drift @500fC）AG gaussian σz=1611µm vs OCELOT 1606µm（0.3%）
    一致；ellipsoid 高估 2.25×（3613µm）。初始束为高斯分布 → Gaussian 模型自洽
  - 修复: validation/backend.py run_ag 与 AG/run_shared.py sc_model 默认改 gaussian；
    run_ag 加 sc_model 可切换参数（默认 None→gaussian）；meta 加 sc_model
  - 新 SC baseline（full beamline @100 fC, Gaussian）: σx=2551.707 σz=1117.416
    σδ=7.004e-3（旧 ellipsoid: 3656.846/2289.143/14.308e-3——σx 现与 OCELOT 2557.325
    差 0.2%）；no-SC baseline 位级不变（1984.191/474.018）
  - 剩余纵向差异（σz 1117 vs OCELOT 525, ~2.1×）: AG 无 σδ 能量 chirp 机制（RMS 包络
    能力边界）+ RF 反馈环；已缩小（ellipsoid 2.25×→gaussian 2.1×）
  - 回归: run_all 6/6、test_ag_charge_semantics（σx(Q) 单调、baseline 保持）、
    r56、hash 7790fd9c2a2b 均不变

## [drift] 2026-08-27 21:37
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-08-27 21:37
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-08-27 21:37
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-08-27 21:37
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-09-14 21:31
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-09-14 21:31
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-09-14 21:31
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-09-14 21:31
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-09-14 21:34
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-09-14 21:34
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [full] 2026-09-14 21:34
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-09-14 21:55
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-09-14 21:55
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-09-14 21:55
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-09-14 21:56
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [drift] 2026-09-14 21:59
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-09-14 21:59
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-09-14 22:00
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-09-14 22:00
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [v0.15-entrypoint-hardening] 2026-08-16
  生产入口一致性与测试硬化（纯工程逻辑；无物理公式/阈值/baseline 改动）:
  - A1 run_all 退出码: main() 返回码 + sys.exit(main())；子测试异常→FAIL（不吞）。
    新 test_run_all_exitcode.py（stub 注入，不跑昂贵模拟）验证：全成功→0、任一失败→1、
    异常→1；真实进程退出码已实测（1 / 0）
  - A2 加速阻尼测试: 原实现 D_corrected 直接返回 D_paper（自证）。改为测量生产
    envelope_ode RHS 的阻尼差分（D_meas=−Δ(dν_u)/ν_u，ν≠0）：D_meas/D_paper=
    1.000000000000（4 案例）；guard 旧系数 γ'/(γβ²) 比值=γ²（1.429687/116.310962）
  - A3 scheduler 判据: T1-T4 等价判定纳入 L4 完整粒子数值路径（allclose atol=1e-12，
    远高于 ~4e-16 浮点底、远低于 ≥1e-5 的真实调度差异）；T5-T7 仍要求"差异"。acceptance
    逐项分类 [PRODUCTION] / [HELPER-CHAR]；生产 lattice 固定 → 非整数总长/部分覆盖无
    生产验收（如实报告，未冒充）
  - B RF 开关统一: run_shared 此前完全不读 physics_switches；OCELOT 两入口用
    rf_longitudinal_kick 决定实例列表 → 纵向 OFF 时横向连带失效。修复：实例调度=任一
    角色开启，两角色在 kick 函数内部独立门控（公式未改）。新 test_rf_switches_entrypoints.py
    三入口×4 组合实测：L=0,T=1 时 σx 仍变（2024.0→1284.1），L=0 时 σδ 与 no-kick 基准
    逐位一致，三入口语义一致
  - C GPT SC 契约: 复用 shared/sc_state.SCState（无第二套状态机）；SpaceCharge 按需
    import（SC OFF 时不可用不阻塞）；import/构造/attach/apply_count=0/coverage 五类
    HARD FAIL；coverage 期望来自 shared lattice（无硬编码 0.777）。新 test_gpt_sc_contract.py
    7 类故障注入全 PASS（进程内注入并恢复）
  - D 尾段与样品面: GPT 无 SC 此前 int(0.777/0.005)=155 步→775mm（sample 777mm 不可达、
    z777mm probe 缺失）。修复：保留完整步 + 追加剩余长度一步（步长配置不变）；z=0 probe
    追踪前精确采样；probe 区间闭区间；非对齐 probe 标 z_exact=False + z_actual_mm。
    新 test_gpt_tail_sample.py：默认终点 0.7770、非整数 0.503→0.503000、整数 0.500 无
    多余步、z0 精确、z422 标非精确（actual 425.0）。旧 775mm 与新 777mm 分别记录，
    未作同位置比较。gpt_route 样品面 dev 由 interp 末点改善为 0.00%
  - E Benchmark4: 原 "AG ellipsoid" 行未指定模型（D-2 后实际跑 gaussian）。改为显式
    sc_model="ellipsoid"/"gaussian" 走生产入口 + meta 标签核对 PASS；数值不变
  - 基线保持: canonical OCELOT hash 7790fd9c2a2b 不变；AG 完整确定性数组 hash
    41f69f8ace7d 不变（sample σx=1984.191437/σz=474.017607）；R56 slope −1.163624
    不变；run_all 6/6 PASS + OVERALL PASS
  - 开放登记（本轮只登记不修）: (1) AG 纵向矩变量衔接——H=0 薄透镜仍把 ν_z 重设为
    C_zδ/(γ²σ_z)（≈0.00106434→≈0.00000315857），疑似 SC 包络 ν_z 与纵向矩不自洽，
    阻塞完整 SC 物理验收，需单独物理推导+审批；(2) 非整数总长/部分覆盖无生产验收；
    (3) 422mm 非对齐中间 probe 需改变追踪路径才可精确采样（方案待批）
  - 报告: validation/reports/entrypoint_consistency_hardening.md
## [v0.15-entrypoint-hardening-repair] 2026-09-14
  入口硬化审核返修轮（只做最小补丁；不改物理公式/shared 物理参数/baseline/阈值）:
  - R1 cfg_override 真正生效: 此前 run_beamline 内所有物理量取自模块导入期全局
    （energy/charge/spot/sigma_xp/N/dz/probes）、build_lattice_from_shared 用全局 p_SI、
    apply_rf_kick 用全局能量与 beta → 审核反例（100→200 keV、100→500 fC、85→170 µm、
    5→10 mm）history 逐位相同。修复：新增 run_params(c) 单点推导全部量（复用
    BeamReference.from_energy_keV），优先级 显式参数 > cfg_override > 默认 config，
    不写回全局；results["run_params"] 记录实际生效参数。新 test_gpt_config_override.py
    6 项全 PASS（步数 156/78、probe 列表随 override 变、σx 1115.232/411.556 µm、
    电荷和 1e-13/5e-13 C、k_sol 22.375110/15.160412、显式 N 优先、A→B→A 无泄漏）
  - R2 RF 开关单层化: 此前 builder 先按 cfg 删除 RF 调度项 → 事后显式 switches 无法
    复活（cfg L=F/T=F + 显式 L=T → 0 kick）。修复：resolve_switches() 只解析一次
    （逐字段合并），组装与执行同源；RF 实例按 active_types 保留（几何长度不变），
    纵向/横向在 kick 函数内独立门控。实测：cfg OFF+显式 L=ON → 1 kick σδ=2.9435；
    cfg ON+显式 L=OFF/T=ON → 1 kick σδ=0.0997 σx=1278.8 µm
  - R3 probe 位置标记进入最终输出: main() 未把 z_actual_mm/z_exact 传给 make_probe →
    425 mm 状态被保存为 "422 mm" 且无告警；控制台现对非精确 probe 加标记，meta 持久化
    SC 运行时契约（scheduler/apply_count/coverage/available/configured/attached）与
    rf_kicks_applied（实际执行次数）。另修复真实缺陷：样品面 probe 在追踪结果里就缺失
    （末步落 49.99999999999999 mm，被闭区间 z_p<=z 拒绝）→ 引入纯浮点舍入容差
    PROBE_TOL_M=1e-12 m（=1e-9 mm，不改步长/追踪路径），原始值始终写入 z_actual_mm。
    新 test_gpt_saved_output.py（main()→真实 make_probe→真实 write_results→读回 JSON）
    8 项全 PASS
  - R4A 阻尼阈值恢复 1e-12（此前被放宽到 1e-9）+ 真实可恢复故障注入：从生产
    envelope_ode 实时源码派生旧系数版本，monkeypatch 模块属性后由同一测量代码执行，
    finally 恢复。实测 max|ratio-1|: 0 / 2.22e-16 / 6.66e-16 / 0（< 1e-12）；注入版
    ratio=γ₀²=1.429686820、max|ratio-1|=4.297e-01 ≫ 1e-12（判据必然 FAIL = 有判别力）；
    锚点数=1（源码被改动则 guard FAIL）；恢复后逐位相同
  - R4B RF 入口覆盖增至 4 入口×4 组合（新增 validation.backend.run_ocelot 行；
    入口 1/4 走 config 路径、入口 2 走 run_shared 解析、入口 3 走 GPT switches 实参）：
    4 行全 PASS，OCELOT 行与 GPT 行数值一致（2.9213/1284.1）
  - R4C test_gpt_tail_sample.py 单位混用修复: z_actual_mm(mm) % dz(m) → 统一 mm
    （旧式实测 425.0 % 0.005 ×1e3 = 4.999999999991 > 1e-6 → 必然假 FAIL；新式残差
    2.842e-13 mm PASS）
  - R4D test_gpt_route_equivalence.py 插值前断言轨迹覆盖（np.interp 越界会被端点钳位
    而"假装通过"）：sample_checked() 越界抛 AssertionError 并打印 FAIL；GPT/validation
    两侧各自断言
  - R4E git diff --check 退出码 0（尾随空格清除）
  - 基线复核不变: canonical OCELOT hash 7790fd9c2a2b、末点 777.0 mm、AG 完整数组 hash
    41f69f8ace7d（σx=1984.191437 / σz=474.017607）、R56 −1.163624、config SHA 不变
  - 未修（登记）: AG 纵向矩变量衔接（H=0 薄透镜重设 ν_z）仍为开放项；非对齐中间 probe
    仍为步末采样+标注；SC 物理未完全验收（本轮只固化运行时契约）
  - 报告: validation/reports/entrypoint_consistency_hardening.md 附录 R；审核汇总图
    validation/reports/review_summary.png（validation/make_review_summary.py 生成）

## [drift] 2026-09-14 23:04
  drift transverse: AG vs OCELOT max rel dev {'sigma_x_um': 0.3767796798699894, 'sigma_y_um': 0.6342565055448065, 'sigma_z_um': 0.09905818830323633, 'eps_nx_mm_mrad': 0.31140389844541905, 'sigma_delta_e3': 0.02245152598292253}
  analytic drift reference matches (sigma_x=sqrt(s0^2+(s0'z)^2))
  sigma_z analytic ref sqrt(sz0^2+(z*sd_p/gamma^2)^2): AG=0.05% OCELOT=0.08%
  R56 adapter σ_δ_p semantic: 0.022% (PASS)
  verdict: PASS — report /Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/drift_AG_vs_OCELOT.png

## [solenoid] 2026-09-14 23:05
  ROOT CAUSE: AG reduced-order Larmor coupling (dnu_x⊃-2ks·nu_y, dnu_y⊃+2ks·nu_x, dsxy⊃2ks(sx^2-sy^2)).
  Exact hard-edge 4x4 (Brown-Chao, == OCELOT SolenoidTM) gives sxy≡0 for a round uncorrelated beam; AG coupling creates spurious sxy and under-focusing.
  k_s (Bz/(2Brho)) = 22.3751 m^-1, k_s^2 = 500.65 m^-2 — identical in both backends.
  AG as-is:  sx=963.4 sy=2468.9 um (x-y broken)
  AG coupling=OFF: sx=1984.2 sy=1984.2 um
  OCELOT (ref):    sx=1996.2 sy=1991.4 um
  AG(off) vs OCELOT sigma_x max dev = 0.60% (<1% PASS) | AG(on) = 389.28% (FAIL)
  FIX: for round beams the coupling must be disabled in the AG force adapter (validation/backend.run_ag solenoid_coupling=False). Not a parameter tune; enforces exact round-beam transport.

## [rf] 2026-09-14 23:05
  RF standardized to thin-lens in BOTH backends (Option A):
    longitudinal kick δ += K·sin(φ+kz), H=-9.779 m^-1, σ_δ AG=2.939e-3 vs OCELOT=2.939e-3 (PASS)
    transverse RF kick K_trans=-2.680 m^-1 added to OCELOT; σ_x AG=1119 vs OCELOT=1122 um (PASS)
    switch OFF vs ON: AG σ_x 1119->542 um, OCELOT 1122->537 um (both read physics_switches.rf_transverse_kick)
    R56 adapter: kick semantic PASS, routing {'drift': 0, 'solenoid': 0, 'rf': 1, 'full': 1} PASS
  RESOLVED: input δ-variable convention (B) fixed by the adapter; σ_z at sample agrees with AG (residual few-µm at the waist).

## [full] 2026-09-14 23:05
  full beamline: sample devs — σ_x 0.60%, σ_y 0.36%, σ_δ 0.00%, ε_nx 0.53%, ε_ny 0.26% (PASS)
  R56 resolved — σ_z: AG 474 vs OCELOT 474 um (0.00%, PASS), waist Δz=0.4 mm
  switches: {'rf_longitudinal_kick': True, 'rf_transverse_kick': False} == {'rf_longitudinal_kick': True, 'rf_transverse_kick': False}

## [2026-10-05 runner-unification] 正式实现与验证入口共用

- 范围：AG / OCELOT CLI + validation/backend；各共用一个正式driver。物理核心、共享YAML、冻结基线及已有模拟结果保持。
- 默认统一：AG coupling=False；OCELOT dz继承配置，补足尾步；None SC继承cfg；RF全关计0。
- 数值回归：14组同参数完整数组逐位不变；AG 41f69f8ace7d（coupling=False/n_points=2000）；OCELOT 7790fd9c2a2b（seed42/N50000/显式dz=0.001）；config 23e97edb733b。
- 验收：最终run_all 7/7/rc0；9个专项组rc0；新增真实CLI JSON/后端数组严格一致检查。
- 首次失败及修正：solenoid 默认5-mm输出在窄焦点附近插值 dev2.48% > 原1%；该既有解析回归显式保留原1-mm条件后dev0.60%，阈值未放宽。默认5-mm流程另有入口合同覆盖。原失败日志保留。
- 信任边界：运行合同与指定回归通过，不是完整SC+RF物理验收；AG纵向状态、非对齐RF和SC收敛继续开放。
- 详细记录：CHANGELOG_runner_unification_20261005.md；用户HTML/JSON/patch/zip位于本聊天outputs。副本测试没有重写原报告/基线。
## [2026-10-16] AG longitudinal Gz / SC-to-RF state consistency

- 研究者选择：纵向 Gz，初态共享 sigma_z/sigma_delta 优先；横向发射度仍固定。
- 仅积分一组纵向状态，相关矩与展宽派生；RF 的 H=0、±H 和行列式检查通过。
- 隔离副本 run_all 8/8；新增纵向专项 15 项；电荷/阻尼/退出码专项及真实 CLI 保存通过，原验收阈值保持。
- 一致初态 .4 m Gaussian-SC：sigma_delta 1e-4→0.00152231291，H=0 对 nu_z 相对变化为 0（修复前 -99.7032%）。
- AG full SC ON：sigma_z 1117.416172→524.432385 um；sigma_delta_e3 7.00436328→4.70665942。
- AG full SC OFF 新基线 sigma_x=1984.189024、sigma_z=473.922215 um，hash02012b2143f5。另存新基线及迁移原因，旧档案不覆盖。
- OCELOT SC OFF canonical 实跑7790fd9c2a2b；config23e97edb733b。短PIC差异（sigma_z1.89%、sigma_delta11.47%）仍为诊断，SC完整物理验收未完成。
- Note: AG/longitudinal_state_physics_note.md；changelog: CHANGELOG_ag_longitudinal_gz_20261016.md。未提交、未推送、未同步外部服务。
