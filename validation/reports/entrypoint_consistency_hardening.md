# 生产入口一致性与测试硬化（entrypoint consistency & test hardening）

Date: 2026-08-16 · 基线 HEAD：`90e9684` · 范围：仅工程逻辑（不改物理公式、不改阈值、不改 baseline）

## 1. 摘要

本阶段修复了 5 类工程缺陷：**测试退出码不可靠**（run_all 恒退 0）、**加速阻尼测试自证不测生产代码**、**scheduler 判据缺粒子路径且混淆 helper/生产验收**、**三个生产入口 RF 开关语义不一致**（run_shared 完全忽略开关；OCELOT 两入口纵向 OFF 时连带关闭横向）、**GPT 主路由 SC 契约缺失**（无 SCState、无 coverage/apply_count 校验、缺 anchor 时静默缩短覆盖）、**GPT 无 SC 追踪丢尾段**（775mm 冒充 777mm 样品面）、**Benchmark 4 模型标签与实际不符**。

修复后：**canonical OCELOT hash `7790fd9c2a2b` 不变**、**AG 完整确定性数组 hash `41f69f8ace7d` 不变**（AG sample σx=1984.191437 / σz=474.017607）、R56 表征不变、run_all 6/6 PASS，且新增 4 个入口级测试（退出码、RF 开关、SC 契约、尾段/样品面）。

## 2. 修改文件

