# AI_HANDOFF — UED 项目当前状态唯一入口

> 本文档是**当前状态入口**，不是完整历史记录。新 session 从本节开始建立认知；
> 需要细节时再读 validation/CHECKPOINTS.md、validation/reports/、validation/baselines/。
> 当前状态：以 PROJECT_STATUS.md 与本文 §42 为准。前面的早期阶段记录保留历史含义，不能当作当前物理资格。

## 0. 版本与位置
- 当前目录：`/Users/qin/Desktop/暑研/Beam_dynamics_simu`；分支：`main`；核对HEAD：`90e96842c177798104601ffc7416208c7a08fb2b`。工作树有既有未提交修改，本轮源摘要用于识别实际运行版本。
- 最近可信标签：**`v0.13-preSC-maintainability`**（上一冻结基线，可回退点）
- 其他标签：`v0.10-noSC-longitudinal-validated`（首次纵向冻结）、`v0.11-noSC-single-source-lattice`
- config SHA：以 `git show HEAD:shared/beamline_config.yaml` 实际计算为准；历史上 v0.13 加 `random.seed` 键导致 SHA 变化过一次，**物理参数值从未改变**
- 运行环境：macOS 13.7.1 (x86_64) / Python 3.12.2（conda-forge）/ OCELOT 26.06.1 / NumPy 1.26.4 / SciPy 1.13.1 / Matplotlib 3.9.2 / PyYAML 6.0.1
- **重要**：所有命令用 `/opt/anaconda3/bin/python3`；系统 `/usr/bin/python3`（3.6）缺 numpy/ocelot/yaml，不可用
- 远程：GitHub `QIN-SMART/Beam-Dynamics`（public，token 已存钥匙串；push 若遇 HTTP 400/超时用 `git -c http.version=HTTP/1.1 -c http.proxy= push`）

## 1. 历史阶段记录（当前状态见 §42 / PROJECT_STATUS）
- 当前阶段：**v0.14.1 SC 正式 beamline 验证准备**——task 1（scheduler equivalence）已完成：manual counter 经 characterization 证明非一般等价（T5–T7），production 已迁移到 OCELOT native `get_next_step()` 调度（SC ON），SC OFF 位级不变；SC 覆盖修正为 cathode→sample（0→0.777m，stop anchor 来自 lattice.elements 的 sample marker）；**SC 数值仍未经正式 beamline 验证，未声称 fully validated**
- 当前阶段：**v0.15 生产入口一致性与测试硬化已完成（待人工审核）**——A1 退出码、A2 生产 RHS 阻尼测试、A3 scheduler 判据含粒子路径、B 三入口 RF 开关独立门控、C GPT SC 状态契约（SCState + 5 类 HARD FAIL）、D 尾段补足至样品面（775→777mm）、E Benchmark4 模型显式化；基线全部保持（hash 7790fd9c2a2b / AG 41f69f8ace7d / R56 −1.163624 / run_all 6/6）。报告：validation/reports/entrypoint_consistency_hardening.md；开放登记：AG 纵向 ν_z 衔接问题（未修）
- 最新：**入口硬化审核返修轮已完成并在此暂停（2026-09-14）**——修复 cfg_override 未生效、RF 开关两层冲突、probe 位置标记未进最终输出、阻尼阈值被放宽/guard 自证、RF 入口覆盖缺 `run_ocelot`、mm/m 单位混用、越界 `np.interp` 假通过、行尾空格；全部回归退出码 0（含 run_all 6/6 与基线 hash 不变）。**本轮未 commit / 未 push / 未同步 iCloud**，工作树不是 clean——详见 §27
- 上一阶段：**v0.15（SC 正式 beamline 验证）阶段 1-5 进行中**——native SC 基线已建立（full beamline @100 fC：σx 1996→2557 +28%、σz 474→525 +11%）、收敛参数已固化（N=5e4/mesh=63³/step≤5，config 注释）、AG vs OCELOT 四级比较初稿完成（方向/趋势一致，纵向量级差 4-6 倍，禁止调参）、证据链审计初稿（Kelisani/Luiten/van Oudheusden 锚点）；v0.14.1 已冻结（标签 v0.14.1-SC-integration-hardened）
- 长期目标：SC 验证完成后才有资格讨论 AG/OCELOT 的 SC 物理对比、GUI、优化
- 禁止事项：修改 AG/OCELOT 核心、RF 方程、R56、lattice 几何、测试阈值、随机策略；未获批准不得实施 v0.14.1 task 2/3 或任何 SC 参数调整

## 2. 项目架构
```
shared/           参数解析 params.py；常量 constants.py（单一来源）；
                  γ/β/p0 派生 beam_physics.py；OCELOT 坐标封装 ocelot_coords.py；
                  输出 schema output_schema.py；双路由对比 compare.py
AG/               核心：beam_dynamics_6d.py（6D 包络 ODE 1289 行）、
                  external_forces.py（螺线管/RF 力）、beamline_sim.py（出图）；
                  适配：run_shared.py（统一输出 JSON）
GPT模拟/          主路由 ued_beamline_v2.py（lattice 单一来源，可 import 测试）
validation/       backend.py（双后端适配，最高风险）、beam_result.py、
                  reference.py（解析参考）、config_check.py（Level-1 检查）、
                  test_*.py、reports/、baselines/
scripts/          sync_to_phone.py（iCloud 同步 + bundle + gpt_review 版本归档）
```
- **唯一几何真源**：`shared/beamline_config.yaml → lattice.elements`；主路由与验证路由均从它构建（v0.11 达成，有 `test_gpt_route_equivalence.py` 保证等价）
- 统一输出：`BeamResult`（σ_x/y/z_um、σ_t、σ_δ_p、ε_nx/ny_mm_mrad + meta provenance）
- provenance meta 含：git_commit、config_sha、lattice_hash、timestamp、python、random_seed、坐标约定

## 3. 两个 backend 职责
- **AG（解析包络，确定性）**：`validation/backend.py::run_ag` → `make_beam_100keV`（Ne、能量、σ 矩、发射度）→ 按 lattice 建 `ExtFieldRegion` 力区（螺线管 Bz、RF 横向力）→ `propagate()`（solve_ivp RK45 积分 6D 包络 ODE）→ 输出 σ 矩。RF 纵向用薄透镜 `apply_rf_thin_lens(H)` 分段施加。SC 通过 `space_charge_forces(beam, model)`（gaussian/ellipsoid）进入 ODE。**AG 是确定性算法，无随机数，SC OFF 时结果位级固定**
- **OCELOT（宏粒子）**：`run_ocelot` → `generate_parray`（配置 seed）→ Drift/Solenoid（SecondTM）→ 解析 RF kick → 可选 SpaceCharge（counter 机制触发）→ 粒子统计 → BeamResult
- 两者比较原则：不要求逐点重合；按"方向→趋势→量级→定量解释"四级推进（AG 是 RMS 解析，OCELOT 是 PIC，模型能力不同）

## 4. 坐标约定（最重要，改代码前必读）
- **项目标准变量：δ_p = Δp/p0**（动量偏差，无量纲）
- **OCELOT 原生第六坐标：p_oc = ΔE/(c·p0)**（能量偏差归一化，**不是** Δp/p0；源码证据 `ocelot/cpbd/beam/generator.py:51`、`beam/particle.py:20`）
- 两者换算（仅限 adapter 边界）：**p_oc = β0·δ_p**（进入 OCELOT 时），**δ_p = p_oc/β0**（离开时）
- 允许出现 p_oc 的位置只有两处：`validation/backend.py`（run_ocelot 束生成、_ocelot_rf_kick）和 `GPT模拟/ued_beamline_v2.py`（apply_rf_kick）——除此之外任何代码出现 p_oc 都是违规（已登记例外：只读诊断脚本 `validation/sc_audit_diagnostics.py:62` 用 set_p_oc 镜像束生成，属 manual-scheduler characterization 保留代码）
- tau = c·t [m]（OCELOT 原生，rparticles[4]）；共动空间坐标 z = −β0·c·Δt（头为正）；输出 σ_z = β0·σ_tau；σ_t = σ_z/(β0c)
- **BeamResult.sigma_delta_e3 恒表示 δ_p**（OCELOT 输出已 ÷β0），禁止直接暴露 raw p_oc
- 业务代码禁止直接写 `rparticles[5]` 等魔法索引，必须用 `shared/ocelot_coords.py` 的语义访问（I_X/I_PX/I_Y/I_PY/I_TAU/I_P、set_*/add_*）
- 禁止在 AG 核心出现 p_oc（已用 grep 验证 0 处）
- 磁矩语义：γ/β/p0 统一从 `shared/beam_physics.py::BeamReference.from_energy_keV` 派生（v0.13），禁止各处重复手写 1+E/511

## 5. R56 最终结论
- 分类：**B — 输入 δ 变量约定不匹配**（不是 OCELOT bug，也不是 AG bug；两模型各自内部自洽）
- 关键证据（冻结表征 `test_r56_convention.py`，禁止修改）：OCELOT raw 斜率 = 传输矩阵 R56_tm = **−1.163624**，与 `−L/(β²γ²)` 偏差 1.25e-5，而与精确 c·t 斜率 `−L/(βγ²)=−0.6379` 差 82.4%（=1/β−1）；形式转换（δ_p=p_oc/β0，Δz=−β0·Δτ）闭合残差 0.2%
- 修复（v0.13 前完成）：adapter 输入 ×β0、RF kick ×β0、输出 ÷β0；**OCELOT 原生 R56 未改**
- 结论：σ_z 压缩曲线在样品面一致（<1%）；深压缩区腰附近有几 µm 的高阶数值残差（τ 空间 vs z 空间 RMS 演化差异），已解释，非 bug

## 6. Solenoid 最终结论
- AG 降阶 Larmor 耦合项（dν_x⊃−2k_s·ν_y、dν_y⊃+2k_s·ν_x、dσ_xy⊃2k_s(σ_x²−σ_y²)）对**圆束**产生虚假 σ_xy 并欠聚焦（z=160mm 处 σ_x=147µm vs 精确 97µm，x-y 对称破坏 σ_y=2469）
- 精确证据：硬边 4×4 Brown-Chao 矩阵（= OCELOT SolenoidTM）对圆束给出 σ_xy≡0（解析可证），OCELOT 结果与之一致
- 修复：适配层关闭耦合（`run_ag(..., solenoid_coupling=False)`；`AG/run_shared.py` 默认 False）；**AG 核心未改**，修正理由写入 CHECKPOINTS
- 验证：coupling OFF 后 AG vs OCELOT σ_x 偏差 0.40%（样品面），x-y 对称恢复

