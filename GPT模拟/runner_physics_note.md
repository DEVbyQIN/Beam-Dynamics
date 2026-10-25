# OCELOT 正式运行实现：Physics Note

日期：2026-10-05。映射模块：`ued_beamline_v2.py` 的 `run_from_config`、`build_lattice_from_shared`、`run_beamline`、`apply_rf_kick`。CLI 和 validation 共同调用这一实现。

## 1. 目的与参考

集中配置、元件组装、粒子生成、RF 操作、原生 SC 调度和诊断。当前调用已安装 OCELOT 的漂移 SecondTM、磁透镜 TransferMap / Navigator / SpaceCharge；没有改动库源码。2026-10-25实际方法与独立参考见 [传输方法 Physics Note](transport_physics_note.md)。历史“整线SecondTM”的声明在本次核对中被发现不符实际，相关旧数字按原日期解释。

## 2. 坐标、方程和单位

束线位置 s 为 m。OCELOT τ=cΔt 为 m；束内物理坐标 z=-βτ，束头为正。原生 p_oc=ΔE/(cp₀)，报告 δp=Δp/p₀；一阶转换 p_oc≈βδp。

粒子初态 στ=σz/β，p_oc=βδp。粒子总能量输入仍沿用 `(energy_keV+511)*1e-6` GeV；本次保留已有数值基线，未调整常量。

纵向 RF：Δδp=V sin(φ+kz)/(β²Etotal)，p_oc 增量为 βΔδp；V 为 V，Etotal 为 eV，k=2πf/c 为 m⁻¹，φ 为 rad。

横向沿用一次冲量：px→px+Kx，py→py+Ky，K=-ekV/(2γβmₑc²)，单位 m⁻¹。螺线管强度 kₛ=eB/(2p₀)，单位 m⁻¹。

## 3. 假设与边界

RF 腔体本身用 Drift 保留长度，RF 作用是手工操作；不是原生加速 Cavity。参考能量固定；上述 p_oc/δp 适配为一阶近似。粒子非线性 RF 与 AG 线性纵向薄透镜、分布式横向包络力并非完全相同近似。

## 4. 数值实现与统一规则

优先级：显式函数参数 > 传入 cfg。默认步长从 `output.step_size_m` 读取；显式 dz 保留。粒子位置使用 seed，动量使用 seed+1，保持原随机策略。

无 SC 时调用 tracking_step，完成固定整步后补足剩余尾步；有 SC 时只使用 Navigator.get_next_step 原生调度。SC 覆盖由 cathode/sample 的零长 marker 定义；请求启用后，导入、构造、attach、apply 和覆盖失败必须报错。

RF 开关逐字段合并。两种作用均关闭时，不计执行 kick。RF 按实例索引计数；meta 记录实例名、名义和实际执行位置。

**已知限制：RF 仍在“第一个起点不早于入口的追踪步”执行。** 例如入口20 mm、步长7 mm时实际在21 mm执行。本次记录这种偏移，未引入事件对齐或更改 SC/RF 的运算顺序；不能声称所有 RF 都精确发生在入口。

## 5. 输入与输出

section 选择活跃元件类型，未激活的有长度元件保留为 Drift。CLI step1/2/3/4 保持既有含义；step1–3 显式禁用 SC，step4 才允许继承配置。API 的 section 与 SC 是独立控制，可用于单元物理案例。

输出 σz=β std(τ)，σδ=std(p_oc)/β，εnx/y=βγ√(〈x²〉〈px²〉−〈xpx〉²)，沿用原诊断。history 和标准 probes 在正式实现中生成一次，CLI 与验证适配只消费结果。非对齐 probe 使用步末粒子状态，保留 nominal/actual/exact；小数位置不再共用取整后的字典键。

## 6. 验证范围

2026-10-05：full、SC OFF、seed42、N50000、显式 dz=0.001 m 的冻结七行数组保持 `7790fd9c2a2b`。配置默认5 mm时 CLI 保存结果与验证接口逐位一致，终点为777 mm。短束线验证 SC 继承、运行契约与覆盖，不代表 SC 收敛或完整物理验收。

螺线管采样检查（seed42/N50000/无SC）：5-mm实际节点与1-mm轨迹对应值的最大σx差1.183e-11 μm；5-mm节点对独立4×4参考的最大偏差0.605%。但对400个中间位置做线性插值，5-mm与1-mm曲线最大偏差2.453%。因此默认5-mm输出不能自动保证窄焦点附近任意位置的1%精度；该解析曲线回归显式使用原1-mm条件。

## 7. 后续问题

需要单独设计 RF 事件对齐并验证 SC/RF 顺序及冻结案例影响。SC 网格/步长/粒子数收敛和完整 SC+RF 物理验收尚未完成。浮点输出、发射度矩定义、参考能量近似及配置几何合法性也需各自有独立依据。

## 2026-10-21 更新

原文旧RF公式、无相位横向K和已知迟到事件描述被本节更新：当前RF使用 shared/rf_model.py 的有效积分电压、时间相位和参考扣除，横向中心相位K=-H/(2γ²)；不模拟共同加速或真实有限场图。详见 shared/rf_model_physics_note.md。

无SC追踪在RF入口切分跨越步，保留原步长序列的其余部分；有SC时为RF_BODY入口注册原生零长PhysProc边界，使Navigator精确到达入口后、下一段传输前执行手工kick。SC的间隔/覆盖/计数仍由原生Navigator管理。非对齐步长的SC运算顺序改变是必要的事件定位修复，不能要求旧错误路径的冻结数组不变。

所有正式历史/探针使用中心化总体矩（按电荷加权），增加纵向相关/实际chirp/发射度/时宽和实际参考量，history含s=0。原始几何横向发射度探针兼容字段仍保留；共同字段明确为归一化发射度。旧无SC canonical hash因RF物理修复、中心矩与起点输出变化迁移，旧证据保留。
