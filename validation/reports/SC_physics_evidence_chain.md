# SC 物理证据链审计（v0.15 task 7）

Date: 2026-08-16 · 目标：为每个 AG SC 公式建立「公式 → 原始论文 → 代码实现行号 → 独立验证」证据链，排除"测试全 PASS 但公式源于 AI 生成"的风险（测试只证明代码符合已规定行为，不证明规定本身正确）。

## 1. Gaussian 模型 — Kelisani et al., PR Applied 20, 034021 (2023)

### 1.1 论文锚点
- 核心方程：6D beam-envelope 方程 `σ_u'' + (γγ'/γ²β²)σ_u' = F_u^e + F_u^s + F_u^ε`，Gaussian bunch 空间电荷场，bunch-charge factor f_b 与总电荷线性相关。
- 外部验证（GPT 审核 2026-08-16 已检索确认）：CERN 文档服务器 / ResearchGate 论文正文存在上述方程与 f_b ∝ Ne 结构。

### 1.2 代码实现（AG/beam_dynamics_6d.py，Gaussian 分支 `_space_charge_forces`）
| 公式元素 | 论文 | 代码行号 | 状态 |
|---|---|---|---|
| f_b = η·Ne·e/(8π√π·ε₀)，η=e/(mc²) | f_b ∝ Ne | :377-379 | ✅ 与 Task 2 修复一致（Ne=Q/e） |
| 主项 Fs_x = f_b·α_x/(β²γ³·σx·σz) | Eq.15 主项 ∝ 1/(β²γ³) | :392 | ✅ |
| O(1/γ) 括号修正 A_x/B_x（含 ν²、θ²、p0² 项） | Eq.15 花括号项 | :395-404 | ⚠️ 需论文全文核对系数（第 2 轮） |
| α 系数表（kx=σx/(γσz) 数值积分插值） | 论文附录 | :77, :366-372 | ⚠️ 需核对积分定义（第 2 轮） |
| Fs_y/Fs_z 对称 | Eq.16/17 | :406-429 | ✅ 结构对称 |

### 1.3 独立验证（计划）
- [ ] 复现论文关键图（envelope + PIC 对比）
- [ ] 极限情形：Ne→0 无 SC；σz≫σx 扁束极限 α 表 vs 解析近似
- [ ] 与 OCELOT PIC 0.5m drift SC 数值对比（v0.15 阶段 5）

## 2. Ellipsoid 模型 — Luiten et al., PRL 93, 094802 (2004)

### 2.1 论文锚点
- 均匀 3D 椭球电子束：内部空间电荷场线性 E_u = (ρ₀/ε₀)·M_u·δu，ρ₀=3Ne/(4πABC)，Mx+My+Mz=1（Eq.3-4）。
- 外部验证：APS 官网可查（GPT 审核已确认）；van Oudheusden 2010 PRL（95 keV/200 fC，RF 反转 SC chirp 压缩）为 UED 同量级应用锚点。

### 2.2 代码实现（AG/beam_dynamics_6d.py，`_ellipsoid_space_charge_forces` + `_ellipsoid_form_factors`）
| 公式元素 | 论文 | 代码行号 | 状态 |
|---|---|---|---|
| E_u = (3Ne·e/(4πε₀·ABC))·M_u·δu | Eq.3 | :513 注释 | ✅ |
| Fs_u = Ne·r_e·M_u/(γ³β²·σu·σv) | 包络方程主项 | :537-543 | ✅ 符号为正（发散）物理正确 |
| 球对称/扁椭球 Mz 解析（oblate/prolate + Taylor） | Eq.4 | :462-479 | ✅ |
| 三轴 Carlson R_D 积分 | 广义椭球 | :491-501 | ✅ Mx+My+Mz=1 归一化校验 |
| σ_u = A_u/√5（RMS↔半轴） | 均匀椭球 RMS 关系 | :447 | ✅ |

### 2.3 独立验证（计划）
- [ ] 极限：球对称（A=B=C）→ Mx=My=Mz=1/3（解析）数值验证
- [ ] 扁盘极限（A≫C）→ Mz→0、Mx→1/2 数值验证
- [ ] 复现 Luiten Fig.（空间电荷主导发射度增长 vs 线性场保持）

## 3. 应用锚点 — van Oudheusden et al., PRL 105, 264801 (2010)

- 95 keV、200 fC、space-charge-dominated UED 束：RF 腔反转 SC 感生速度 chirp → 时间压缩。
- 本项目参数对比：100 keV / 100 fC（可扩展 200 fC 验证）——同量级、同机制（RF 压缩），为整条 beamline 物理（SC + RF + 纵向动力学）提供外部基准。
- 计划：Q=200 fC 参数下跑双后端，与论文压缩因子/时间分辨率量级对照（第 2 轮）。

## 4. 未决项（第 2 轮，需论文全文）
1. Kelisani 括号项 A/B 系数逐项核对（含 (1−p0²) 因子语义：p0=γβ 归一化动量）
2. α 系数表积分定义（s 代换 t/(1−t)）与论文附录逐项对照
3. OCELOT SC（ASTRA 算法）与 AG 的分布假设差异对量级比较的影响评估

## 5. 结论（初稿）
- 两个 SC 模型的**主项结构**（∝Ne、∝1/(β²γ³)、form factors）与论文锚点一致，且有 UED 应用论文（van Oudheusden 2010）同量级支撑。
- **括号修正项与 α 表**需论文全文核对后才能写"fully anchored"。
- 最终判定待：①诊断基线数值（阶段 1-4）；②AG vs OCELOT 量级对比（阶段 5）；③论文全文核对（第 2 轮）。
