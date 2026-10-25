# UED Beam Dynamics Simulator

> **当前状态与下一步（2026-10-25）**：先看 [项目现状、边界与计算路线图](PROJECT_STATUS.md)。
> 后续计算使用 [计算卡模板](CALCULATION_CARD_TEMPLATE.md)，明确问题、参考、预算和完成条件。
> 旧报告按原日期保留；回归通过范围与模型物理适用范围分别记录。

超快电子衍射（UED）束流动力学模拟器 —— 基于物理的、可互验的双路线束流模拟框架。

- **AG 路线**：三维 RMS 包络与论文 SC Gx/Gy/Gz 演化（高斯闭合，完全确定性）
- **OCELOT 路线**：宏粒子追踪（漂移 SecondTM、磁透镜一阶 TransferMap + 可选 PIC 空间电荷）

两条独立路线共享**唯一参数源** `shared/beamline_config.yaml`（lattice 单一来源），
并用一套统一的验证框架进行交叉校验（AG vs OCELOT）。

每种模型只有一套正式执行实现：日常 CLI 和验证适配调用同一个 driver。
验证层设置案例、比较结果；它不再独立创建初态、组装束线或执行 RF/SC。

---

## 项目目标

以"物理可解释、数值可验证、过程可追溯"为原则，构建一个 UED 束流动力学模拟器：

- 横向：螺线管聚焦、漂移、束团尺寸演化
- 纵向：RF 纵向透镜（chirp）与束团压缩、时间分辨
- 空间电荷：高斯模型（Kelisani 2023）与均匀椭球模型（Luiten 2004）
- 双路线互验：AG（解析包络）与 OCELOT（宏粒子）在相同参数下交叉校验

> 信任一个模拟结果的前提是「物理模型 + 数值实现 + 验证 + 文档」四者一致。
> 一个物理假设清晰、经过验证的简单模型，胜过复杂的黑箱模拟。
> —— 详见 [AGENTS.md](AGENTS.md)（AI 辅助科研编码规范）

---

## 架构总览

```
shared/beamline_config.yaml
        ├─ AG CLI ──────┐
        ├─ run_ag ──────┴→ AG.runner.run_from_config → AG 核心
        │
        ├─ OCELOT CLI ──┐
        └─ run_ocelot ──┴→ ued_beamline_v2.run_from_config
                          → build_lattice_from_shared → run_beamline → OCELOT
```

### 两个独立 backend

| | AG（解析包络） | OCELOT（宏粒子） |
|---|---|---|
| 方法 | 6D 包络 ODE（`solve_ivp` RK45） | 漂移二阶、磁透镜一阶 + 粒子统计；手工 RF kick |
| 模型 | Kelisani 2023 | OCELOT `generate_parray` + `Navigator` |
| 空间电荷 | Gaussian / Ellipsoid 解析模型 | PIC（NGP 沉积 + FFT 泊松求解） |
| 随机性 | 确定性算法，位级固定 | 配置化 seed，同 seed 位级可复现 |
| 发射度 | 三方向由配对 F/G 演化结果计算 | 从宏粒子的中心矩计算 |

比较原则：不要求逐点重合，按「方向 → 趋势 → 量级 → 定量解释」四级推进。

统一运行规则（2026-10-05）：显式参数覆盖 cfg；省略 SC 参数继承 cfg。
AG 默认关闭原有圆束螺线管耦合修正，显式 True 对照保留。
OCELOT 默认 dz 继承 `output.step_size_m`，无 SC 时补足尾步；原 1-mm 冻结回归须显式传 `dz=0.001`。
CLI 的 step1–3 仍关闭 SC，step4 才允许配置启用。RF 事件精确落在入口，实际位置写入 `meta.rf_events`；有SC时入口边界由原生Navigator调度。
详见 [路径合并变更记录](CHANGELOG_runner_unification_20261005.md) 和两条路线的 `runner_physics_note.md`。