## 7. RF 状态
- **纵向（已解决）**：两后端统一薄透镜模型；chirp H = eV·k·cosφ/(β²E₀) = **−9.78 m⁻¹**；kick δ_p = (V/(β²E_tot))·sin(φ+k·z_phys)，z_phys=−β0·tau；σ_δ_p 一致性 0.3–1%（阈值 2%）；kick 语义测试残差 6e-13
- **横向（open item）**：K_trans = −e·k·V/(2γβ·m_e·c²) = **−2.68 m⁻¹**（Panofsky-Wenzel），默认 **OFF**（`physics_switches.rf_transverse_kick: false`）；公式尚未独立验证，仅两后端自洽。开启时两路一致（AG σ_x 1119→542、OCELOT 1120→535）
- kick 时机按每个 rf 实例的 z_start（多实例支持），每次只踢一次；drift/solenoid 节禁止误踢（有 routing 测试防回归 {0,0,1,1}）
- 参数来源：`lattice.elements[rf*].parameters`（frequency_GHz/voltage_kV/phase_rad）

## 8. Lattice single source 状态
- 已达成：`build_lattice_from_shared(cfg, active_types)` 是主路由唯一几何构建入口；验证路由 run_ocelot 从同一 `_lattice_elements` 构建
- step 语义（**测试语义，不是物理路由**）：1{drift} / 2{+solenoid} / 3{+rf} / 4{+rf+SC}；未激活元件保留等长 Drift，总长恒等于样品位（777mm）
- 多螺线管、多 RF 支持（每实例独立 B/V/f/φ）；几何等价由 `test_gpt_route_equivalence.py` 验证（名称/类型/长度/顺序/RF 位置精确一致，样品面 dev<2%）
- 配置一致性由 `validation/config_check.py`（Level-1）只读检查：energy↔γ↔β↔p0、RF 频率合理、位置单调、sample==总长、schema 合法

## 9. RNG Policy
- 配置：`config.random.seed = 42`（v0.13 起）
- 生成序列：`seed` → generate_parray（x/y/tau 确定）；`seed+1` → px/py/δ_p（独立序列，**避免 x 与 px 用同序列导致虚假相关的陷阱**——这是 v0.13 之前发现的坑，禁止回到单 seed 覆盖）
- **同 seed 两次运行位级一致**（OCELOT full 验证 hash e041d6ae9fb7a0d2）——历史"首束随机"问题已解决
- 陷阱：OCELOT `SpaceCharge.prepare()` 无条件 `np.random.seed(10)`（sc.py:106）——若在束生成前 prepare 会污染全局 RNG；当前流程 prepare 在束生成后，影响有限，但记录在案
- 测试受控集用 `default_rng(seed+2)`（test_rf），与主序列隔离

## 10. SC v0.14 审计最终结论
- **P0 根因（已修复）**：OCELOT 的 `tracking_step()` 只应用 transfer maps；PhysicsProcess（含 SpaceCharge）只在 `track()` 主循环的 `get_next_step()` 的 counter 机制中触发（`ocelot/cpbd/track.py:476-479`）。**历史所有代码（backend、主路由、benchmark）都用 tracking_step，因此 SC 从未真正运行**——这就是 v0.12 之前"SC ON/OFF 几乎重合"疑点的根因
- **v0.14 修复（manual counter，已退役）**：曾在 `run_ocelot`、`ued_beamline_v2.run_beamline`、`sc_audit_diagnostics` 的循环内复刻 counter 逻辑（`sc.counter -= 1; if counter<=0: ...`）；SpaceCharge 构造从 config 传 `step` 与 `nmesh_xyz`
- **v0.14.1 task 1（已落地）**：manual counter 经 characterization（`validation/test_sc_scheduler_equivalence.py`）证明非一般等价——T5 尾段丢失、T6 区间外触发、T7 生产 lattice 下覆盖 [0,0.422) vs [0,0.777)；**production 已迁移到 OCELOT native `get_next_step()` 调度**（== track() 核心，backend.py::run_ocelot 与 ued_beamline_v2.py::run_beamline 的 SC ON 分支）；SC OFF 保持原 tracking_step 循环，位级不变（数组 hash 7790fd9c2a2b）
- **stop anchor**：SC ON 时 runtime sequence 保留 lattice.elements 中的 cathode/sample 零长 marker，PhysProc attach 为 cathode→sample（覆盖 [0, sample.z_start=0.777)，无硬编码）；SC OFF sequence 不变（带/不带 marker 已验证位级一致）
- **metadata（SC ON，只读）**：sc_scheduler="ocelot_native"、sc_apply_count、sc_coverage_start_m、sc_coverage_stop_m、sc_events（z,zstep 列表）
- **⚠️ SC 数值未验证**：v0.14 smoke/charge/收敛数值是 **manual-scheduler 行为**（保留于 sc_audit_diagnostics.py 作为 manual characterization），native-scheduler 的 SC 数值验证属 v0.15。**禁止把 SC 描述为 fully validated**
- 修复后诊断（`sc_audit_diagnostics.py`）：smoke 500 fC 纯漂移 0.5m：σx 725→2436µm（+236%）、σz 302→1595µm（+428%）、εnx 0.080→0.120（+49%）；charge 0→1000 fC 单调（σx 725→3439、σz 302→2269、εnx→0.149）；N(1e4/5e4/1e5)±0.3%、mesh(33/63/127)±0.6% 收敛；SC step≤5 建议（step=10 偏 7.5%）
- OCELOT SC 算法（源码证据 sc.py）：NGP 沉积（:191-193）→ 自由空间 Green 卷积 + FFT 解 Poisson（:85-168，ASTRA 同款）→ 三线性插值（:202-204）→ 含纵向 Ez（:200,248）→ 束团静止系解场、实验室系 kick（横向乘 1−β0²，:246-248）；电荷来自 q_array（:241）；默认 low_order_kick=True、random_mesh=False、random_seed=10

## 11. AG charge semantics bug（已修复，v0.14.1 task 2）
- 根因：AG SC 强度 `fb = η·Ne·e/(8π√π·ε₀)`（beam_dynamics_6d.py:379）中 **Ne = config beam.n_particles = 50000** → 等效总电荷 Ne·e = **8 fC**，比物理束团电荷（`beam.charge_fC = 100`）弱 **12.5 倍**
- 语义区分：**beam.n_particles 对 OCELOT 是宏粒子数值计数（数值精度参数）；beam.charge_fC 是物理束团电荷**
- **修复（2026-08-12，仅 adapter 层）**：`validation/backend.py::run_ag` 与 `AG/run_shared.py` 注入 `Ne_phys = abs(Q_C)/E_SI`（≈6.24e5 @100 fC）；AG 核心与 SC 公式未改；SC OFF 路径 Ne 强制 0 → 位级不变
- 验证：`validation/test_ag_charge_semantics.py`——charge 语义（ag_ne_phys==Q/e，σx(Q) 单调 2202→12106 µm）与 n_particles 不变性（Q 固定时 n=1e4/5e4/1e5 SC ON 位级一致；SC OFF sample σx=1984.191/σz=477.001 与 v0.13 基线精确一致）；run_all 6/6 + r56 不变
- 注意：SC ON 数值较旧 bug 时代明显增大（Q=100 fC 时 σx≈3657 µm vs 旧 ~1 mm 量级）——**预期变化，不是回归**

## 12. SC runtime state contract（已实施，v0.14.1 task 3）
- **统一状态机**（`shared/sc_state.py::SCState`）：`sc_requested → sc_available → sc_configured → sc_attached → sc_apply_count → sc_effective`；`sc_effective = (sc_apply_count > 0)` 是"SC 真正运行"的唯一判据
- **HARD FAIL**（requested=True 时）：import/构造/attach 失败、tracking 后 apply_count==0、coverage != cathode→sample 全部直接 raise；`except ImportError: pass` 已删除（backend.py 与 ued_beamline_v2.py）
- **双状态源消除**：`step` 只定义 route capability（1-3 无 SC），config.enabled 定义 requested；GPT 主路由 `sc_requested_from(cfg,step)=config.enabled AND step>=4`，main 单次运行（r_uni 第二跑已删除）→ 终端显示与 saved sc_enabled 不可能不一致
- **AG meta 对齐**：physical_charge_C / physical_electron_number（正式 contract）+ sc_requested/sc_effective；ag_ne_phys 保留 alias（task 2 兼容）
- 测试：`validation/test_sc_runtime_state.py` A-F 全 PASS；回归 6/6 + r56 + canonical hash 7790fd9c2a2b 不变

## 13. no-SC regression baseline（必须保持）
- 测试命令：`/opt/anaconda3/bin/python3 validation/run_all.py`（6 项）+ `validation/test_r56_convention.py`
- **canonical no-SC regression hash（v0.14.1 起正式定义）**：
  `SHA1( contiguous bytes of [z_mm, sigma_x_um, sigma_y_um, sigma_z_um, eps_nx_mm_mrad, eps_ny_mm_mrad, sigma_delta_e3] )[:12]`
  （run_ocelot SC OFF，config seed 42，N=5e4，dz=0.001，full beamline）→ **`7790fd9c2a2b`**
  旧 `e041d6ae9fb7a0d2` 不再追踪：其输入对象/算法未记录，无法严格复现
- 6 项全 PASS：config_schema（Level-1 一致性）、drift（σ_x 0.2%、σ_δ_p 语义 0.022%）、solenoid（0.40%）、rf（σ_δ_p <1%、kick 语义 6e-13）、full_beamline（七项量化：σ_x 0.60%、σ_y 0.36%、σ_δ_p 0.46%、ε_nx 0.53%、ε_ny 0.26%、σ_z 0.63%、σ_t 0.63%、腰 Δz=0.4mm）、gpt_route（样品面 <1%）
- full_beamline 样品面参考值：AG σ_x=1984.191µm/σ_z=**474.018µm**（v0.15 纵向修复后重固化，原 477.001；与 OCELOT 474.022 差 0.0008%）；OCELOT σ_x=1996.205/σ_z=474.022（同 seed 位级，canonical hash 7790fd9c2a2b）
- r56_convention：raw slope=−1.163624、闭合残差 2.11e-3、naive 0.826 —— 冻结不变
- AG 数组确定性位级可复现（σz baseline 于 2026-08-16 纵向修复后更新为 474.018）；OCELOT 同 seed 位级可复现
- **AG 纵向修复（v0.15，2026-08-16）**：theta_z 补 1/γ² 相对论因子（Δz'=δ/γ²，Kelisani Eq.6 Λz=σδ/γ²）；修复前纵向膨胀高估 ~γ²（5 MeV 案例 σz 0.923mm vs 论文图 ~0.05mm）；修复后论文案例 σz=34.8µm（OCELOT 37µm）、项目 no-SC σz=474.018（OCELOT 474.022）；横向与 SC 公式未动；方案与推导见 `validation/reports/AG_longitudinal_fix_proposal.md`
- 注：生产 SC ON 默认模型在 v0.15 D-2 起为 **Gaussian**（此前为 ellipsoid）；SC ON 数值以 CHECKPOINTS v0.15-D2 为准
- **P0-1/P0-2 RESOLVED（v0.15，2026-08-16）**：Eq.3 阻尼系数 γ'/(γ³β²)（旧 γ'/(γβ²) 差 γ²，仅加速路径；当前 γ'=0 baseline 位级不变）；αxx/αyy 补 1/2（Eq.24-25，影响 <0.01%，ellipsoid 路径不受影响）。证据与实施见 `validation/reports/v0.15_formula_resolution_P0.md` + `v0.15_P0_implementation.md`
- **D-2 SC 模型切换（v0.15，2026-08-16）**：生产 SC ON 默认从 ellipsoid 改 Gaussian（Benchmark 4：AG gaussian vs OCELOT 0.3% 一致；ellipsoid 高估 2.25×；初始束为高斯 → 模型自洽）。新 SC baseline σx=2551.707/σz=1117.416（ellipsoid 旧值 3656.846/2289.143）；Gaussian 下横向与 OCELOT 0.2% 一致；no-SC baseline 位级不变。详见 `validation/CHECKPOINTS.md` v0.15-D2

