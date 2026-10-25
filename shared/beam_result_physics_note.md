# 共享结果与诊断：Physics Note

日期：2026-10-05。映射：`shared/beam_result.py`、`shared/run_contract.py`；旧 `validation/beam_result.py` 仅保留导入兼容。

## 物理定义和单位

容器接收已经计算的诊断数组，不组装束线、不计算力。束线位置 z_mm 为 mm；σx/y/z 为 μm；εnx/y 为 mm·mrad；σδ为 ×10⁻³ 的动量相对偏差；energy_keV 为参考粒子动能。

原时间诊断 σt=σz/(βc)，输出 fs；β由各点参考能量计算。chirp_m 保留原可选字段，单位 m⁻¹。本次没有新增纵向发射度或 chirp 算法。

## 数值和坐标边界

AG 的 probe 沿用线性插值；记录 sampling=linear_interpolation，只有查询位置在真实输出节点上才标 exact。`at` 查询超出轨迹范围时报错，1e-9 mm仅用于浮点端点舍入，不能替代缺失的传播距离。

OCELOT 的正式实现生成步末粒子诊断和 actual/exact 标记；`from_history` 只把它装入共享容器，不重新计算物理量。两种模型的采样方法保留区别，不能把 OCELOT 步末 probe 与 AG 名义位置插值当成同一真实面。

## 运行规则

run_contract 只管理 section、有效开关、文字说明和来源元数据。显式开关逐字段覆盖 cfg；来源 Git 查询在源码所在仓库执行，不受调用者 cwd 影响。配置 hash 描述输入配置，有效 dz/N/SC 等覆盖另见结果 meta，不能仅凭同一 hash 判断实际设置相同。

## 验证和局限

测试核对 CLI JSON history 与后端数组逐位一致，以及超界查询明确失败。原有解析物理测试保持独立。固定种子一致不能证明统计收敛；容器不检查所有核心积分失败、非正定矩或非法方差，这些仍需后续专项验证。

## 2026-10-21：正式共同诊断 v2

两路线 history/probes 统一增加 C_zdelta_m [m]、chirp_per_m [m⁻¹]、eps_nz_mm_mrad（ζ,δp）[mm·mrad]、eps_z_zprime_m（ζ,ζ′）[m]、sigma_t_fs [fs]、energy_keV [keV]、beta_ref/gamma_ref。实际 beam chirp 为中心矩 C/σζ²，不是 RF 输入 H；时宽不是仪器总时间分辨率。OCELOT history 也保存真实初始 s=0 分布。

全部粒子矩减去质心，并按 |宏粒子电荷| 作总体加权；零电荷用等权总体。原横向 emit 未减质心的数值因此有意改变，追踪坐标不因此改变。动量接口仍是近轴、窄展宽的一阶 δp≈p_oc/β；px/py 是归一化动量，在该范围近似几何斜率，不作全阶同一声明。

C、σζ²、σδ² 描述同一协方差，D=σζ²σδ²-C²≥0；εn,p=βγ√D，εs=√D/γ²。AG 使用实际演化状态的 γ；OCELOT 使用正式坐标适配的参考 γ。旧 AG 核心静质量常量与共享511keV近似仍有 ppm 级差异，现显式记录实际 beta_ref/gamma_ref，不在保存层悄悄重新定义参考。

AG 的 off-grid probe 插值二阶矩后重算派生诊断，方法标签为 linear_interpolation_of_covariance；不能独立插值 h/ε 后宣称仍严格满足约束。OCELOT probe 保留实际步末位置。比较器不再取整小数位置，显示 actual/exact/method；不同实际面的行明确禁止作同面偏差解释，查询越界失败。新版绘图增加实际 h、C、纵向 ε 和时宽。

已计算的正式诊断数组经 shared 容器验证后原样保存，避免反复换单位重算丢失位级一致。对于强相关协方差，小 D 对舍入高度敏感；发射度约束按 |ΔD|≤64εmachine(AB+C²) 判断，仅用于浮点表示，不是可放宽的物理误差阈值。有限负方差/非PSD仍失败。

来源信息增加实际主源文件SHA256和关键依赖版本；config SHA不等于实际运行覆盖参数。旧字段保留；schema_version=2。旧只包含七项基础量的结果仍可读取/绘图，但不伪造不存在的纵向诊断。

AG 的 beta_ref/gamma_ref 直接使用实际ODE历史，不从共享511 keV近似静能重新反推。现有AG核心与共享/OCELOT静能常量存在ppm量级差别，本轮明确记录并保留；未进行全项目常量迁移。此差别不能解释百分比至倍数级的SC发射度差异。