当前状态（2026-10-21）：AG 演化三方向相空间面积，SC/RF/分段重建使用同一状态；横向 Gx/Gy 已补齐。无效的 `epsilon_nz_mm_mrad` 从共享 YAML 删除；旧配置读取时警告并忽略，初态由共享束长、`sigma_delta` 与零相关推导。两路线共同 JSON 保存实际 chirp、纵向相关矩、纵向发射度、RMS 时宽及实际参考量。RF 修正时间相位的 β 因子，采用有效积分电压、参考扣除与同一入口薄透镜；详见 [RF Physics Note](shared/rf_model_physics_note.md)、[横向 G Note](AG/transverse_g_physics_note.md) 和 [共同诊断](shared/beam_result_physics_note.md)。这些修复不等于完整有限腔、任意耦合或全 SC 物理验收；历史结果按原日期和公式解释。

---

当前系数计算（2026-10-22）：AG 的 F/G 共用原论文九项 α 的直接积分，已移除正式路径的样条表与边界截断；数值比例范围每轴 `[1e-6,1e6]`，域外明确报错。默认完整 AG 轨迹的所有系数请求均记录范围和误差估计；这不等于高斯闭合或完整 SC 已物理验收。详见 [α 数值 Physics Note](AG/alpha_coefficients_physics_note.md)。无 SC 的15条历史数组与2026-10-21版本逐位相同，旧基线未改。

短SC筛查（2026-10-22）：100 keV、初始85 μm圆束/300 μm束长、50 mm纯漂移，Q=1/10/100 fC、5种子与N/网格/步长有限控制。在本轮经验误差范围内，尺寸支持5%筛查目标；动量展宽仅1 fC支持2%，10/100 fC的AG均值分别低约3.95%/9.83%。纵向发射度分别低约5.80%/69.47%；没有另设纵向发射度阈值。横向发射度总值接近不代表SC增长已被重现。详见[研究定义与数值](validation/sc_scope_study_physics_note.md)及AI_HANDOFF第32节；不能外推完整束线/强压缩，也不代表PIC绝对真值。研究脚本要求显式`--out`，不改生产物理或既有结果。

## 目录结构

```
├── shared/                       # 共享层（单一来源）
│   ├── beamline_config.yaml      # ★ 唯一参数真源（beam + lattice + SC）
│   ├── params.py                 # 参数解析与派生量
│   ├── constants.py              # 物理常数（单一来源）
│   ├── beam_physics.py           # γ/β/p0 派生（BeamReference）
│   ├── ocelot_coords.py          # rparticles 语义访问（禁止裸索引）
│   ├── output_schema.py          # 统一输出 schema
│   ├── beam_result.py            # 正式实现与验证共用的结果容器
│   ├── run_contract.py           # section / 开关 / 来源规则（无力公式）
│   └── compare.py                # 双路线对比工具
│
├── AG/                           # AG 路线（物理修改先推导、验证）
│   ├── beam_dynamics_6d.py       # 6D 包络 ODE（1289 行，核心）
│   ├── external_forces.py        # 螺线管 / RF 力模型
│   ├── beamline_sim.py           # 出图
│   ├── runner.py                 # 唯一正式 AG 执行实现
│   └── run_shared.py             # AG 统一输出适配层（薄适配器）
│
├── GPT模拟/                      # OCELOT 路线（主路由）
│   ├── ued_beamline_v2.py        # 主路由（lattice 单一来源，可 import）
│   └── {drift,solenoid,rf,space_charge}/   # 分节 benchmark
│
├── validation/                   # 验证框架
│   ├── backend.py                # 调用正式 driver 的兼容适配
│   ├── beam_result.py            # 共享容器的导入兼容
│   ├── run_all.py                # 一键回归（11 组，config_schema 含几何专项）
│   ├── test_*.py                 # 分节/整线/路由等价测试
│   ├── CHECKPOINTS.md            # 验证检查点日志
│   ├── reports/                  # 验证报告
│   └── baselines/                # 冻结基线
│
└── scripts/
    └── sync_to_phone.py          # iCloud 同步 + gpt-review 打包
```

---

## 环境要求

- macOS / Linux
- Python 3.10+
- 依赖：`numpy`、`scipy`、`matplotlib`、`PyYAML`、`ocelot`（≥ 26.x）

```bash
pip install numpy scipy matplotlib pyyaml ocelot-collab
```

> 注意：OCELOT 的 `energy` 参数是**总能量**（GeV），即 `(E_keV + 511) * 1e-6`，
> 这是本项目曾经踩过的单位坑（见 `validation/CHECKPOINTS.md`）。