## 14. 下一阶段 v0.14.1 明确任务（SC 正式 beamline 验证）
1. **✅ 已完成（2026-08-12）**：manual counter vs OCELOT native scheduler 等价性证明。结论：非一般等价（T5–T7 差异），production 已迁移到 native `get_next_step()`（SC ON），SC OFF 位级不变；SC 覆盖修正为 cathode→sample。证据：`validation/test_sc_scheduler_equivalence.py`（T1–T7 + acceptance A–F 全 PASS）、run_all 6/6、r56 不变
2. **✅ 已完成（2026-08-12）**：AG charge semantics——`run_ag`/`run_shared` 注入 `Ne_phys = Q/e`（≈6.24e5）；SC OFF 位级不变（1984.191/477.001）；n_particles 不变性测试全 PASS（详见 CHECKPOINTS v0.14.1-ag-charge-semantics）
3. **✅ 已完成（2026-08-12）**：SC 状态机（六态 + HARD FAIL，shared/sc_state.py）与双状态源统一（step=capability、config=requested、effective=apply_count>0）；测试 test_sc_runtime_state.py A-F 全 PASS
4. **进行中（v0.15 阶段 2）**：固化 SC 收敛参数 N=5e4、mesh=63³、SC step≤5——已写入 config 注释与 SC_native_baseline.md（native 数据：N ±0.3%、mesh ±0.6%、step≤5）
5. **进行中（v0.15 阶段 3）**：AG vs OCELOT SC 四级比较——方向/趋势一致；量级差异：横向 +84% vs +28%、纵向 σz +380% vs +11%（隔离实验显示 AG 纵向 SC 为 OCELOT ~2.5 倍；full beamline σδ 差异为 RF chirp 反馈环）；**禁止调参拟合**；ε 增长差异为模型能力。报告：SC_AG_vs_OCELOT_comparison.md + 曲线图
7. **物理证据链审计（v0.15 新增，来源：GPT 审核意见 2026-08-16）**：为每个 AG SC 公式建立「公式 → 原始论文 → 代码实现行号 → 独立验证」证据链。已知外部锚点：Kelisani et al. 2023 PRA（6D envelope + Gaussian SC，f_b ∝ Ne）、Luiten et al. 2004 PRL（均匀椭球 SC，线性内部场）、van Oudheusden et al. 2010 PRL（95 keV/200 fC RF 压缩，UED 同量级基准）。目标：排除"测试全 PASS 但公式源于 AI 生成"的风险（测试只证明代码符合已规定行为，不证明规定本身正确）。验证方式：复现论文关键图 + 与 OCELOT PIC 独立对比
6. 每步回归：no-SC 6 项 + r56 保持 PASS；SC ON 结果附完整 provenance（含 seed/mesh/step/N）
- **禁止**：声称 SC fully validated；修改 AG/OCELOT 核心；调整测试阈值；进入 GUI；优化参数让两模型吻合

## 15. 关键文件（职责速查）
- `validation/backend.py`：双后端适配 + 力组装 + RF kick + p_oc 转换 + provenance（**最高风险，改前必读 §4**）
- `shared/params.py`：解析 + derived() + lattice helpers；`shared/beam_physics.py`：BeamReference；`shared/constants.py`：物理常数；`shared/ocelot_coords.py`：rparticles 语义访问
- `GPT模拟/ued_beamline_v2.py`：主路由（可 import；main() 守卫）；`AG/run_shared.py`：AG 统一输出
- `validation/beam_result.py`：统一容器；`validation/reference.py`：解析参考；`validation/config_check.py`：只读一致性
- 测试：`test_config_consistency / test_drift / test_solenoid / test_rf / test_full_beamline / test_gpt_route_equivalence`；**`test_r56_convention.py` 冻结禁改**；`test_sc_scheduler_equivalence.py`（SC 调度 characterization + production acceptance A–F，mesh 33³ 加速）；`sc_audit_diagnostics.py`（manual-scheduler SC characterization 只读脚本）

## 16. 关键报告
- `validation/reports/SC_integration_audit.md`：P0 根因 + 修复 + 诊断数值 + 状态机设计（§8 附 v0.14.1 manual→native 实施状态更新）
- `validation/reports/SC_ocelot_source_audit.md`：OCELOT SC 源码逐条行号证据
- `validation/reports/SC_AG_model_audit.md`：AG SC 公式与模型假设
- `validation/reports/R56_convention_resolution.md`：B 类结论全推导
- `validation/reports/v0.12_dataflow_audit.md` / `v0.12_data_contract.md` / `v0.12_maintainability_risk.md` / `v0.13_architecture_audit.md`：架构/数据流/契约/风险
- `validation/baselines/v0.10-noSC-longitudinal-validated/`：冻结基线（manifest/environment/physics-status）

## 17. 禁止修改区域（红线）
- AG 核心三文件（beam_dynamics_6d.py / external_forces.py / beamline_sim.py）
- OCELOT 安装源码（/opt/anaconda3/.../ocelot/）
- `test_r56_convention.py`（冻结表征）
- 测试阈值；baseline 目录；`shared/beamline_config.yaml` 物理参数值
- 随机策略（除非作为已验证的接口改动）；RF 纵/横向方程；R56；solenoid 方程

## 18. STOP CONDITIONS（触发即停，报告第一个失败点，不连续打补丁）
- 任何原有测试从 PASS 变 FAIL；AG 确定性数组非预期变化；config SHA 意外改变
- 元件数量/顺序不一致；RF kick 数量错误；step1/2 出现 RF kick
- 出现 NaN、负方差、发射度≈0；为使两模型吻合而准备调参；无法确认某变量定义或单位
- SC 相关：SC ON 无任何效应；manual counter 与 native scheduler 对照不等价且无法解释

## 19. 交接后第一件事
1. `git log --oneline -5` + `git status` 确认工作树干净
2. 读本文件 §0-§14；如需细节读 validation/CHECKPOINTS.md 最新条目（注：CHANGELOG/CHECKPOINTS 目录在 validation/ 下）
3. 跑 `validation/run_all.py` + `test_r56_convention.py` 确认基线
4. 按 §14 任务书开始 v0.14.1 的第一步（scheduler 等价性证明），每步带回归

## 20. 阶段历史沿革（速览，细节在 validation/CHECKPOINTS.md）
- v0.10（基线冻结）：drift/solenoid/RF 分节验证通过，冻结标签 + baselines/ 目录；当时发现并修了 OCELOT 能量单位 bug（energy 应是总能量 GeV）、ε_nz 一致性、螺线管耦合、RF 薄透镜统一
- v0.11（lattice 单一来源）：主路由硬编码几何（0.100/0.240/0.355/0.777）清除，`build_lattice_from_shared` + 多实例 + step 语义；新增 `test_gpt_route_equivalence`
- v0.12（架构治理）：常量单一来源 constants.py、provenance meta、Level-1 config_check、7 份 v0.12 审计报告
- v0.13（结构债务收敛）：BeamReference 统一 γ/β/p0、ocelot_coords 语义封装、random.seed 配置化（同 seed 位级可复现）；标签 `v0.13-preSC-maintainability`
- v0.14（SC 接入审计）：定位 P0（tracking_step 不触发 PhysProc）、manual counter 修复、SC 诊断（smoke/charge/收敛）、三份 SC 报告；**SC 未正式验证**

## 21. 常见陷阱与调试要点
- **单位**：OCELOT energy 参数是总能量 GeV（`(E_keV+511)*1e-6`）；tau 是米（c·t）；σ_z 输出 = β0·std(tau)；σ_δ_p = std(p_oc)/β0。任何"看起来差 1.8 倍"先检查 β0 是否漏乘/漏除
- **seed**：束生成必须 seed→generate_parray、seed+1→px/py/δ_p；禁止在 generate_parray 前后重复同 seed（x-px 相关陷阱）；SC 的 prepare() 会 seed(10)（影响全局 RNG）
- **rparticles**：一律用 ocelot_coords 语义名；禁止裸索引
- **SC 无效症状**：SC ON/OFF 逐位相同 → 检查 counter 触发逻辑是否在循环内；若用 get_next_step() 注意无 proc 时按元素大步走（破坏细采样）
- **AG SC 偏弱**：Ne 语义是宏粒子数，AG SC 强度 ∝ Ne·e，与 charge_fC 无关（12.5× 偏弱，未修）
- **调试顺序**（AGENTS.md 规范）：先查单位 → 再查坐标定义 → 再查极限情形（SC OFF 应 ε=const、无场应 drift）→ 再对照解析解
- 物理常数一律从 shared/constants.py 取；γ/β/p0 一律从 BeamReference 取

## 22. AG SC 公式速查（详情见 SC_AG_model_audit.md）
- Gaussian（Kelisani 2023）：主项 Fs_x = fb·αx/(β²γ³·σx·σz)，fb = η·Ne·e/(8π√π·ε₀)，η=e/(mc²)；α 系数由 kx=σx/(γσz)、ky=σy/(γσz) 查插值表；另有 O(1/γ) 括号修正项（beam_dynamics_6d.py:384-431）
- Ellipsoid（Luiten 2004）：Fs_x = Ne·r_e·Mx/(γ³β²·σx·σz)，Mx/My/Mz 为均匀椭球 form factors（球对称解析 / 三轴 Carlson 积分），Mx+My+Mz=1（:506-545）
- 两模型 ε_nx 均为输入常量 → **天然不产生发射度增长**（这是模型能力限制，不是 bug；与 OCELOT PIC 的投影 ε 增长对比时禁止据此判 AG 错）
- SC 与发射度项在包络方程中线性相加：dν_u = Fe_u + Fs_u + F_eps_u + 耦合（envelope_ode:997-999）
- SC OFF 语义：`Ne=0` → fb=0 → 无 SC 力（no-SC 基线的标准做法）

