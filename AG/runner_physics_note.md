# AG 正式运行实现：Physics Note

更新：2026-10-16（初版 2026-10-05）。映射模块：`AG/runner.py`、`AG/run_shared.py`；诊断容器见 `shared/beam_result_physics_note.md`。

纵向 SC/RF 的最新定义见 [longitudinal_state_physics_note.md](longitudinal_state_physics_note.md)。本文初版合并入口时未改物理；2026-10-16 已按用户选择补齐纵向 Gz，初态以共享束长、sigma_delta 为准，旧纵向固定发射度及旧 AG 冻结值不再适用于新版。

## 1. 目的与现有模型

入口合并把初态创建、外场组装、RF 分段和诊断集中到 `run_from_config`。它调用 `beam_dynamics_6d.py`、`external_forces.py`、`beamline_sim.py`。物理模型参考 Kelisani, Phys. Rev. Applied 19, 054011 (2023)；当前恢复纵向 Gz，横向发射度仍固定。

## 2. 方程、坐标与单位

束线位置记为 s，单位 m；束内纵向坐标 z，单位 m。δ=Δp/p₀ 是无量纲动量偏差，σz 是纵向 RMS 束长。γ、β 来自 `BeamReference`。

物理电子数 Ne=|Q|/e；Q 为 C，宏粒子数量不进入 AG 的 Ne。

纵向 RF 沿用入口薄透镜：δ→δ+Hz，H=eVk cosφ/(β²γmₑc²)，单位 m⁻¹；V 为 V，k=2πf/c 为 m⁻¹，φ 为 rad。实际状态更新全部交给原有 `apply_rf_thin_lens`。

螺线管沿用 kₛ=eB/(2p₀)，B 为 T，p₀ 为 kg·m/s；外场力和空间电荷力仍由原模块计算。

## 3. 近似与独立开关

默认 Gaussian 包络 SC；显式 `sc_model='ellipsoid'` 保留原有选项。SC OFF 通过 Ne=0 生效。纵向 RF 为入口线性薄透镜；横向 RF 是腔体区间上的连续包络力，并非 OCELOT 的一次粒子横向冲量。

当前共享初态为圆束。正式实现默认 `solenoid_coupling=False`，与原 AG 日常入口一致；显式 True 仍可用于原有对照测试。两者不能被当成同一模型设置。

## 4. 数值流程

按 section 选择活跃元件：drift、solenoid、rf、full。关闭某类外场保留总传播长度。按配置顺序到达每个 RF 入口，执行纵向更新，再继续传播。求解器、容差、SC 系数插值均沿用原核心。

`n_points` 是输出采样预算，不是积分器内部固定步长；有 RF 时每段使用 max(200, n_points/(RF数+1)) 的整数采样数。保留旧验证路径终点的浮点运算顺序，使冻结数组逐位一致。真实尾部间隙仍延伸到配置终点。

## 5. 输入与输出

显式函数参数覆盖传入 cfg；省略 SC 参数继承 cfg。配置不被修改。返回共享 `BeamResult`，由 CLI 保存 history/probes，验证层只返回该结果。

输出 σx/y/z 为 μm，σδ 为 ×10⁻³，归一化横向发射度为 mm·mrad。meta 记录 section、SC 状态、有效 RF 开关、耦合设置、RF 入口事件及采样预算，并记录纵向输入优先级、C、ν、θ、chirp、两种坐标下的纵向发射度与约束残差。`rf_kicks_applied` 在 AG 中计数纵向薄透镜调用；横向连续力不计作一次 kick。

## 6. 验证范围

2026-10-05：原 no-SC、full、coupling=False、n_points=2000 的七行数组 SHA1 前12位保持 `41f69f8ace7d`；CLI 保存数组与验证接口逐位一致。原 drift/solenoid/RF 解析检查继续由验证目录承担；短 SC 案例只作实现回归。

2026-10-16：纵向状态物理修正后，新 no-SC AG 数值参考为 `02012b2143f5`，旧值保留用于追溯；输入、坐标及迁移原因见独立纵向 Note 和新基线 JSON。专项及原有回归均通过，阈值不放宽。

## 7. 已知限制

纵向 νz、Czδ、σδ 的状态约束、H=0 恒等性、初态优先级及求解器失败处理已经修复并验证。横向发射度仍固定，Gx/Gy、SC 系数/网格与抽样误差、非高斯分布、高阶纵向运动学仍未全面验证；短 PIC 对照的动量展宽仍有约 11.5% 差异。

## 2026-10-21 更新

正式 SC 补齐 Gx/Gy，分段RF重建保留14列演化历史。两RF开关任一启用即访问对应入口，每实例一次；纵向调制和横向积分透镜均在同一入口执行，不再叠加分布式横向RF力。共同RF模型、坐标、相位、电压和适用域见 shared/rf_model_physics_note.md。新增共同纵向输出、实际状态参考γ和采样约束见 shared/beam_result_physics_note.md。无效纵向发射度配置已删除，旧配置会明确警告。

## 2026-10-22 α 数值修复

正式 F/G 共用直接积分，不再使用截断插值表。`sc_alpha_evaluation`记录包括内部试算阶段的全部系数请求及其数值范围/加阶差；`sc_alpha_table_domain`只作旧表域对照，`legacy_table_no_longer_used=True`、`gaussian_sc_uses_clipped_coefficients=False`。数值域外或积分不满足检查时明确失败。详见alpha_coefficients_physics_note.md；不是新增闭合模型或物理适用域保证。