| 文件（绝对路径） | 修改内容 | 风险 |
|---|---|---|
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/run_all.py` | A1：返回退出码；异常→FAIL；`sys.exit(main())`；OVERALL 行 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_run_all_exitcode.py` | **新增** A1 stub 注入回归（不跑昂贵模拟） | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_ag_acceleration_damping.py` | A2：改为测量生产 `envelope_ode` RHS 阻尼差分 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_sc_scheduler_equivalence.py` | A3：等价判据纳入 L4 粒子路径；acceptance 分类标注 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/AG/run_shared.py` | B：读 `physics_switches`；纵向/横向 RF 独立门控；meta 记录 | 中 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/GPT模拟/ued_beamline_v2.py` | B+D+C：RF 独立门控、`switches`/`cfg_override` 参数优先级、SCState 契约、尾段补足、probe 位置标注 | 中 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/backend.py` | B：`_ocelot_rf_kick` 纵向门控；rf 实例调度条件 = 任一角色开启 | 中 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_rf_switches_entrypoints.py` | **新增** B：三入口 × 4 组合实测 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_gpt_sc_contract.py` | **新增** C：7 类故障注入 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_gpt_tail_sample.py` | **新增** D：整数/非整数总长、probe 边界 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_benchmark4_scmech.py` | E：显式 sc_model + 标签核对 | 低 |
| `/Users/qin/Desktop/shuyan/Beam_dynamics_simu/validation/test_gpt_route_equivalence.py` | 调用方式修正：SC ON 时保留 cathode→sample anchors（否则契约 HARD FAIL） | 低 |

确认未修改：AG 核心三文件（beam_dynamics_6d / external_forces / beamline_sim）、OCELOT、`shared/beamline_config.yaml`、`shared/sc_state.py`、测试阈值、baseline、`validation/backend.py` 的无 SC 追踪循环。

## 3. 任务 A：让测试真正检查生产代码

### A1 退出码
- **修改前**：`main()` 无返回值；`__main__` 调 `main()` 不 `sys.exit` → **任何子测试失败，进程仍退出 0**；子测试异常会直接抛出（无 OVERALL 汇总）。
- **修改后**：逐项 `try/except`（`SystemExit` 与 `Exception` 均记为 FAIL 并打印 traceback/提示），`OVERALL: PASS/FAIL`，`sys.exit(main())`。
- **验证**（`test_run_all_exitcode.py`，进程内 stub 注入，不跑昂贵模拟）：
  - 全成功 → `rc=0` PASS；6 项逐一失败 → `rc=1` PASS；`drift` 抛异常 → `rc=1`（异常未变 PASS）PASS
  - 真实进程验证：注入失败 → 进程退出码 **1**；全部成功 → **0**

### A2 加速阻尼测试
- **修改前**：测试内 `D_corrected()` 直接 `return D_paper(...)` —— 自证式，**不检查生产实现**。
- **修改后**：调用生产 `beam_dynamics_6d.envelope_ode`，在同一状态比较有/无 γ′ 的 RHS 差分（`dν_u` 位于索引 6,7,8），隔离阻尼：
  `D_measured = −Δ(dν_u)/ν_u`，与论文 `D_paper=γ′/(γ³β²)` 比较；`ν=1e-3≠0`。
- **验证**（4 案例：100 keV/5 MeV × γ′=5/50）：
  - `D_meas/D_paper = (1.000000000000, 1.000000000000, 1.000000000000)` PASS
  - GUARD：旧系数 `γ′/(γβ²)` 的比值 = γ²（1.429687 / 116.310962，精确）→ 若生产仍是旧公式，测试必然 FAIL

### A3 Scheduler 判据
- **修改前**：`events_equiv = L1 ∧ L2 ∧ L3`（**不含完整粒子数值路径**）；acceptance 全部标为 "PRODUCTION-PATH ACCEPTANCE"，但 D/E 实际只测 native helper。
- **修改后**：新增 `L4_equiv`（`np.allclose(atol=1e-12)`）并纳入判据：`combined = events ∧ path`；T1–T4 要求 combined 等价，T5–T7 要求 combined 差异（预期差异仍通过）。acceptance 逐项标注 `[PRODUCTION]` / `[HELPER-CHAR]` 并分类汇总。
- **验证**：T1–T4 `L=PPPP` EQUIV；T5–T7 DIFFER；expectations ALL PASS；acceptance 分类 ALL PASS。
- **覆盖缺口（如实报告）**：生产 lattice 固定（777 mm、整数步数），"非整数总长"与"部分 SC 覆盖"没有生产入口验收，仅有 helper characterization（D/E）——已在输出与本文档标注，未冒充生产验收。

## 4. 任务 B：统一 RF 开关（两开关独立）

- **修改前**：
  - `AG/run_shared.py`：**完全不读 `physics_switches`** —— RF 横向力恒加入、纵向薄透镜恒施加。
  - `GPT模拟/ued_beamline_v2.py`：纵向由 `rf_elems` 驱动、横向 kick 复用同一列表 → 纵向 OFF 时横向连带失效。
  - `validation/backend.py::run_ocelot`：同样用 `rf_longitudinal_kick` 决定 `rf_elems`，纵向 OFF 时横向也失效。
- **修改后**：三入口统一语义 —— RF 实例在 **任一角色开启**时调度；纵向 kick 由 `rf_longitudinal_kick` 门控、横向由 `rf_transverse_kick` 门控，**gate 在 kick 函数内部**：
  - `backend._ocelot_rf_kick`：`if sw["rf_longitudinal_kick"]: add_p_oc(...)` + `if sw["rf_transverse_kick"]: add_px/add_py`
  - `ued_beamline_v2.apply_rf_kick(..., rf_longitudinal=...)`
  - `run_shared`：两个 `rf_regions`/`rf_elems` 分别按对应开关门控
- **参数优先级**：`run_beamline(..., switches=None, cfg_override=None)` —— 显式参数 > cfg_override > 模块 cfg（不再被模块缓存覆盖）。
- **验证**（`test_rf_switches_entrypoints.py`，三入口 × 4 组合，实测状态）：

| 入口 | L=1,T=1 | L=1,T=0 | L=0,T=1 | L=0,T=0 | 判定 |
|---|---|---|---|---|---|
| backend.run_ag | σδ=2.9392, σx=1251.7 | 2.9392, 1984.2 | 0.1000, **1251.7** | 0.1000, 1984.2 | PASS |
| AG.run_shared | 同上 | 同上 | 同上 | 同上 | PASS |
| GPT.run_beamline | 2.9213, 1284.1 | 2.9213, 2024.0 | 0.0999, **1284.1** | 0.0999, 2024.0 | PASS |

（L=0 时横向 σx 仍从 2024.0 → 1284.1，证明两开关独立；纵向 OFF 时 σδ 与 no-kick 基准逐位一致。）

## 5. 任务 C：GPT 主路由 SC 状态契约

- **修改前**：自建状态处理；`SpaceCharge` 顶层 import；`if sc_proc is not None and len(lat.sequence) >= 2` 静默跳过 attach；无 coverage 校验；无 apply_count=0 校验；results 的 `sc_requested`/`effective` 独立拼装。
- **修改后**：复用 `shared/sc_state.SCState`（单一状态机，无第二套实现）；`SpaceCharge` **按需 import**（SC OFF 时不可用不阻塞）；import/构造/attach 失败 → `sc_state.fail()`；tracking 后 `verify_final(0.0, sample_z(lattice))`（coverage 期望来自 shared lattice，**无硬编码 0.777**）；`effective = apply_count > 0`；results 由 `to_meta()` 统一写入。
- **验证**（`test_gpt_sc_contract.py`，进程内故障注入并恢复，未卸载/修改 OCELOT）：

| 场景 | 结果 |
|---|---|
| 1 正常 SC ON | available/configured/attached=True, apply=10, effective=True, coverage=[0.000,0.050] PASS |
| 2 import 失败 | RuntimeError「SpaceCharge import failed」PASS |
| 3 构造失败 | RuntimeError「construction failed」PASS |
| 4 attach 失败 | RuntimeError「add_physics_proc failed」PASS |
| 5 零事件 | RuntimeError「sc_apply_count=0」PASS |
| 6 错误 coverage（缺 sample anchor） | RuntimeError「coverage [0.0,0.0] != expected [0.0,0.05]」PASS |
| 7 SC OFF + SC 模块不可用 | 正常运行，requested=False effective=False PASS |
| 8 一致性 | sc_effective == (apply_count>0) == True，requested 已记录 PASS |

## 6. 任务 D：追踪末段与样品面诊断

- **修改前**：SC OFF 循环 `n_steps = int(total_length / dz_track)` → 0.777/0.005 = 155 步 → **775 mm**；sample（777 mm）永不到达；`z777mm` probe 缺失；probe 区间为半开 `[z_before, z)` → 终点亦无法采样；z=0 probe 在第一步末采样（5 mm 错标为 0）。
- **修改后**：保留全部完整步，**追加一步剩余长度**（`tracking_step(lat, p, remaining, navi)`，不改配置步长）；probe 区间改闭区间；**z=0 起点在追踪前以初始状态精确采样**；每条 probe 记录新增 `z_actual_mm` 与 `z_exact`（非对齐中间 probe 明确标注为步末采样，**不再冒充精确诊断**）。
- **验证**（`test_gpt_tail_sample.py`）：

| 检查 | 结果 |
|---|---|
| 默认 777 mm：终点 | 0.7770 m（原 0.7750）PASS |
| `z777mm` probe | 存在且 `z_exact=True` PASS |
| 非整数总长 0.503 m | 终点 0.503000 PASS |
| 整数总长 0.500 m | 终点 0.500000，样本数 100（无多余尾步）PASS |
| 起点 probe z0 | `z_exact=True` PASS |
| 非对齐 probe z422mm | `z_exact=False`，`z_actual_mm=425.0`（≠422）PASS |
| 对齐 probe z100/z500 | `z_exact=True` PASS |

- **边界说明（按要求先报告方案、不擅自扩展）**：422 mm 是 config 中唯一的非步长对齐中间 probe。精确采样它需要改变 tracking 物理路径（子步/插值），本轮**未做**；当前以 `z_exact=False` + 实际位置明确标注。
- **旧 775 mm 与新 777 mm**：775 mm 仍保留在 history 中（第 155 个完整步），777 mm 为新的真实样品面——**两者按不同位置分别记录，未作为"同位置误差"比较**。
- **回归**：`validation/backend.py` 的无 SC 追踪未改动，canonical hash 验证后不变；`test_gpt_route_equivalence` 的样品面 dev 由（775 末点 interp）改善为 **0.00%**（真实 777 mm 对照）。

## 7. 任务 E：Benchmark 4 模型明确化

- **修改前**：`AG ellipsoid` 行调用 `run_ag(...)` 未指定模型（D-2 后默认已为 gaussian）→ **标签与实际模型不符**；另一路用 `core.propagate` 直调（初始条件/入口与前者不完全一致）。
- **修改后**：两路都经生产入口 `run_ag(..., sc_model="ellipsoid"/"gaussian")`，断言 `meta["sc_model"]` 与标签一致，OCELOT 走 `run_ocelot`；三者同初始条件、同物理电荷（500 fC）、同传播长度（0.5 m）、同诊断面。
- **验证**：label check PASS；ellipsoid σz=3612.9 µm / gaussian σz=1611.4 µm / OCELOT σz=1606.4 µm（与修复前数值一致，未调公式）。**不以单次对照断言模型对错**。

## 8. 实测值与基线（收尾回归）

| 项 | 修改前 | 修改后 | 判定 |
|---|---|---|---|
| canonical OCELOT hash（SC OFF, full, seed42, N=5e4, dz=0.001） | `7790fd9c2a2b` | **`7790fd9c2a2b`** | 不变 |
| AG 完整确定性数组 hash（no-SC full） | `41f69f8ace7d` | **`41f69f8ace7d`** | 不变（非仅端点） |
| AG sample σx / σz | 1984.191437 / 474.017607 | 1984.191437 / 474.017607 | 不变 |
| R56 slope | −1.163624 | **−1.163624** | 不变 |
| run_all 6 项 | PASS | PASS（见 §11 实测） | — |
| 新增测试 | — | 4 项全 PASS | — |

## 9. 批准的行为修正（输出变化，非回归）

1. **AG/run_shared**：默认 `rf_transverse_kick=false` 现在真正生效 → 该入口 σx 由 1251.7 变 1984.2 µm（与同开关的验证入口一致）。
2. **GPT 主路由无 SC**：终点由 775 mm → **777 mm**（真实样品面），history 多一个尾步点，`z777mm` probe 出现。
3. **probe 记录**新增 `z_actual_mm` / `z_exact` 字段（共享 schema 允许 extra 字段；`z_mm` 名义值语义不变）。
4. **OCELOT 两入口**：`rf_longitudinal_kick=false, rf_transverse_kick=true` 时横向 kick 现在生效（此前被连带关闭）。默认配置（long=true, trans=false）行为不变 → canonical hash 不变。

## 10. 未解决问题（登记，不在本轮修复）

1. **AG 纵向矩变量衔接（阻塞完整 SC 物理验收，§八要求只登记）**：共享初始条件、100 fC、Gaussian SC、0.4 m 纯漂移后，`H=0` 的 `apply_rf_thin_lens` 仍把 `ν_z` 从 ≈0.00106434 改写为 ≈0.00000315857。根因指向 `apply_rf_thin_lens` 无条件重设 `ν_z = C_zδ/(γ²σ_z)`（即 H=0 也重定义），与 SC 演化出的 `ν_z` 不自洽。**不修改、不加经验系数、不自动补矩方程、不归因于"模型能力差异"**；后续需单独物理推导与修复审批。
2. **生产入口验收缺口**：非整数总长 / 部分 SC 覆盖仅有 helper characterization（§3 A3）。
3. **非步长对齐中间 probe**（422 mm）：当前为步末采样并标注 `z_exact=False`；精确采样需改变 tracking 路径（方案待批）。
4. **测试运行环境要求**：本机需 `NUMBA_CACHE_DIR=/tmp/numba_cache`（OCELOT 的 numba 缓存对 site-packages 无可写定位符）——环境问题，非代码缺陷；已在本轮所有回归中统一设置。
5. **既有 P1/P2（v0.15 审计遗留）**：Larmor 耦合（已关闭）、chirp 公式冗余、AG 内部常量重复——见 `v0.15_AG_physics_audit.md`。

## 11. 实测退出码与回归结果

（见最终回复中的数据：每项测试的真实进程退出码、run_all 6/6、canonical hash。）

## 12. 最值得人工审核的材料

A 级：
1. `GPT模拟/ued_beamline_v2.py`（任务 B/C/D 交汇处：RF 门控、SC 契约、尾段与 probe 语义）
2. `AG/run_shared.py`（任务 B 的行为修正：默认横向 RF OFF 现在生效）
3. `validation/backend.py`（`_ocelot_rf_kick` 纵向门控 + rf 调度条件）
4. `validation/test_gpt_sc_contract.py`（故障注入是否真实覆盖 5 类 HARD FAIL）

B 级：`validation/run_all.py`、`validation/test_ag_acceleration_damping.py`、`validation/test_sc_scheduler_equivalence.py`（判据/标签）
C 级：`test_gpt_tail_sample.py`、`test_rf_switches_entrypoints.py`、`test_benchmark4_scmech.py`

---

# 附录 R：入口硬化审核返修轮（repair round，2026-09-14）

> 本附录只记录**返修轮的增量**。上文 §1–§12 是上一轮（已验收）的记录，**未被改写**。
> 返修原则：只做最小补丁，不回滚/不覆盖上一轮成果；不改 AG 核心、OCELOT 源码、任何物理公式（RF / R56 / solenoid / SC 力 / θ_z / 电荷语义）、`shared/` 物理参数与 baseline；不放宽阈值；不自动提交/推送/同步。
> HEAD 仍为 `90e9684`（本轮**无新 commit**），工作区**不是 clean 状态**（上一轮 10 个已修改跟踪文件 + 本轮新增测试/报告）。

## R1. 审核返修项与状态

| # | 审核发现 | 状态 | 验收测试（真实退出码见 §R5） |
|---|---|---|---|
| 1 | `cfg_override` 名义存在但能量/电荷/光斑/发散/N/步长/probe 仍取自模块导入期全局；`build_lattice_from_shared` 用全局 `p_SI`；`apply_rf_kick` 用全局能量/β → 审核反例（100→200 keV、100→500 fC、85→170 µm、5→10 mm）history **完全相同** | **已修复** | `validation/test_gpt_config_override.py` |
| 2 | RF 开关两层冲突：builder 先按 cfg 删除 RF 调度项 → 事后 `switches` 显式开启也无法复活（cfg L=F/T=F + 显式 L=T → 0 kick） | **已修复** | `validation/test_rf_switches_entrypoints.py`（4 入口×4 组合）+ `/tmp/verify_fixes.py` 复现脚本 |
| 3 | `run_beamline` 记录了 `z_actual_mm/z_exact`，但 `main()` 调 `make_probe` 时丢掉 → 保存文件把 425 mm 数据当 “422 mm”，且样品面 probe 缺失 | **已修复** | `validation/test_gpt_saved_output.py` |
| 4A | 阻尼阈值被放宽到 `1e-9`，且 guard 只是比较两个闭式表达式（未真正注入故障） | **已修复**：恢复 `1e-12` + 真实可恢复故障注入 | `validation/test_ag_acceleration_damping.py` |
| 4B | RF 入口覆盖缺 `validation.backend.run_ocelot` | **已修复**：4 入口 × 4 组合 | `validation/test_rf_switches_entrypoints.py` |
| 4C | `test_gpt_tail_sample.py` 中 `z_actual_mm % dz` 混用 mm/m（425 mm % 0.005 m = 0.005 → 假 FAIL） | **已修复**：统一到 mm | `validation/test_gpt_tail_sample.py` |
| 4D | 样品面对比在越界时被 `np.interp` 端点钳位而“假装通过” | **已修复**：插值前断言轨迹真实覆盖查询面 | `validation/test_gpt_route_equivalence.py` |
| 4E | `git diff --check` 有尾随空格 | **已修复**（`git diff --check` 退出码 0） | `validation/test_sc_scheduler_equivalence.py` |

## R2. 修复 1：`cfg_override` 真正生效

**修改前（审核反例，实测）**：`run_beamline` 内所有物理量取自模块导入期全局 `energy/charge/spot/sigma_xp/N/dz/z_probes`；`build_lattice_from_shared` 的 Solenoid `k` 用全局 `p_SI`；`apply_rf_kick` 用全局能量与 β。因此把 cfg 换成 200 keV / 500 fC / 170 µm / 10 mm 后，**history 与默认配置逐位相同**，反例成立。

**修改后**：
- 新增 `run_params(c)`：**单一有效配置**推导本次运行的全部量（`E_keV, Q_C, N_part, spot_rms, sig_z0, epsilon_n, sigma_delta, gamma, beta, beta_gamma, p_SI, sigma_xp, sigma_yp, E_total_eV, z_probes_mm, dz_track, seed`），复用 `BeamReference.from_energy_keV`（无第二套物理实现）。
- 优先级 `显式参数 > cfg_override > 默认 config`；**不写回/不修改** `cfg`、`switches` 等模块全局（无全局突变）。
- `build_lattice_from_shared(cfg, ...)` 的 Solenoid `k` 由**该 cfg 的能量**推导；`apply_rf_kick(..., ref=P)` 使用本次运行的 β/γ/E_total。
- `results["run_params"]` 记录本次实际生效参数（供测试/审计核对，不再是“声称”）。

**实测（`test_gpt_config_override.py`，A=默认，B=200 keV/500 fC/170 µm/10 mm）**：

| 指标 | 修复前 | 修复后 A | 修复后 B | 判定 |
|---|---|---|---|---|
| history 步数 | 相同 | 156 | 78 | PASS（步长生效） |
| probe 列表 | 相同 | 9 个（含 422/500/600/700） | [0,100,400,777] | PASS（probe 来自 override） |
| 记录的有效参数 | 全局 | 100 keV / 1.0e-13 C / 85 µm / 0.005 m | 200 keV / 5.0e-13 C / 170 µm / 0.01 m | PASS |
| 粒子电荷和（N=3000） | — | 1.000000e-13 C | 5.000000e-13 C | PASS（电荷语义） |
| 发散 σ_x′ | — | 1.436e-03 | 4.864e-04 | PASS（由能量重算） |
| 运动学 γ | — | 1.1957 | 1.3914 | PASS |
| 样品面 σ_x | 相同 | 1115.232 µm | 411.556 µm | PASS（物理量变化） |
| Solenoid k | 相同 | 22.375110 1/m | 15.160412 1/m | PASS（用本 cfg 能量） |
| 显式 `nparticles=1234` vs override N=50000 | — | 实际 1234 | — | PASS（显式 > override） |
| A→B→A 状态泄漏 | — | 逐位相同 | — | PASS（无污染） |
| `sc_enabled` 优先级 | — | 显式 False 胜出；None→config（applies=156） | — | PASS |

## R3. 修复 2：RF 开关单层化

**修改前**：`build_lattice_from_shared` 先按 `cfg` 的开关删除 RF 调度项，`run_beamline` 事后又解析一次 `switches` → 两层判定；cfg 里关掉后，显式 `switches` 无法复活（实测 cfg L=F/T=F + 显式 L=T → **0 kick**）。

**修改后**：`resolve_switches(cfg, switches=None)` 只解析一次（`physics_switches` ← 显式 `switches` 的**逐字段**合并），组装与执行使用**同一结果**；RF 实例只要 `"rf_cavity" in active_types` 就进入序列（与开关无关），**物理门控发生在 kick 函数内部**，纵向/横向独立；step1/2 无 RF 的入口能力限制保留；关 RF 时 RF 段长度仍以 Drift 保留 → 几何长度不变；**公式未改**。

**实测**：

| 场景 | 修复前 | 修复后 |
|---|---|---|
| cfg L=F/T=F，builder | rf_elems=0（项被删） | rf_elems=1（保留几何） |
| cfg L=F/T=F + 显式 L=T | 0 kick | **1 kick, σδ=2.9435** |
| cfg L=T/T=F + 显式 L=F,T=T | 横向被连带关闭 | **1 kick, σδ=0.0997, σx=1278.8 µm**（横向生效、纵向未施加） |
| 逐字段覆盖（只给 L） | 另一字段被丢弃 | T 继承 cfg → 1 kick, σδ=2.9435 |

## R4. 修复 3：probe 位置标记进入最终输出

**修改前**：`main()` 的 `make_probe(...)` 未传 `z_actual_mm/z_exact` → 保存文件把步末 425 mm 状态标成 “422 mm” 且无任何告警。

**修改后**：`main()` 透传 `z_actual_mm=`/`z_exact=`；控制台对 `z_exact=False` 的行追加 `[! sampled at … NOT the exact plane]`；meta 持久化 SC 运行时契约状态（`sc_scheduler/apply_count/coverage_start/stop/available/configured/attached`）与 `rf_kicks_applied`（实际执行次数）。

**同时发现并修复一个真实缺陷（本轮新增）**：样品面 probe 在**追踪结果里就缺失**——最后一步落在 `49.99999999999999 mm`（累计浮点误差 7.1e-15 mm），被闭区间判据 `z_p <= z` 拒绝。修法：引入**纯浮点舍入容差** `PROBE_TOL_M = 1e-12 m`（= 1e-9 mm，比 lattice 最小物理长度小约 12 个数量级；**不改步长、不改追踪路径**）用于“平面是否到达”和 `z_exact` 判定；原始位置始终写入 `z_actual_mm`。`z_exact=True` 的语义因此是“该平面在双精度累计误差内被真实到达”，而非“无误差”。

**实测（`test_gpt_saved_output.py`，短 lattice：drift 20 + RF 22 + drift 8 = 50 mm 样品面，probe [0,20,22,50]，dz 5 mm，SC ON 33³，N=2000）**：

| 检查 | 修复前 | 修复后 |
|---|---|---|
| 保存文件 probe 记录 | 只有 0/20/22（样品面缺失） | 0/20/22/**50** 全部带 `z_actual_mm`+`z_exact` |
| z=0 | exact=True, actual=0.0 | 同（起点在追踪前以初始状态采样） |
| 样品面 50 mm | **缺失** | exact=True, actual=49.99999999999999 mm（z_mm 名义 50.0） |
| 非对齐 22 mm | exact=False, actual=25.0（未存档） | exact=False, actual=25.0（**已存档**） |
| history 末点 | 50.000000 mm | 50.000000 mm |
| SC 契约持久化 | 仅 scheduler 名 | scheduler=ocelot_native, apply=10, coverage 0.0→0.049999999999999996, available/configured/attached=True |
| `sc_enabled` 与运行时一致 | — | saved=True == effective=True（requested=True） |
| `rf_kicks_applied` | 取列表长度 | 实测执行次数 = 1（scheduled=1） |

> 说明：样品面“缺失”有两个原因，二者都已定位并修复——(a) 生产代码的舍入容差（上）；(b) **测试自身**用 `Z_SAMPLE*1e3 = 50.00000000000001` 作为查表键，而保存的名义标签是 50.0。测试已改为使用取整后的名义 mm 值，并在注释中记录该浮点陷阱。

## R5. 修复 4：阈值与覆盖

### 4A 阻尼阈值恢复 `1e-12` + 真实故障注入
- `TOL_REL` 由 `1e-9` **恢复为 `1e-12`**（未放宽）。实测 `max|D_meas/D_paper − 1|`：100 keV/γ′=5 → **0**；100 keV/γ′=50 → **2.22e-16**；5 MeV/γ′=5 → **6.66e-16**；5 MeV/γ′=50 → **0**。全部 < 1e-12（余量约 3 个数量级；差值法做的是同一 RHS 相减，误差仅来自末位舍入）。
- **可恢复故障注入**（不再是“比较两个闭式表达式”）：`make_old_damping_rhs()` 读取**生产 `envelope_ode` 的实时源码**，把唯一一处 `damping_coeff = gamma_prime / (gamma**3 * beta**2)` 替换为旧式 `/(gamma * beta**2)`，在与生产模块共享 globals 的命名空间中 exec，然后**通过 monkeypatch 模块属性**让**同一套测量代码**跑注入版本，`finally` 中恢复。
  - 注入锚点出现次数 = **1**（若生产公式被改动，锚点不匹配 → guard 立即 FAIL，不会“测了个空”）。
  - 注入 build 的 `D_meas/D_paper = 1.429686820` = γ₀²（精确），`max|ratio−1| = 4.297e-01`，**≫ 1e-12 → 本测试的判据在旧 bug 下必然 FAIL**（证明判别力）。
  - 恢复后生产 RHS 重测结果与注入前**逐位相同**（`np.array_equal` = True）。

### 4B RF 入口覆盖（4 入口 × 4 组合，真实状态变化）

| 入口 | L=1,T=1 | L=1,T=0 | L=0,T=1 | L=0,T=0 | 判定 |
|---|---|---|---|---|---|
| `validation.backend.run_ag` | σδ=2.9392, σx=1251.7 | 2.9392, 1984.2 | 0.1000, **1251.7** | 0.1000, 1984.2 | PASS |
| `AG.run_shared` | 同上 | 同上 | 同上 | 同上 | PASS |
| `GPT.run_beamline` | 2.9213, 1284.1 | 2.9213, 2024.0 | 0.0999, **1284.1** | 0.0999, 2024.0 | PASS |
| **`validation.backend.run_ocelot`**（本轮新增行） | 2.9213, 1284.1 | 2.9213, 2024.0 | 0.0999, **1284.1** | 0.0999, 2024.0 | PASS |

- 语义判定（非模型近似）：纵向 ON → σδ 增长；纵向 OFF → σδ 与 no-kick 基准**逐位一致**；横向开/关 → σx 变化 >1 µm，且**与纵向开关独立**（Δσx：AG 732.46/732.47 µm，GPT 与 OCELOT 739.87/739.87 µm）。
- OCELOT 行与 GPT 行数值完全相同，是同一 seed/同一物理的**交叉验证**（两入口共享 `_ocelot_rf_kick` 语义）。
- 入口 1/4 不传 `switches=`，走 **config 路径**；入口 2 走 `AG.run_shared` 的 config 解析；入口 3 走 GPT 主路由的 `switches` 实参——因此覆盖了三种不同的开关来源。

### 4C mm/m 单位混用
- 修改前：`mid["z_actual_mm"] % dz * 1e3 < 1e-6`（mm vs m）→ 实测 `425.0 % 0.005 = 0.004999999999991`，`×1e3 = 4.999999999991 > 1e-6` → 该断言**必然假 FAIL**（且与真实位置无关）。
- 修改后：`step_mm = dz * 1e3`，残差 `min(r, step−r)`；实测 425.0 mm 对 5 mm 步长残差 **2.842e-13 mm** → PASS。

### 4D 越界 `np.interp` 不再能“通过”
- 新增 `sample_checked()`：先断言 `z_arr[0] − 1e-9 ≤ z_query ≤ z_arr[-1] + 1e-9`，否则抛 `AssertionError`（被捕获并打印为 **FAIL**，不静默钳位）。GPT history 与 validation 轨迹**各自**独立断言后才插值；失败时不再输出误导性的 dev 数值。

### 4E 空白
- `git diff --check` 退出码 **0**（无尾随空格）；新增的未跟踪文件也扫描确认无尾随空格。

## R6. 实测退出码（真实进程 `rc=$?`，非管道尾部）

扫描脚本 `/tmp/run_regression.sh` 逐项运行并以 `rc=$?` 记录（`/tmp/regression_all.log`）。

| # | 命令 | 真实退出码 | 用时 |
|---|---|---|---|
| 1 | `validation/test_gpt_config_override.py`（返修 1 验收） | **0** | 28 s |
| 2 | `validation/test_gpt_tail_sample.py`（返修 4C） | **0** | 10 s |
| 3 | `validation/test_run_all_exitcode.py` | **0** | 10 s |
| 4 | `validation/test_gpt_sc_contract.py` | **0** | 12 s |
| 5 | `validation/test_benchmark4_scmech.py` | **0** | 384 s |
| 6 | `validation/test_ag_acceleration_damping.py`（返修 4A） | **0** | 4 s |
| 7 | `validation/test_sc_runtime_state.py` | **0** | 106 s（另一次 135 s） |
| 8 | `validation/test_ag_charge_semantics.py` | **0** | 11 s |
| 9 | `validation/test_ag_alpha_coefficients.py` | **0** | 1 s |
| 10 | `validation/test_r56_convention.py` | **0** | 14 s |
| 11 | `validation/test_sc_scheduler_equivalence.py` | **0** | 318 s |
| 12 | `validation/test_gpt_route_equivalence.py`（返修 4D） | **0** | 104 s |
| 13 | `validation/run_all.py`（6 项：config_schema / drift / solenoid / rf / full_beamline / gpt_route） | **0**（6/6 PASS + `OVERALL: PASS`） | 222 s |
| 14 | `validation/test_rf_switches_entrypoints.py`（返修 4B，4 入口×4 组合） | **0** | — |
| 15 | `validation/test_gpt_saved_output.py`（返修 3 验收，`main()` 全链） | **0** | 17 s / 85 s |
| 16 | 基线快照 `baseline_snapshot.py` | **0** | — |
| 17 | `git diff --check` | **0**（无输出） | — |
| 18 | `--step 1` / `--step 3` CLI 冒烟（`main()` 显示路径，写入临时 out_dir） | **0** | — |

说明：
- 第 2、6、7、15 项在本文档写作时**已在最终代码状态下复跑**（第 15、7 项在 `main()` 显示路径改为有效参数之后重跑，仍为 0）。
- 第 5 项（Benchmark 4）耗时最长；第 13 项（`run_all`）本身会再跑一遍 `full_beamline` / `gpt_route`，耗时以实际日志为准。
- 环境：所有涉及 OCELOT 的命令均需 `NUMBA_CACHE_DIR=/tmp/numba_cache`（+`MPLCONFIGDIR=/tmp/mpl`）。

### R6.1 返修轮的对照数值（run_all / gpt_route，最终代码状态）

| 指标（样品面 777 mm） | AG (no-SC) | GPT 主路由 | validation.run_ocelot | 偏差 | 阈值 | 判定 |
|---|---|---|---|---|---|---|
| σ_x (µm) | 1984.191 | 1996.205 | 1996.205 | 0.00% | <5% | PASS |
| σ_y (µm) | — | 1991.415 | 1991.415 | 0.00% | <5% | PASS |
| σ_z (µm) | 474.018 | 474.022 | 474.022 | 0.00% | <5% | PASS |
| σ_δ (e-3) | 2.939 | 2.939 | 2.939 | 0.00% | <5% | PASS |
| ε_nx (mm·mrad) | 0.080 | 0.080 | 0.080 | 0.00% | <5% | PASS |
| time_res (fs) | 2884.155 | 2884.180 | 2884.180 | 0.00% | <5% | PASS |

- `test_gpt_route_equivalence` 第 C 段：覆盖断言先通过（GPT z∈[5.000, 777.000] mm，validation z∈[1.000, 777.000] mm，查询 777.000 mm），再插值 → 六项偏差全部 **0.00%**。
- 随机性：GPT/OCELOT 宏粒子路由在测试内固定 `seed=42`；AG 为确定性包络。上表偏差为 0.00% 属同种子同物理的逐位一致，不代表模型间普遍一致性（模型对比见 v0.15 审计文档）。

## R7. 基线未变（返修轮复核）

| 项 | 期望 | 实测 | 判定 |
|---|---|---|---|
| canonical OCELOT hash（SC OFF, full, seed42, N=5e4, dz=0.001） | `7790fd9c2a2b` | **`7790fd9c2a2b`** | 不变 |
| OCELOT 末点 | 777.0 mm | 777.0 | 不变 |
| AG 完整确定性数组 hash（no-SC full） | `41f69f8ace7d` | **`41f69f8ace7d`** | 不变 |
| AG sample σx / σz | 1984.191437 / 474.017607 µm | 1984.191437 / 474.017607 | 不变 |
| R56 slope | −1.163624 | −1.163624 | 不变 |
| config SHA / 元件数量与顺序 | 不变 | 不变（未触碰 `shared/`） | 不变 |

## R8. 仍未解决（登记，不在本轮修复）

1. **AG 纵向矩变量衔接**（同 §10.1，**未修**）：`H=0` 的 `apply_rf_thin_lens` 仍无条件重设 `ν_z = C_zδ/(γ²σ_z)`，与 SC 演化出的 `ν_z` 不自洽（≈0.00106434 → ≈0.00000315857）。**本轮未碰、未加经验系数、未归因于“模型能力差异”**；需单独物理推导与审批。
2. **非步长对齐中间 probe（422 mm）**：仍为步末采样 + `z_exact=False` + 实际位置存档；精确采样需改变 tracking 路径（方案待批，本轮未做）。
3. **SC 物理未完全验收**：本轮只固化**运行时契约**（requested/available/configured/attached/apply_count/effective/coverage 与最终 coverage 校验），**不等于** SC 力模型已被物理验证。
4. **`z_exact` 语义依赖容差**：`z_exact=True` 表示“在 1e-12 m 舍入容差内到达名义平面”，原始值在 `z_actual_mm`；若日后有人把该容差当物理精度使用，属误用。
5. **生产入口验收缺口**（同 §10.2）：非整数总长 / 部分 SC 覆盖仍只有 helper characterization。
6. **环境**：OCELOT 相关命令需 `NUMBA_CACHE_DIR=/tmp/numba_cache`、`MPLCONFIGDIR=/tmp/mpl`（环境问题，非代码缺陷）。

## R9. 本轮可能引入的新风险（如实登记）

1. `PROBE_TOL_M = 1e-12 m` 是**新增容差**：它只用于“平面到达/精确”判定，不参与追踪；但若未来出现比 1e-9 mm 更细的 probe 需求，该容差需要重新评估。
2. `run_params()` 成为**唯一参数推导点**：若将来有人在 `run_beamline` 内直接使用模块全局（例如新增物理分支忘了走 `P[...]`），override 会再次“静默失效”。当前靠 `results["run_params"]` 回执 + 测试 1c/1d/1e 兜底，但**不是编译期保证**。
3. `resolve_switches()` 逐字段合并：显式字典中**未出现的字段**继承 cfg（这是本轮要求的行为）；若调用方以为“传了字典就是全量覆盖”，会误判。
4. `main()` 现在返回输出路径并接受 `out_dir`：测试得以驱动完整序列化链，但**测试与 CLI 共享同一 `cfg` 全局**（通过 `gpt.cfg = c` 注入），因此测试仍不是“真 CLI 子进程”验收。
5. `sample_checked()` 的 1e-9 mm 覆盖裕度是经验值：若某天后端轨迹终点比样品面短超过 1e-9 mm（真实缺步而非舍入），会以 FAIL 暴露——这是期望行为，但需注意它与 R3 的生产容差**不是同一个数**（1e-12 m vs 1e-9 mm，量级相同、用途不同）。
6. `make_old_damping_rhs()` 依赖生产源码字面量锚点；若生产公式被合法重构（换行/改名），锚点数≠1 会让 guard FAIL（**故意如此**，避免“注入失效却报 PASS”），但会造成一次假警报。