## 23. 关键数值速查（100 keV 参考束）
- γ0=1.1957、β0=0.5482、βγ=0.6556、p0=1.790e-22 kg·m/s、v0=1.644e8 m/s
- ε_nx=ε_ny=0.08 mm·mrad、ε_nz=0.02 mm·mrad（=βγ·σ_z·σ_δ 自洽值）、σ_x0=σ_y0=85µm、σ_z0=300µm、σ_δ_p=1e-4、Q=100 fC、N=5e4
- 螺线管 k_s=22.38 m⁻¹（k_s²=500.65 m⁻²）、RF H=−9.78 m⁻¹、K_trans=−2.68 m⁻¹、k_rf=59.86 m⁻¹
- 样品面（no-SC）：AG σ_x=1984µm/σ_z=477µm；OCELOT σ_x=1996µm/σ_z=474µm
- SC 诊断（500 fC 漂移）：OCELOT σx 725→2436µm；AG 侧尚未做同等 SC 对比（Ne 语义未修，不可直接比）

## 24. 测试命令与协作约定
- 一键回归：`/opt/anaconda3/bin/python3 validation/run_all.py`（约 30-40 分钟，输出 6 项 PASS/FAIL + 样品面数值）
- 冻结表征：`... validation/test_r56_convention.py`（结果必须逐位不变）
- SC 调度：`... validation/test_sc_scheduler_equivalence.py`（native vs manual 事件对照 + production 验收 A–F，约 3 分钟）
- SC 诊断（manual characterization）：`... validation/sc_audit_diagnostics.py`（smoke + charge scan + convergence，只读）
- iCloud 同步：仅用户要求时使用 `scripts/sync_to_phone.py`；`--gpt-review` 为外部复核的可选打包模式，不是每轮自动执行的收尾动作。
- 任务输出与收尾规则：以根目录 AGENTS.md 当前版本为准，按任务规模说明结果、验证与开放问题；不再强制生成 GPT 审核文本或自动运行 gpt-review 同步。外部复核、手机同步与 Git 提交/推送按用户明确要求执行。
- 失败处理：按根 AGENTS.md 区分本轮非预期回归、原有缺陷和物理定义不足；暂停相关风险补丁，定义明确且已授权的原有缺陷可继续修复。禁止为拟合而调参。
- 与用户协作：物理假设、模型选择、验收标准由用户决定；AI 负责实现、文档、测试；禁止未经批准修改红线区

## 25. 交接自检清单（下个 session 开场必做）
- [ ] `git log --oneline -3` 确认 HEAD 与本文 §0 一致（或已更新）
- [ ] `git status --short` 工作树干净（handoff 提交后应无未提交改动）
- [ ] `git rev-parse v0.13-preSC-maintainability` 可回退点存在
- [ ] 读 §4 坐标约定（δ_p/p_oc/tau/z 语义）——所有改动的前提
- [ ] 读 §10 SC 结论——**禁止声称 SC fully validated**
- [ ] 读 §14 v0.14.1 任务书——按序执行，第一步是 scheduler 等价性证明
- [ ] 跑 run_all + r56 确认基线，与 §13 数值对照
- [ ] 任何新代码遵守红线（§17）与 AGENTS.md 规范

## 26. 与旧 session 的边界
- 上一 session 的最后结论：SC 审计完成、P0 修复落地（manual counter）、SC 诊断通过（smoke +236% 等）、no-SC 六项回归 + R56 全部 PASS、AG 位级不变
- 上一 session 的已知债务（v0.14.1 处理）：manual counter 等价性未证、AG Ne 语义未修、SC 状态机未建、SC 收敛参数未固化
- **v0.14.1 task 1/2/3（本 session）全部完成**：scheduler 迁移（§10）、AG charge semantics（§11）、SC runtime state contract（§12）
- 本 session 未做的事：冻结标签 v0.14.1-SC-integration-hardened（待用户确认）、SC 正式 beamline 对比（v0.15）、GUI、优化、任何 SC 参数调整

## 27. 返修轮交接（2026-09-14 暂停点，**代码已就绪、未提交/未推送/未同步 iCloud**）

> 本 session 只做「入口硬化审核返修」：在上一轮（v0.15 entrypoint hardening）**未提交的工作树之上**
> 打最小补丁，修复独立审计提出的 4 类残余缺陷。**未修改任何物理公式、shared 物理参数、baseline 或阈值**
> （唯一阈值改动是把被放宽的阻尼阈值**恢复**为 1e-12）。用户明确要求：本轮**不**自动 commit / push / iCloud 同步。

### 27.1 暂停时的确切状态
- 分支 `main`，**HEAD 仍为 `90e9684`（本轮无新 commit）**；工作树**不是 clean**：
  10 个已修改跟踪文件 + 8 个未跟踪新文件（见 §27.3）。上一轮成果全部保留，未被回滚。
- 全部验收与回归**已跑完并记录真实退出码**（见 §27.4），最后一项 `validation/run_all.py` = 退出码 0、6/6 PASS + `OVERALL: PASS`。
- 基线复核**不变**：canonical OCELOT hash `7790fd9c2a2b`、末点 777.0 mm；AG 完整确定性数组 hash `41f69f8ace7d`（σx=1984.191437 / σz=474.017607）；R56 slope −1.163624；config SHA 未变（`shared/` 未触碰）。
- 返修报告：`validation/reports/entrypoint_consistency_hardening.md`（**附录 R** 为本轮；§1–§12 为上一轮，未改写）。
- 审核汇总图：`validation/reports/review_summary.png`（生成脚本 `validation/make_review_summary.py`，运行时会重新实测四个面板的数值）。

### 27.2 本轮修了什么（按审核项）
1. **R1 `cfg_override` 真正生效**：新增 `run_params(cfg)` 作为**唯一**参数推导点；优先级 `显式参数 > cfg_override > 默认 config`；lattice 的 Solenoid `k`、RF kick 的 β/γ/E_total、probe 列表、步数、N、电荷全部走有效配置；不再读写模块全局。`results["run_params"]` 回执实际生效参数。
2. **R2 RF 开关单层化**：`resolve_switches()` 一次解析（cfg ← 显式 switches 的逐字段合并），组装与执行同源；RF 实例只按 `active_types` 保留几何；纵向/横向在 kick 函数内部独立门控。
3. **R3 probe 位置标记进最终输出**：`main()` 把 `z_actual_mm/z_exact` 传给 `make_probe`；控制台对非精确 probe 加警示；meta 持久化 SC 运行时契约与 `rf_kicks_applied`（实际执行次数）。并修掉一个真实缺陷：样品面 probe 因累计浮点误差（末步 49.99999999999999 mm）被闭区间判据丢掉 → 引入**纯舍入容差** `PROBE_TOL_M=1e-12 m`（不改步长/追踪路径），原始值始终写入 `z_actual_mm`。
4. **R4A** 阻尼阈值 `1e-9 → 1e-12`（恢复，未放宽）+ 从生产源码派生的**可恢复故障注入**（旧系数注入后判据必然 FAIL，恢复后逐位一致）。
   **R4B** RF 入口覆盖 → 4 入口 × 4 组合（新增 `validation.backend.run_ocelot`）。
   **R4C** `z_actual_mm % dz` 的 mm/m 混用修复。**R4D** 样品面对比前先断言轨迹覆盖（防 `np.interp` 端点钳位假通过）。**R4E** `git diff --check` 干净。