---

## 本地 GUI（v0.1，2026-10-25）

在项目根目录双击 `启动界面.command`，或执行 `/opt/anaconda3/bin/python3 run_gui.py --open`，浏览器访问 `http://127.0.0.1:8765`。

Windows：先双击 `安装环境.bat`（创建 `.venv` 并按 `requirements-gui.txt` 安装依赖），之后双击 `启动界面.bat`。进程停止、超时、关闭清理、UTF-8 与中文/空格路径已按平台分开处理；**本轮未做 Windows 实机验证**，详见 [gui/WINDOWS.md](gui/WINDOWS.md)。

支持参数与元件编辑、共享几何校验、两路线顺序运行、进度/停止、对比曲线及配置/结果/图像导出。运行数据放在 `gui_runs/`，不覆盖共享默认或既有结果。详见 [GUI 使用说明](gui/README.md)。工程验收采用两条10mm短束线、实际SC推进后的停止及失败/超时等检查；没有新增物理模型或物理精度认证。

## 快速开始

### 1. 运行 OCELOT 主路由（GPT 路线）

```bash
# 支持 step 语义：1=drift, 2=+solenoid, 3=+RF, 4=+空间电荷
python3 "GPT模拟/ued_beamline_v2.py" --step 3
```

### 2. 运行 AG 路线（解析包络）

```bash
python3 AG/run_shared.py
```

### 3. 一键回归验证（约 30–40 分钟）

```bash
python3 validation/run_all.py            # 11 组；通过不等于完整 SC 物理验收
python3 validation/test_r56_convention.py # 冻结表征（结果必须逐位不变）
```

两条路线运行后都会写入统一结果文件（`shared/results/`），
可用 `shared/compare.py` 做 AG vs OCELOT 对比。

---

## 调整元件位置或长度

`lattice.elements` 按实际束线顺序列出元件，`z_start`、`length` 的单位是米。
每个元件入口必须等于前面所有长度之和；实际空段也须显式写成 drift。
YAML 加载、两模型正式 driver 和 OCELOT builder 共用
[`validate_geometry`](shared/geometry.py)，在生成初态/追踪前检查连续性、重叠、
顺序、长度、名称、末端 sample 和诊断范围；不自动移动元件或改写配置。
仅容纳浮点累加舍入，不允许真实间隙。可单独预检：

```bash
python3 -c 'from shared.params import load_config; from shared.geometry import validate_geometry; print(validate_geometry(load_config("shared/beamline_config.yaml")))'
```

例如把 RF 入口从 400 mm 移到 410 mm、腔长从 22 mm 改为 30 mm，且样品仍固定在 777 mm，
需要一起修改以下几何项；这只是配置示例，本轮没有修改默认 YAML。

| 元件 | 新 `z_start` / m | 新 `length` / m |
|---|---:|---:|
| drift2 | 0.160 | 0.250 |
| rf1 | 0.410 | 0.030 |
| drift3 | 0.440 | 0.337 |
| sample | 0.777 | 0 |

若希望在 RF 入口/出口取样，可将 `output.z_diagnostics_mm` 中的 400、422 改为 410、440。
诊断面单位是毫米；可以在束线内任意取样，不强制跟随元件边界，也不会自动跟随移动。
只改 RF 长度而未调整邻段时，会报出具体元件、gap（间隙）或 overlap（重叠）、实际与预期位置。

当前两路线均在 **RF 入口施加薄透镜**，RF 长度保留为束线占长；增加长度不会自动变成有限长度腔体场模型。
RF 关闭时仍保留其占长；磁透镜关闭的阶段也保留对应漂移段。不要把元件长度改成零来代替关闭物理作用。
两路线 JSON 的 `meta.geometry` 保存共同几何摘要；实际 RF 位置看 `meta.rf_events`，
实际终点看 `history.z_mm`，SC 覆盖看 `sc_coverage_*`。
手工创建 lattice 后直接调用低层 `run_beamline` 的研究脚本，仍由调用者保证其与配置一致。
详细规则、测试与边界见[配置几何契约](shared/geometry_contract.md)。

---

## 配置文件

所有物理参数的唯一来源是 `shared/beamline_config.yaml`。核心结构：

```yaml
beam:
  energy_keV: 100.0        # 束流动能 [keV]
  charge_fC: 100.0         # 束团电荷 [fC]
  n_particles: 50000       # 宏粒子数 (OCELOT) / Ne (AG)

initial_distribution:
  spot_rms_um: 85.0        # 横向 RMS 尺寸 [μm]
  bunch_length_um: 300.0   # 纵向 RMS 长度 [μm]
  epsilon_n_mm_mrad: 0.08  # 归一化横向发射度 [mm·mrad]
  sigma_delta: 1.0e-4      # 动量偏差 δ_p = Δp/p₀

space_charge:
  enabled: false           # 空间电荷默认关闭
  mesh: [63, 63, 63]       # PIC 网格

lattice:
  elements:                # ★ 唯一几何定义（z_start/length 单位：m）
    - {name: cathode, type: cathode, z_start: 0.000, length: 0.000}
    - {name: drift1,  type: drift,   z_start: 0.000, length: 0.100}
    - {name: solenoid1, type: solenoid, z_start: 0.100, length: 0.060,
       parameters: {B_field_T: 0.05}}
    - {name: rf1, type: rf_cavity, z_start: 0.400, length: 0.022,
       parameters: {frequency_GHz: 2.856, voltage_kV: 30.0, phase_rad: 3.1416}}
    - {name: sample, type: sample, z_start: 0.777, length: 0.000}
```

元件类型：`cathode`（阴极）、`drift`（漂移）、`solenoid`（螺线管）、
`rf_cavity`（RF 腔）、`sample`（样品面/诊断面）。支持多螺线管、多 RF 实例。

> 物理开关 `physics_switches`：`rf_longitudinal_kick`（默认开）、
> `rf_transverse_kick`（默认关，Panofsky-Wenzel 横向踢，公式尚未独立验证）。

---

## 坐标约定（最重要）

项目的一切改动都以坐标约定为前提，详见 [AI_HANDOFF.md](AI_HANDOFF.md) §4。

| 符号 | 含义 | 单位 |
|---|---|---|
| δ_p = Δp/p₀ | 项目标准动量偏差（无量纲） | - |
| p_oc = ΔE/(c·p₀) | OCELOT 原生第六坐标（**不是** Δp/p₀） | - |
| τ = c·t | OCELOT 共动时间坐标 | m |
| z = −β₀·c·Δt | 空间坐标（头为正） | m |

转换规则（仅限 adapter 边界）：

```
进入 OCELOT : p_oc = β₀ · δ_p
离开 OCELOT : δ_p  = p_oc / β₀
```

`BeamResult.sigma_delta_e3` 恒表示 δ_p。禁止在业务代码直接写
`rparticles[5]` 等魔法索引，必须用 `shared/ocelot_coords.py` 的语义访问。

---

## 物理模型

### 螺线管聚焦

聚焦强度：

```
k_s = e·B_z / (2·p₀)
```

本项目参考束 k_s = 22.38 m⁻¹（k_s² = 500.65 m⁻²）。
对于**圆束、无关联**的束团，AG 核心的降阶 Larmor 耦合项会产生虚假 σ_xy 并欠聚焦，
已在适配层关闭（`solenoid_coupling=False`），AG 核心未改，与精确硬边 4×4 传输一致。

### RF 纵向透镜（薄透镜模型）

两后端统一：

```
chirp  H = e·V·k·cosφ / (β²·E₀)      # = −9.78 m⁻¹
kick   δ_p += (V/(β²E_total))·sin(φ + k·z_phys)
```

φ = π 时产生最大线性 chirp（速度聚束）。每次每个 RF 实例在自身 z_start 踢一次。

### 空间电荷（SC）

- **AG**：Gaussian（Kelisani 2023，带误差检查的 α 直接积分）或 Ellipsoid（Luiten 2004，三轴 Carlson 积分）
- **OCELOT**：PIC —— NGP 沉积 → 自由空间 Green 卷积 + FFT 解泊松 → 三线性插值 → 含纵向 E_z