### 27.3 改动文件（绝对路径）
修改（本轮新增改动；其中 `GPT模拟/ued_beamline_v2.py`、`validation/CHECKPOINTS.md`、`validation/test_ag_acceleration_damping.py`、`validation/test_gpt_route_equivalence.py`、`validation/test_sc_scheduler_equivalence.py` 同时含上一轮改动）：
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/GPT模拟/ued_beamline_v2.py`
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_ag_acceleration_damping.py`
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_rf_switches_entrypoints.py`
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_gpt_tail_sample.py`
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_gpt_route_equivalence.py`
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_sc_scheduler_equivalence.py`（仅删一处行尾空格）
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/CHECKPOINTS.md`（追加 `[v0.15-entrypoint-hardening-repair]` 条目）
- `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/reports/entrypoint_consistency_hardening.md`（附录 R）
新增：`validation/test_gpt_config_override.py`、`validation/test_gpt_saved_output.py`、`validation/make_review_summary.py`、`validation/reports/review_summary.png`
（上一轮遗留的未跟踪文件：`test_gpt_sc_contract.py`、`test_gpt_tail_sample.py`、`test_rf_switches_entrypoints.py`、`test_run_all_exitcode.py`、`reports/entrypoint_consistency_hardening.md`）
**未触碰**：`AG/beam_dynamics_6d.py`、`AG/external_forces.py`、`AG/beamline_sim.py`、OCELOT 源码、`shared/*`（含 `beamline_config.yaml`、`sc_state.py`）、所有 baseline 数值。

### 27.4 交接复跑命令（真实退出码已记录，见附录 R6）
```bash
cd /Users/qin/Desktop/shuyan/Beam_dynamics_simu
export MPLCONFIGDIR=/tmp/mpl NUMBA_CACHE_DIR=/tmp/numba_cache     # OCELOT/numba 必需
/opt/anaconda3/bin/python3 validation/test_gpt_config_override.py      # rc=0  返修 1
/opt/anaconda3/bin/python3 validation/test_gpt_saved_output.py         # rc=0  返修 3
/opt/anaconda3/bin/python3 validation/test_rf_switches_entrypoints.py  # rc=0  返修 2/4B（4 入口×4 组合）
/opt/anaconda3/bin/python3 validation/test_ag_acceleration_damping.py  # rc=0  返修 4A
/opt/anaconda3/bin/python3 validation/test_gpt_tail_sample.py          # rc=0  返修 4C
/opt/anaconda3/bin/python3 validation/test_run_all_exitcode.py         # rc=0
/opt/anaconda3/bin/python3 validation/test_gpt_sc_contract.py          # rc=0
/opt/anaconda3/bin/python3 validation/test_benchmark4_scmech.py        # rc=0（≈6.4 min）
/opt/anaconda3/bin/python3 validation/test_sc_runtime_state.py         # rc=0
/opt/anaconda3/bin/python3 validation/test_ag_charge_semantics.py      # rc=0
/opt/anaconda3/bin/python3 validation/test_ag_alpha_coefficients.py    # rc=0
/opt/anaconda3/bin/python3 validation/test_r56_convention.py           # rc=0（slope −1.163624 必须逐位不变）
/opt/anaconda3/bin/python3 validation/test_sc_scheduler_equivalence.py # rc=0（≈5.3 min）
/opt/anaconda3/bin/python3 validation/test_gpt_route_equivalence.py    # rc=0
/opt/anaconda3/bin/python3 validation/run_all.py                       # rc=0，6/6 PASS
git diff --check                                                       # rc=0（无输出）
```
基线快照脚本（本 session 用的临时脚本，不在仓库内）：重建 canonical/AG hash 与 AG 样品面数值，用于确认 7790fd9c2a2b / 41f69f8ace7d / 1984.191437 / 474.017607 未变。

### 27.5 明天（下个 session）建议的下一步
1. **人工/GPT 审核**本轮附录 R 与 `review_summary.png`，特别是：`run_params()` 是否仍有遗漏的全局读取、`resolve_switches()` 的逐字段合并语义、`PROBE_TOL_M` 是否可接受。
2. 审核通过后再决定**是否提交**（用户未要求，故本轮未 commit）。建议提交范围：`GPT模拟/ued_beamline_v2.py`、5 个 validation 测试、`validation/CHECKPOINTS.md`、报告 + 图 + 生成脚本；**不要**把 `shared/results/` 或大数据产物加入。
3. 是否需要把两个返修验收测试（`test_gpt_config_override.py`、`test_gpt_saved_output.py`）纳入 `validation/run_all.py` 的 6 项列表——本轮**未加**（避免改动 `test_run_all_exitcode.py` 的 stub 列表），作为待决事项。
4. **仍未解决（登记，勿在未批准前动）**：AG 纵向矩变量衔接 —— `H=0` 的 `apply_rf_thin_lens` 仍无条件重设 `ν_z = C_zδ/(γ²σ_z)`（≈0.00106434 → ≈0.00000315857），与 SC 演化出的 `ν_z` 不自洽；422 mm 非对齐中间 probe 仍为步末采样 + 标注；SC 物理**未**完全验收（本轮只固化运行时契约）。

### 27.6 本轮已知残余风险（详见附录 R9）
`run_params()` 是唯一参数推导点但**无编译期保证**（新增物理分支若直接读模块全局会再次静默失效）；`resolve_switches()` 未出现的字段继承 cfg；`PROBE_TOL_M`/`sample_checked` 的覆盖裕度是新引入的经验容差；返修测试通过 `gpt.cfg = c` 在**进程内**注入配置，因此仍不是「真 CLI 子进程」验收。

## 28. 正式入口合并（2026-10-05，当前架构）

本节更新前面历史路由描述；旧测试记录按各自日期/参数解释。

- AG：`AG/run_shared.py` / `validation.backend.run_ag` → `AG.runner.run_from_config`。
- OCELOT：CLI / `validation.backend.run_ocelot` → `ued_beamline_v2.run_from_config` → builder / run_beamline。
- validation/backend.py 不再创建初态、组装元件或维护第二套追踪/RF循环；`_rf_constants` 仅保留原测试系数接口。
- AG 默认 coupling=False；OCELOT 默认dz读取配置。冻结1-mm回归需显式 dz=0.001；不要用变化后的默认值误判冻结数组变化。
- BeamResult 属于 shared，旧导入兼容。新增 test_runner_contract 注册到 run_all（现7项）。
- 最终 run_all 7/7、9项专项、14组前后数组通过。首次 solenoid 5-mm插值偏差2.48%失败保留；显式原1-mm条件后0.60% < 原1%，未放宽阈值。
- 无SC冻结摘要保持：AG 41f69f8ace7d，OCELOT 7790fd9c2a2b；config 23e97edb733b。核心/配置/基线/原结果文件保持。
- 待推进：AG纵向状态关系推导、OCELOT RF非对齐入口、SC收敛；不能因本次合并PASS声称完整SC+RF已物理验收。
- 详见 CHANGELOG_runner_unification_20261005.md、两路线 runner_physics_note.md、shared/beam_result_physics_note.md。
- 用户交付：outputs/ued_runner_merge_20261005.html；证据JSON、patch、zip同目录。测试日志/前后现场在 /tmp/ued_runner_merge_20261005/。
- 未提交、未推送、未iCloud同步，保留开始时已有未提交工作。

## 29. AG 纵向状态与 Gz（2026-10-16，更新当前物理状态）

- 用户选择：补齐论文纵向 Gz；初态采用共享束长和 sigma_delta，推导 AG 纵向发射度。仅恢复 Gz，横向 Gx/Gy 未恢复，横向发射度仍固定。
- 独立状态为 σz、νz、M=σz²(θz²−νz²)，按 Eq.(17)/(20) 配对演化；σδ=γ²θz、Czδ=γ²σzνz 从同一状态推得。公开历史仍保持 12 列。
- RF 输入先检查，按同一协方差作薄透镜；H=0 恒等，±H 可逆，行列式守恒。旧 SC→RF 的约 −99.7% 斜率跳变已修复。
- YAML 未改。历史 epsilon_nz_mm_mrad=0.02 仅记录来源，当前有效初态为 0.0196651503343；meta 明确 epsilon_configured_used=False。
- 新诊断位于 meta.longitudinal_evolution.history；纵向几何发射度与动量坐标归一化发射度名称区分。新 Note：AG/longitudinal_state_physics_note.md。
- 原有回归加新增专项共 8 组 PASS；纵向专项 15 项；电荷语义、阻尼、退出码另行 PASS；真实 CLI 保存的七项数组与正式 API 逐位一致。
- 第一个回归问题为阻尼测试人工初态 C=0、ν≠0；已改为相容初态，原阻尼公式/NU_TEST/阈值保持。零发射度案例另暴露机器舍入边界，按 64ε 明确识别/记录，有限负方差仍拒绝。
- 新 AG 无 SC 参考 hash：02012b2143f5（原 41f69f8ace7d 已作为旧记录保留）；σx=1984.189024、σz=473.922215 μm。新基线 JSON 单独保存原因与旧值；电荷测试原 1e-3 μm 阈值未改。
- OCELOT 无 SC canonical 实跑仍为 7790fd9c2a2b，config 仍为 23e97edb733b。共享物理配置、OCELOT 源码/库和原冻结目录未改。
- 完整 AG / SC ON 样品面：σz 1117.416172→524.432385 μm，σδ 7.00436328→4.70665942（×1e-3）。这是 AG 修复前后对照，不是完整 SC 跨模型验收。
- 短 PIC 对照：0.05 m / 100 fC / seed42 / N5000 / mesh33³ / dz1mm；σz 约差 1.89%，σδ 约差 11.47%。尚未作该案例统计/网格收敛，不调参消差。
- 仍开放：Gx/Gy、SC 模型和 PIC 收敛、非高斯/高阶动量学、OCELOT 非对齐 RF 事件、加速坐标；非零旧连续 chirp 回调现在显式报错，正式入口继续使用薄透镜。
- 本轮交付：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/ag_longitudinal_20261016/report.html。测试在 /tmp/ued_ag_step1_20261016/validation_copy，未重写原报告或基线档案。
- 未提交、未推送、未 iCloud 同步，保留此前未提交工作。禁止继续把旧“纵向状态待推导”或旧固定发射度描述当作新版状态。

## 30. 共同诊断、RF时间相位与AG Gx/Gy（2026-10-21，当前状态）

本节更新第28–29节的旧当前状态；历史数字和报告按原日期保留。

- 用户批准实施输出补齐、删除旧epsilon输入、Astra high独立RF推导、恢复Gx/Gy、有限SC对照。Astra保存推导/参考脚本后额度中断，主代理完成接续集成与验收。
- 仍是两模型各一个正式实现；未新增第三种模型、枪内发射/加速、样品衍射或探测器。
- 删除YAML epsilon_nz_mm_mrad=0.02。共享sigma_z/sigma_delta为准，推导epsilon；读到旧字段会警告且不覆盖正式初态。
- 共同JSON v2含15条历史数组：旧7条加C_zdelta_m、chirp_per_m、eps_nz_mm_mrad、eps_z_zprime_m、sigma_t_fs、energy_keV、beta_ref、gamma_ref。PIC使用中心化电荷权重矩、真实起点；AG中间probe插值协方差再推导。实际平面/插值方法显式记录。
- RF相位从Delta_t推导：H=Veff*k*cos(phi)/(beta^3*Etotal)。100keV约-17.8374 m^-1，旧约-9.77883。电压解释为有效积分电压，不任意再乘TTF；固定参考模型扣理论参考粒子增益。横向共同入口线性模型K=-H/(2gamma^2)，默认仍关。真实有限长度腔体物理仍待场图/电压标定。
- RF非对齐入口在SC ON/OFF均有精确事件测试；SC ON沿用原生Navigator调度，不另写SC计数器。
- AG演化Mx/My/Mz，恢复论文Gx/Gy。公开历史14列，前12列不变，后两列为实际eps_nx/eps_ny[m]。分段重建必须传完整行；旧11列接口不能恢复未提供的动态发射度。正式输出用实际ODE gamma，避免共享近似静能重推诊断；现存常量ppm差别明确记录而未全局迁移。
- RK45在1000fC新RF强压缩处发生非法试算阶段，现缩步重试；接受状态、原容差/阈值不变。指数正解的独立拒步检查通过。旧BeamlineSim sc_on=False也已修复。
- **实际新红旗**：100fC完整AG轨迹样点的kx/ky最大376.721，高于alpha表上界100，7/1999行越界。旧系数截断仍存在，本轮只增加警告和sc_alpha_table_domain记录，未无依据外推。该完整AG结果不作物理精度验收；下一步优先建立表内误差预算和越界策略。输出样点检查不能证明所有内部步均在域内。
- 50mm短漂移、100fC、PIC N50000/63^3/dz1mm/seed42：AG相对PIC束宽-0.066%、束长+0.033%、sigma_delta-9.947%、纵向发射度-69.807%。匹配初始保留矩后展宽/发射度残差仍在；Gx/Gy补齐不是非高斯模型升级。
- 有限控制：PIC 63^3→95^3时sigma_delta +0.295%、eps_nz +0.460%；dz1→0.5mm为+0.078%/+0.069%；seed42→43为-0.345%/-2.403%。另有N20000/50000、mesh33/63和10fC控制。只有两个种子，不是统计置信区间，也不是全束线SC收敛证明。
- 最终run_all实跑退出0，10/10组通过；相关专项（RF开关、配置覆盖、保存、尾段、电荷语义、阻尼、退出码、SC运行态、Gxy、共同诊断/RF）均退出0。写报告的测试运行于/private/tmp/ued_impl_20261021/validation_copy，原报告/CHECKPOINTS/旧基线未覆盖。
- 两模型正式CLI函数/API在指定有效设置下15数组相同（进程内真实驱动+保存验收，不泛称shell参数解析全验收）。无SC版本化基线：AG 62d55ac141e6，OCELOT 12c087cf62be；旧02012b2143f5/7790fd9c2a2b保留。新JSON单独记载RF/统计/采样/求解状态迁移原因，未放宽旧物理阈值。
- 长SC调度历史表征脚本本轮未完整重跑；只迁移其无SC版本化摘要。F07全局配置几何、F17alpha、F20历史原型隔离、F22可执行环境锁等仍开放，详见问题账本。不再把“所有历史问题都修好”作为结论。
- 交付：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/implementation_20261021/report.html。附原始数字、独立推导、测试退出码/日志、source_before/变化patch；CHANGELOG_shared_rf_gxyz_20261021.md及相关Physics Note。
- 图PNG已目视检查；HTML结构/本地链接检查，浏览器file访问受限未绕过，未做最终HTML浏览器渲染验收。未commit、未push、未同步外部服务，保留开始时已有未提交工作。

## 31. AG α 直接积分（2026-10-22，更新第30节F17状态）

- 本轮只执行路线图第1项：核查α表内精度和表外行为；没有进入下一阶段PIC适用范围/种子扫描、没有改RF或新增模型。
- 旧表域[0.01,100]的11×11扫描，最差单项是kx≈39.8107、ky=0.01的αyy，相对独立积分偏差55.38%；不能将其解释为默认末端束参误差55%。原表外截断问题亦确认。
- 新AG/alpha_coefficients.py直接算原论文九积分；正值对数变量分面板Gauss–Legendre，16/32点加阶检查（必要时64/128），相对检查5e-11；尾项有<2.7e-15解析相对界。域为每轴[1e-6,1e6]，非法或域外输入明确失败。该域是数值检验范围，不是物理模型适用域。
- 核心F/G共用一个alpha_at，无np.clip或旧表；无SC直接返回零SC力。get_alpha_interpolators仅保留旧脚本初始化/标量分量调用兼容，不再创建样条。
- sc_alpha_evaluation记录全部系数请求及内部试算范围，包含缓存请求；旧sc_alpha_table_domain只作旧表域对照，明确legacy_table_no_longer_used=True、gaussian_sc_uses_clipped_coefficients=False。新模块加入源码SHA256溯源。
- 248点对独立自适应积分，最大相对差7.8e-15；8组55位原s变量锚点最大相对差约6e-15。另有Carlson RD、球对称九项、x/y交换、加权恒等式、边界失败和缓存副本检查。最初极端比例的简单浮点参考报警，未当作最终基准，失败证据保留。
- 默认100fC完整AG：4314次系数请求，实际比例约0.06546–379.097，截断0次；加阶差最大约3.93e-15。最强压缩输出样点也经独立积分核对，不宣称每个内部点都另算独立参考。
- 默认末端相对旧版本：σx -0.01785285%、σz -0.01184684%、σδ -0.01310308%。高斯F/G模型、物理配置、常量、RF和OCELOT实现未改。不是靠拟合PIC消差。
- 无SC全部15条历史数组逐位保持；AG旧62d55ac141e6基线不变。正式CLI函数/API SC ON/OFF保存一致。相关专项7项和run_all均退出0；总回归新增alpha_numerics，现11/11组通过；旧阈值/基线不改。写报告的测试在/private/tmp/ued_alpha_20261022/validation_copy。
- F17的“旧表截断/未检查插值”数值缺陷已替换并在声明范围内验收；AG物理闭合、非高斯/高阶、PIC统计收敛与真实RF场仍开放。下一步才是路线图第2项，先少量固定短SC案例逐量判断，不全量重跑。
- 交付：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/alpha_accuracy_20261022/report.html；另有原始比较、55位锚点、误差预算、前后正式结果、日志、源码快照与本轮patch。
- 图PNG已目视核对；HTML结构/链接检查，浏览器file访问先前受限，本轮未绕过，未声称浏览器渲染已验收。保留已有未提交工作；未commit、未push、未同步外部服务。

## 32. 短SC逐量使用边界（2026-10-22，承接第31节后续）

- 本轮执行路线图第2步：100 keV、初始σx=σy=85 μm、σz=300 μm、σδ=1e-4、εnx/y=0.08 mm·mrad，50 mm无RF/磁透镜漂移；不改生产物理/共享配置/旧阈值/旧基线，不新增模型，不重跑完整束线。
- 新validation/sc_scope_study.py调用正式run_ag/run_ocelot，必须显式--out。Q=0/1/10/100 fC，每个Q主设置N50000/63³/dz1mm，五个分开的种子42/104729/130363/155921/196613；非零Q在seed42另作N20000、95³、0.5mm单因素控制，100fC加N20000/33³粗网格。31条计划记录全新生成，另一个廉价零SC步长对照；主运行退出0。
- 旧PIC的结果容器源码哈希不同、发行包版本元数据不完整，严格复用门槛未过。首次预检在第一条模拟前因版本查询退出；修为缺失即不复用，关键控制重算。10/100fC seed42哨兵可逐位复现旧端值，但未以此跳过本轮控制。OCELOT当前模块自报26.06.1。
- 每量分别比较AG/PIC均值差和5种子Student-t95均值半宽。再将N/mesh/dz所致模型相对差变动的绝对值之和作经验余量；不是严格误差上界或完整收敛证明。沿用现有尺寸5%、展宽2%、横向发射度5%作本次筛查目标；没有另造纵向发射度PASS阈值。
- 三个非零Q尺寸都支持本工况5%目标。Q1展宽均值差-0.18575%，经验范围[-0.90788,0.53638]%，支持2%；Q10为-3.94607%，范围[-4.90173,-2.99041]%；Q100为-9.83202%，范围[-11.66099,-8.00305]%，后两者不支持2%目标。结论不能外推到完整束线或RF强压缩。
- 纵向发射度均值差Q1/10/100为-0.25416%/-5.80400%/-69.47347%；Q100经验差异范围[-71.38822,-67.55873]%。初态保留二阶矩匹配后，Q10/100展宽仍-3.913%/-9.876%，纵向发射度仍-5.623%/-69.414%，名义初态抽样差异不能解释主要残差。
- 区分“总值接近”和“增长可预测”：Q100 PIC配对横向x/y发射度增长约2.975%/3.059%，纵向约227.017%；当前AG Gx/Gy/Gz在这些案例中变化均小于0.0002%，没有重现增长。横向总值在5%目标内不能当增长验收。低电荷微小横向增长未可靠分辨；差异未被本轮控制消除，不代表已证明全部由物理近似导致或PIC就是真值。
- 新增6项分析/适配契约检查通过；保存记录逐条验证有效SC/apply/0–50mm覆盖/无RF/实际端面，AGα全请求在域内且无截断。去chirp残差与εnz的恒等式核对；零SC步长最大端面相对变化5.44e-15。没有仅凭这些局部/工程检查宣称全SC物理通过。
- 报告/原始JSON/日志/计划/前后哈希/本轮patch位于：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/sc_scope_20261022/，主报告report.html。定义见validation/sc_scope_study_physics_note.md；不覆盖旧报告/默认结果。
- 路线图第1步α已完成，第2步本有限工况完成；第3步真实RF设备对应仍需电压定义/轴向场资料。本轮不继续强压缩扫描，也不重复已完成单步研究或擅自增加非高斯闭合。
- 图PNG目视检查；HTML结构/链接核查，浏览器file访问先前受限未绕过，不声称浏览器渲染验收。保留之前未提交工作；未commit/push/上传或同步。

## 33. 配置几何一致性（2026-10-22，额度重置后续接完成）

- 目标：配置可调，而 AG 显式位置与 OCELOT 累加长度不能解释成两条不同束线。新增 shared/geometry.py，不自动修复或重排；元件按顺序连续，长度/位置有限非负，RF/磁透镜正长，sample 唯一且零长末端，名称唯一，诊断面在轨迹内。只容纳 64 ULP 舍入（小于1 m时约1.42e-14 m）。
- YAML 加载、AG/OCELOT 正式 driver、OCELOT 独立 builder、config_check 共用校验；两模型 JSON 增加 meta.geometry。实际事件/端点仍核对 rf_events、history.z_mm、SC 覆盖；不把配置摘要当作实际执行证据。
- 几何专项最终8方法通过：RF 入口25 mm/腔长30 mm/样品67 mm，两后端API与CLI保存结果在SC ON/OFF下均符合；SC用N300、33³、dz1mm、seed42，检查事件与覆盖，不判定SC精度。各阶段磁透镜/RF占长保持，非法输入在模拟前失败。
- 8个相关专项脚本退出0（几何、cfg_override、保存输出、尾步、RF四开关、SC运行契约、SC状态、总测试退出码）。run_all 11/11组退出0；config_schema 另按最终8方法版本定向验收。可写测试在 /private/tmp/ued_geometry_20261022/validation_copy，不覆盖仓库已有结果/CHECKPOINTS。
- 另在 cli_copy 内实际改写 YAML 并启动独立 AG/GPT 脚本：SC ON/OFF 共4次退出0，保存结果RF实际25mm、末端67mm；2次非法配置均退出1并出现 rf1: gap，已有结果文件字节不变。保留逐进程日志、实际输入和保存JSON。
- 前后默认无SC正式API、默认N/seed/dz：AG/OCELOT各15条历史数组逐位相同。AG实际末点776.9999999999999 mm，OCELOT777.0 mm，保留舍入原值；未改物理公式、共享YAML、常量、旧阈值、基线。
- 首次测试曾把RF加长后的重叠误写为间隙，已改正预期；旧SC apply_count=0测试原先删掉所有实体元件却保留远处sample，现改为合法50mm束线并抑制Navigator的PhysProc交付，确认SC确因零执行而失败。两个首次失败日志保留，未放宽失败判据。
- 定义/使用示例：shared/geometry_contract.md、README「调整元件位置或长度」、CHANGELOG_geometry_20261022.md。当前薄透镜在RF入口作用，加长腔体不代表有限长度场；低层手工run_beamline仍由调用者保证lattice/配置一致。
- 完整报告、前后输出、复现脚本、日志、几何阶段patch/源码哈希：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/geometry_contract_20261022/report.html。额度暂停检查点另存，不丢弃原有成果。HTML只做结构/本地链接检查；先前浏览器file访问受限，本轮不绕过、不声称渲染验收。未commit/push/上传。


## 34. 当前状态入口与后续计算约定（2026-10-24，仅文档整理）

- 仓库已从 Desktop/shuyan 移到 Desktop/暑研/Beam_dynamics_simu；核对10月22日几何交付的108文件哈希，内容变化0项。最近动态验收日期仍是10月22日；本轮新模拟0、新物理测试0。
- 当前总入口为 PROJECT_STATUS.md，README 顶部链接；包含已完成/限域/开放状态、模型边界、参数单位、23项原问题的当前解释及下一步队列。保留全部旧报告，不把旧F17/几何open当当前状态；F07非几何验收完整性不因此关闭。
- CALCULATION_CARD_TEMPLATE.md要求每轮明确唯一问题、实际设置、参考、观测量/目标来源、误差余量、运行预算、退出码及完成条件。完成可为支持、不支持或证据不足；不要求强制吻合。
- “真值”分开处理：解析/独立积分验证规定数学问题；数值收敛给特定工况参考资格；实验带校准和不确定度验证装置。PIC不是无条件标准，经验控制不是完整上界；数学参考不是现实零误差答案。
- 推荐下一张卡C1：规定高斯入射下，独立积分正弦RF后的中心矩，量化AG线性化范围，再接正式短例；不是新增生产模型。C2按需补SC参考资格；C3才做固定磁透镜的SC×纵向RF四组合整线归因。当前均未执行。
- 整理报告、证据映射、当前问题JSON、前后保护哈希与本轮文档diff位于 /Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/project_status_20261024/。仅文档变更；不修改物理代码、YAML、旧阈值、基线或默认结果，不安装环境，不commit/push/同步。


## 35. C1 RF独立高斯数学参考（2026-10-24）

- 已完成上一节C1：新增验证层参考/研究/Physics Note/八项局部检查；生产模型、共享配置、旧阈值和基线不改。实际运行在隔离副本，不重写旧结果，不跑run_all。
- 三组规定RF入射σζ30/300/3000μm；100keV、σδ1e-4、C0、Veff30kV、f2.856GHz、φ3.1416；RF入口0m、样品22mm；无SC/磁透镜/横向RF。每模型各一次正式CLI main→driver→真实JSON，共六条短轨迹。不是六个独立shell CLI进程，也不是完整束线。
- 只读观察实际RF前后；高斯45/65位积分与特征函数互证。八项局部检查、45项数学/工程核对通过。AG对自身实际线性参考最大矩相对差3.74e-11；OCELOT同云时间公式逐点δ最大绝对差1.11e-16。大跨度AG残差消减已记录，未放宽阈值。
- 同一高斯与共同常量下，线性相对正弦的σδ差+0.00051836%/+0.0536320%/+5.40995%；εnz差约−0.00000002747%/−0.0274292%/−95.5044%。σδ的2%筛查仅支持前两例；chirp/ε没有新设物理PASS。300μm不代表默认整线实际RF入射，3000μm仅验证固定参考一阶动量坐标数学映射。
- 当前OCELOT生成器±5σ、500PDF节点、梯形CDF线性反演诱导499段均匀密度；总体RMS比名义高59.492ppm。独立GL8/16和65位区间积分交叉核对，输入固定偏差、有限云、实现、线性化分别列出。小新增非线性方差另展示精度，不冒称主要量1e-12检查覆盖所有小量。
- 单云等权IID/CLT渐近95%半宽；三组复用seed42不是独立重复，不能称多种子收敛或完整系统误差上界。Astra high只读独立推导/源码/结果审核未发现实质数学错误；没有额外生产轨迹。
- 留下两项单列边界：AG RF/粒子H既有常量差约2.070ppm，状态βγ约1.123ppm；RF位于s=0时AG history[0]为RF后、OCELOT为RF前。本轮以实际事件快照判断，不改生产常量/采样契约，不将出口漂移矩当瞬时RF后。
- 当前总表PROJECT_STATUS.md已更新。后续先复用资料核对整线实际RF入射和四处诊断；C2按目标量补SC数值资格；C3四组合整线归因仍未执行。真实场标定、共同加速和SC物理精度仍开放。
- 报告/计算卡/原始JSON/实际配置/快照/参考/日志/源哈希/保护核对/阶段patch：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/rf_reference_20261024/。定义见validation/rf_gaussian_reference_physics_note.md。
- PNG目视检查；HTML结构/本地链接检查。此前浏览器file访问受限，本轮不绕过、不宣称浏览器渲染验收。保留已有未提交工作；未commit/push/同步或上传。


## 36. C3前置：整线RF入射与诊断证据盘点（2026-10-24，新模拟0）

- 只读181份JSON与42份数组存档，提取17条完整覆盖记录（含重复保存，非17次独立模拟）；不重跑模拟或测试套件，不修改生产代码/配置/旧阈值/基线/默认结果。
- 10月22日无SC整线在400mm RF前，AG/OCELOT束长301.301804/301.341024μm，RMS相位跨度约0.03290rad；共同纵向统计可提取，原始RF入口云未保存，不能从二阶矩确认高斯。
- 正常400mm history点均为RF前；AG拼接删除RF后续段首点，粒子在下一推进前kick。瞬时RF后同面记录缺失，第一后续点为400.377377/405mm，有漂移；SC记录的下一点还可能含SC，不能直接作为RF效应。
- 历史SC入口约716μm且已有明显chirp；粒子N20000/dz1mm、AG来自后来α阶段，存在版本/配置差异，只作历史线索。RF前粒子εnz已约0.1329，不能把整线末态差异全归RF；没有据此确认最终SC物理原因。
- 无SC配置与当前默认一致，但运行内shared/params.py哈希a915…与当前84a4…不同；后来的108文件清单仅文档改变，不足以倒写运行内哈希，本轮未确认原因，不宣称严格当前复用。旧SC源哈希差异更多，缺本工况数值资格。
- 当前shared/results仍是旧JSON：缺C/chirp/εnz，GPT范围5→775mm、配置SHA不同；旧输出保留，不能据此指认当前起点/尾步修复失效。
- 已有无SC曲线最小束长样点约480mm、约5.6–5.7μm；到777mm样品约1113μm。是有限采样观察，不是精确腰点或自动调参目标。
- 下一项C3-A缩小为当前无SC整线每模型一次共2条，计入C3原8条基础预算；N50000/seed42/OCELOT显式dz1mm，保存实际RF前后同面状态/粒子云/完整正式JSON，再比较同云线性、同云正弦、匹配二阶矩高斯。尚未执行；其余SC资格/组合保持后续，不能外推短SC收敛。
- 报告/清单/数据提取/来源SHA/代码片段/下一卡/前后保护/阶段文档patch：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/rf_entry_inventory_20261024/。原HTML/结果不覆盖；PNG目视、HTML结构链接检查，不声称浏览器渲染验收。未commit/push/同步。


## 37. C3-A：当前无SC正式整线RF前后快照（2026-10-24）

- 按用户明确要求新增2条正式整线，AG/OCELOT main各一次，计入C3基础8条，已用2、剩6；C1短例不重复计入。本轮无额外正式轨迹、不跑run_all。
- 当前源文件隔离副本；完整共享几何/磁透镜/100keV/100fC，N50000、seed42、显式OCELOT dz1mm、AG默认n_points2000/原容差；SC OFF、纵向RF ON、横向OFF。
- 只读观察真实原RF函数前后。AG另观察原propagate返回位置，粒子记录parray.s；均在400mm，前后无漂移/SC混入，原函数一次；保存原始tau/p_oc/权重、AG状态及正式JSON、完整输入、源/库哈希。
- 正式捕获进程退出0、独立冻结分析退出0，14项数学/工程核对满足。第一次在/private/tmp误启动，validation尚未导入即失败，实际轨迹0，日志保留；正确目录后只有上述2条。生产代码/配置/阈值/旧基线/默认结果不改。
- 同一真实云/同一常量线性相对正弦RF：σδ差+0.0547908%、成对IID/CLT95%半宽±0.00105389个百分点，支持本工况2%展宽筛查；εnz差-0.0182525%、半宽±0.0208172个百分点跨零，不能称总体微小增长已分辨或全部量物理通过。
- 真实入射σζ301.34μm、h0.02859m⁻¹；匹配均值/A/B/C高斯与实际云正弦结果的σδ差-0.000590107%、εnz差-0.0101208%。包含有限样本/形状，不给无依据置信区间，不从边缘图/偏度峰度证明联合高斯。非零质心相位平移用45/65位积分/解析及GH64复核；既有常量ppm差异单列。
- 本轮回答“是否不断缩小范围”：是先隔离再合并，最终交付按工况/物理量的可信范围与必要修改清单。剩余6条分开无RF基准、纯SC、SC+RF；每项有完成条件，不自动无限加扫描/新模型。SC数字资格只按目标需要补，短漂移资格不外推整线。
- 报告/计算卡/两条实际JSON/快照/参考/脚本/日志/保护与文档patch：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/rf_entry_capture_20261024/。本轮只安装2份状态文档，分析工具不另加生产模块。
- PNG目视检查；HTML结构/本地链接检查，不宣称浏览器渲染。未commit/push/上传或同步。


## 38. C3四组合基础整线验收收口（2026-10-24，8/8条）

- 用户明确授权剩余6条；本轮新增SC0/RF0、SC1/RF0、SC1/RF1各两路线，按源/库/输入/输出SHA复用C3-A的SC0/RF1两条。基础预算8/8齐全，不自动追加扫描/模型/重构；不跑run_all。
- 固定100keV/100fC、初始85/300μm/σδ1e-4/εnx=y0.08、N50000/seed42、PIC63³/step1/dz1mm、原完整几何/磁透镜；横向RF关。正式AG/OC driver API各一次/新记录并用共同write_results保存；避开OCELOT main的自动无SC对照，未改生产代码。
- RF ON观察真实原函数前后400mm；RF OFF无瞬时变换，AG400mm用正式协方差插值明确non-exact，粒子实际400mm云保存。起点/400/样品粒子云、完整六维指纹、RF事件云、AG状态、实际SC覆盖/次数、所有输入/源/库/结果SHA保留。
- 新粒子三条初始数组指纹相同，复用那条初始统计相同；八条工程契约与独立冻结分析45项满足本卡目标。正式运行/分析退出码与日志见本轮报告。
- SC+RF样品AG相对OC：σζ+0.474%、σδ+0.364%、εnx-35.642%、εnz-86.135%。RF前εnz已经AG 0.0196651 vs OC 0.13866，主要差在RF之前，尺寸/总展宽接近不能替代发射度检验。
- RF两组对独立线性/时间正弦均满足原目标；同云线性化和匹配高斯差另列，不把输入/有限样本/常量差混作实现错误。四组合原单位因子分解B/R/S/I，百分比同分母，交互不当唯一微观原因。
- 当前边界：AG可作本例尺寸/趋势对照，但SC发射度/增长不能当可靠定量预测；本整线PIC只有一组N/mesh/dz/seed，无完整数值精度资格，不能指定真值/物理PASS。已有短SC控制不外推；只在研究目标需要时另立有限资格或模型选择任务。
- 本轮未发现需立刻修补的新RF/执行/保存实现缺陷；生产代码/默认YAML/旧阈值/基线/旧结果保持，仅更新当前状态文档。常量ppm/输出事件侧/环境锁与设备标定等开放项保留，不自动阻止本轮收口。
- 报告/计算卡/8条账本/实际JSON/云和状态/源与输出SHA/因子分解/日志/保护/文档patch：/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/beamline_acceptance_20261024/。PNG目视、HTML结构/本地链接核对；不宣称浏览器渲染验收。未commit/push/上传/同步。

## 39. OCELOT实际方法与低能局部参考（2026-10-25）

- 用户授权逐项复查并最小修复，复杂磁透镜问题启用Astra high独立只读推导。
- 原builder的全局字符串SecondTM被安装26.06.1静默回退为TransferMap；原模型标签不符实际。Solenoid原生二阶T又继承通用无场张量：同长度Drift/Solenoid T逐项相同，缺必要x*poc色差。
- 正式builder改为类对象、逐类显式请求：Drift SecondTM，Solenoid TransferMap；检查活动tms，失配硬失败。低层自建lattice仍按调用者选择，但准确记录caller_supplied与实际方法。
- JSON增加库版本、策略、限制与每元件tracking_methods。README/状态与Physics Note改称漂移二阶、磁透镜一阶，未更改安装库或新增磁场模型。
- 9项专项通过：独立质量壳漂移/截断阶数、一阶Hamiltonian磁透镜、已知原生二阶缺项、故障回退、短CLI/API/validation/保存一致性、短SC实际调用与事件/覆盖。新增组接入run_all，并验证退出码故障传播；本轮未运行完整run_all。
- 必要无SC整线预算2/2：同YAML/100keV/100fC/seed42/N50000/dz1mm；原12c087cf62be逐位复现，新b34afef25641。样品面εnz由0.01968765588变0.06242682855，尺寸/chirp变化很小。新日期OCELOT基线保留源/库/输入摘要，旧基线/结果/物理阈值不动。
- 原SC对比与有限敏感性研究属于旧传输方法，不直接作为新默认定量结论；AG独立数学/闭合推导保留。下一步SC场/kick局部参考与必要数值资格，非自动重复八条或升级新模型。
- 证据/脚本/原新共同JSON/独立Astra复核/测试/摘要/变更补丁/HTML：`/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/ocelot_method_acceptance_20261025/`。

## 40. O2-SC：局部场、kick与坐标独立核对（2026-10-25）

- 用户授权沿既定顺序继续；本轮无须复杂物理子代理。45项数学/执行检查通过，静态网格误差单独报告，未声称默认工况完整SC精度通过。
- 独立参考不调用AG公式或OCELOT坐标函数：高斯Coulomb积分以球高斯Gauss解析互证；原生/同时刻转换由质量壳/自由飞行定义推导；共同速度kick以全局矢量Lorentz投影推导。
- 静态potential两形状×33/63，直接场所选点误差3.8%–3.9%→1.1%–1.2%；对齐el_field 34/64所选点7.82%→1.92%。补1次非圆非轴64³控制，误差0.91%–1.85%、反对称残差约7e-15。非默认随机云误差界，不称完整收敛。
- 原生/独立坐标和规定场kick在预定舍入尺度内一致；匀强Ez空间功对冻结时间kick的有限步偏差按ds²缩放（40/20/10eV输入功，偏差约0.003047/0.0007618/0.0001904eV）。
- 仅1条2mm正式短漂移：100keV/100fC、N4000/33³/dz0.5mm/SC开RF关，4次真实SCapply。观察首步完整原函数的前后状态和场；独立回坐标更新最大poc差约7.30e-16。未重算整线。
- 总potential11（预算12）、el_field7、apply18（预算20，含规定场14+真实4）、完整轨迹0、ODE0；生产源码、共享输入、旧基线/报告与安装库未改，仅更新状态文档和新增Physics Note。
- 保留共同平均速度而非逐粒子速度的力近似；该首步冻结场下的力向量RMS差约0.0534%，不外推为整线/发射度误差。当前入口等权正电荷幅值；低能常量ppm/一阶delta适配、自由空间假设等仍有范围。
- 下一项O3当前方法下的有限数值资格；只对主要量/代表工况按预算补缺，不重做旧全部扫描，不升级AG。
- 报告/原始JSON/首步NPZ/独立reference.py/analysis脚本/预算/源与库摘要：`/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/ocelot_sc_local_20261025/`。

## 41. O3当前工况的有限数值敏感性已按预算收口（2026-10-25）

- 目的：当前漂移SecondTM/磁透镜TransferMap下，SC+纵向RF完整777mm束线对N/mesh/dz/seed的敏感性；不是全参数空间或实验精度认证。
- 预算与实绩：5/6条完整轨迹、6/6次已尝试；联合加密超时。前两条原结果完整复用，本次只续接未尝试项；单条1800秒、累计5400秒，失败/超时也计数，不追加或自动重跑。
- 联合加密因整轮累计90分钟预算结束，最后保存的进度为285.5mm，尚未到RF入口；实际仅保留初态粒子云、配置和进度，没有样品面JSON或末次进度位置的粒子云。不能把这一条作为完整联合加密比较。
- 固定100keV/100fC，初始85/300μm、σδ1e-4、εnx=y0.08mm·mrad；纵向RF开、横向RF关。基准N50000/63³/dz1mm/seed42；控制N100000、95³、dz0.5mm、seed43及联合加密，见specs.json。
- 本轮显式开启SC并使用1/0.5mm；共享YAML默认仍为SC关/dz5mm。5mm未在本轮检查，GUI不可将本轮范围自动贴到原默认或所有可调参数组合。
- 已完成设置的样品面相对基准最大绝对变化：σx 0.4747%、σy 0.3154%、σζ 0.08405%、chirp 0.007063%、σδ 0.08664%、εnx 1.095%、εny 0.2173%、εnz 1.798%。这是有限设置的观测幅度，不是误差上界或置信区间；基准与联合加密均不指定为真值。按观测量逐项看，尺寸相近不能代替发射度验收。
- 已完成五条各自保存初态/RF前/RF后/样品完整六维云、共同JSON和事件；实际覆盖、RF位置/次数、方法元数据、同N同seed初态指纹、原始云独立重算与发射度残余方差互证已有检查。细节见saved_verification.json；这些不代替物理验证。O3只研究OCELOT，未新增AG计算或更新两模型差异。
- 两层分辨率与两个种子不构成完整渐近收敛或统计估计，未新设物理PASS阈值。共同速度、自由空间、一阶delta适配、磁透镜色差与真实腔体标定等边界保留；改变能量/电荷/几何后不自动继承本工况结论。
- 生产公式、默认配置、安装库、旧基线和既有结果未改；本轮仅计算/分析/报告，并更新PROJECT_STATUS与AI_HANDOFF。未跑完整run_all；未提交/推送/上传/同步。
- 下一项：在这些明确边界下整理第一版GUI的配置编辑、几何校验、正式运行和结果展示；不将升级AG、全枪或真实有限场模型作为界面开发的前置条件。若研究目标要求更高精度，再为该目标单独决定数值预算。

报告、计算卡、账本、源/库摘要、原始云与独立重算：`/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/ocelot_stability_20261025/report.html`。

## 42. GUI v0.1 已实现（2026-10-25）

- 入口run_gui.py / 启动界面.command；gui/server.py负责本地HTTP与串行子进程，gui/worker.py只调用两条正式driver并复用共同保存，gui/web/为无外部依赖的中文页面。
- 工作配置按任务冻结，数据位于gui_runs/；不覆盖shared默认或旧结果。几何复用shared.geometry；mm界面与m配置在明确边界换算。
- 真正完成两条10mm无SC/带磁透镜和RF的工程短例；启动期取消之外另验证SC实际推进至1mm后停止。6项专项和桌面/手机浏览器交互检查通过；无新增完整SC轨迹、物理模型或阈值，未跑run_all。
- 使用范围和启动方式见gui/README.md；工程验收材料位于 /Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/gui_mvp_20261025/。未提交/推送/上传。

## 43. GUI Windows 兼容改造（2026-10-25）

- 起因：续接 outputs/windows_support_20261025（已定位未改代码）。本轮补齐启动器、进程创建/停止/超时/关闭清理、UTF-8 与中文空格路径、专项测试与文档；未重做物理审计、未跑长 SC 扫描。
- 实现：新增 gui/platform_compat.py（平台唯一分支点：spawn_kwargs/request_stop/force_stop/terminate_tree/process_alive/parent_alive/UTF-8 IO/worker_env）；server.py 取消/超时/关闭清理改走兼容层，worker 环境注入 PYTHONUTF8/PYTHONIOENCODING，run.log 二进制，JSON/YAML 显式 UTF-8，job.json 记录 worker_pid 仅作诊断；worker.py 父进程检测改 compat.parent_alive。
- Windows 入口：启动界面.bat（chcp 65001、%~dp0、优先 .venv、参数透传）、安装环境.bat（强制 CPython 3.12、venv、requirements-gui.txt）、运行GUI测试.bat；三个 .bat 为 CRLF 且内容纯 ASCII（避免 cmd 代码页解析问题）；新增 .gitattributes 固定换行。
- 依赖：requirements-gui.txt 精确 pin 到 macOS 验证版本；11 个包均有 cp312 win_amd64 轮子，ocelot-collab 26.6.1 为 py3-none-any；pyfftw 在 ocelot 中是 try/except 可选加速。证据见 gui/WINDOWS.md §5（元数据级，非实机）。
- 验证（macOS 3.12.2）：test_gui 6/6（基线亦 6/6）；test_platform_compat 29/29；test_gui_e2e 3/3（27.0 s，真实服务进程：短例完成 / 运行中取消→cancelled 且无 result.json / SIGINT 关闭后无遗留 worker）；test_windows_native 6 项 skip（无 Windows 主机）。
- 限制：没有 Windows 实机执行，Windows 原生测试与 .bat 双击流程未运行；OCELOT 路线未在 Windows 跑过；>260 字符长路径、杀毒/受控文件夹、关闭控制台窗口清理、端口 SO_REUSEADDR 差异均未实测。不宣称 Windows 全部通过。
- 未改物理核心、shared 参数与单位、默认束线 YAML、基线和旧结果；本轮未 commit/推送/上传。变更记录：CHANGELOG_windows_gui_20261025.md。

## 2026-10-26 文档与 Windows 复核修订

- 核对实际 GitHub main b4aa241；起始 README/平台文件与本地相同。发现 taskkill 非零误判成功、无界等待、Win32 HANDLE 签名/错误分类、watchdog 写失败退出和测试平台兼容问题，已本地修复。停止无法确认时暂停队列；安装器检查新旧环境 CPython 3.12 x64。
- 当前验证：单元/契约 46 通过、6 Windows 原生 skip；真实 GUI E2E 4 通过（两路线 10mm 正式短例、积分中取消和关服务）。两轮共 4 完整短轨迹 + 4 中断 SC 调用；无完整 SC 研究，无全套 run_all。Windows 实机尚未验证。
- 修订 README 旧 RF 公式、已修复电荷问题、配置示例和历史测试范围；项目文档升至 v1.1，附当前源码/证据。原 v1 ZIP 保留。物理核心、默认配置、数值阈值和旧基线未改。
- 报告：`docs/review_20261026/REVIEW.md`；测试日志/账本同目录。当前修改未 commit/push。