> ⚠️ 当前状态（v0.14.1）：SC 调度已迁移到 OCELOT native `get_next_step()`，
> 但 **SC 数值尚未正式通过 beamline 验证**，不声称 fully validated。
> 已知未修问题：AG 的 SC 强度 ∝ Ne·e（宏粒子数），与物理束团电荷
> `charge_fC` 语义不一致（偏弱 12.5 倍，见 v0.14.1 task 2）。

---

## 验证与回归

一键回归 `validation/run_all.py` 共 7 项；以下物理数值为已有无 SC 参考范围，当前实测以报告为准：

| 测试 | 内容 | 验收 |
|---|---|---|
| config_schema | Level-1 配置一致性 | 能量↔γ↔β↔p₀ 自洽 |
| drift | 漂移传输 | σ_x 0.2%（解析参考） |
| solenoid | 螺线管聚焦（耦合关闭、显式1-mm采样） | 曲线最大偏差 <1% |
| rf | RF 薄透镜 | σ_δ <1%、kick 语义 6e-13 |
| full_beamline | 整线 7 项量化 + 腰位置 | σ_x 0.60%、σ_z 0.63%、腰 Δz=0.4mm |
| gpt_route | 共用正式实现、同参数与种子 | 全部 history 数组逐位一致 |
| runner_contract | CLI 保存结果、默认值、RF开关、SC与尾步 | 同模型数组一致；非法步长/超界查询报错 |

冻结数值（100 keV、no-SC；AG coupling=False/n_points=2000；OCELOT seed42/N50000/显式dz=1 mm）：

```
AG    : σ_x = 1984.191 μm   σ_z = 474.018 μm   （摘要 41f69f8ace7d）
OCELOT: σ_x = 1996.205 μm   σ_z = 474.022 μm   （同 seed 位级可复现）
```

RNG 策略（v0.13）：`seed → x/y/tau`；`seed+1 → px/py/δ_p`（独立序列，
避免 x–px 虚假相关）。

**失败处理**：测试失败、冻结数组/config 摘要变化、元件/事件或有限值异常时，
按 [AGENTS.md](AGENTS.md) 区分本轮非预期回归、原有缺陷和物理定义不足；
暂停相关风险修改，定义明确且已授权的既有缺陷可继续修复。

---

## 版本状态

| 版本 | 内容 | 标签 |
|---|---|---|
| v0.10 | drift/solenoid/RF 分节验证通过，冻结基线 | `v0.10-noSC-longitudinal-validated` |
| v0.11 | lattice 单一来源（清除硬编码几何） | `v0.11-noSC-single-source-lattice` |
| v0.12 | 架构治理（常量单一来源、provenance） | - |
| v0.13 | 结构债务收敛（BeamReference、seed 配置化） | `v0.13-preSC-maintainability` |
| v0.14 | SC 接入审计：定位 P0（tracking_step 不触发 PhysProc）并修复 | - |
| v0.14.1 | SC 调度迁移到 OCELOT native `get_next_step()` | - |

当前阶段：v0.14.1 SC 正式 beamline 验证准备。长期目标：SC 验证完成后
才有资格讨论 AG/OCELOT 的 SC 物理对比、GUI、优化。

---

## 文档导航

| 文档 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | AI 辅助科研编码规范（物理笔记、验证、红线） |
| [AI_HANDOFF.md](AI_HANDOFF.md) | 项目当前状态唯一入口（版本、坐标、结论、任务书） |
| [validation/CHECKPOINTS.md](validation/CHECKPOINTS.md) | 验证检查点详细日志 |
| [validation/reports/](validation/reports/) | 各专题验证报告（SC/R56/架构/数据流） |
| [REFERENCES.md](REFERENCES.md) | 公开文献清单（PDF 不入库） |
| [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md) | 物理模型优化路线图 |
| CHANGELOG_*.md | 各次修改报告（原因→修改→物理影响→验证） |

---

## 红线（禁止修改）

- AG 核心三文件（`beam_dynamics_6d.py` / `external_forces.py` / `beamline_sim.py`）
- OCELOT 安装源码
- `validation/test_r56_convention.py`（冻结表征）
- 测试阈值、baseline 目录、`shared/beamline_config.yaml` 物理参数值
- 随机策略、RF 方程、R56、螺线管方程

---

## 许可证

[MIT](LICENSE) · Copyright (c) 2026 QIN-SMART
