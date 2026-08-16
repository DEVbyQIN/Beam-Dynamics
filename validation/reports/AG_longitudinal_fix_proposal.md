# AG 纵向模型修复方案（v0.15 — 红线区，需批准后实施）

Date: 2026-08-16 · 目标文件：`AG/beam_dynamics_6d.py`（AG 核心，红线）· 状态：**方案待审批，未改代码**

## 1. 问题陈述

AG 纵向束团尺寸演化系统性高估纵向膨胀，随 γ 增大而恶化：

| 场景 | AG | OCELOT（ASTRA 算法） | 论文 Fig.2（目视裁决） |
|---|---|---|---|
| 论文案例（5 MeV/1 nC/10cm drift）σz | 0.923 mm | 0.037 mm | ~0.05 mm ✅ |
| 项目 100 keV drift σz 增长（vs 解析 σδ/γ²） | 1.75%（高估 ~2.5×） | 0.08%（正确） | — |

用户目视确认论文 Fig.2 的 σz 曲线在 z=10cm 处 ~0.05mm → **AG 纵向高估 ~20 倍（5 MeV），OCELOT 正确**。

## 2. 根因（公式级定位）

### 2.1 论文定义（Kelisani 2023，Eq.3/6）
- 包络方程：σ''u + (γγ'/γ²p²)σ'u = Fᵉu + Fˢu + Fᵉᵐu（Eq.3）
- 发射度力：**Fᵉᵐu = (Λu² − σ'u²)/σu（Eq.6）**，Λu = √⟨Δu'²⟩ = 粒子斜率 rms

### 2.2 纵向斜率的相对论因子
粒子相对参考的纵向斜率（推导：δ=Δp/p₀ → Δβ=δβ₀/γ₀² → Δz'=Δβ/β₀=**δ/γ₀²**）：
```
Λz = σδ / γ²        （物理；R56_z = −L/(βγ²) 一致 ✓）
```

### 2.3 AG 实现缺陷（AG/beam_dynamics_6d.py:276-282）
```python
theta_z: eps_geo = self.eps_nz / p0          # p0=γβ → θz≈εnz/(βγσz)≈σδ  ← 缺 1/γ²
```
AG 把 εnz 反推的发散 **θz≈σδ 直接当纵向斜率**，未除 γ²。

### 2.4 数值验证
| 场景 | AG 当前 θz | 物理 Λz=σδ/γ² | 高估倍数 |
|---|---|---|---|
| 100 keV | 1.017e-4 | 6.99e-5 | 1.45（γ²=1.43）✓ 实测 2.5× |
| 5 MeV | 9.09e-3 | 8.60e-5 | 105.8（γ²=116）✓ 实测 ~20× |

（σz 增长 ∝ Λz 线性 → 高估倍数≈γ² 或 √γ² 之间，量级吻合）

## 3. 修复方案（最小改动）

### 3.1 改动点：`theta_z` property（:276-282），仅 εnz 项除以 γ²
```python
@property
def theta_z(self) -> float:
    """Longitudinal RMS divergence (dimensionless slope).

    v0.15 fix: the longitudinal particle slope is Δz' = δ/γ² (relativistic
    kinematics), so the emittance-derived divergence must carry 1/γ²:
        Λz = εnz/(βγ³σz) = σδ/γ²   (uncorrelated case)
    Previously the 1/γ² factor was missing → σz expansion overestimated by
    ~γ² (×1.4 at 100 keV, ×116 at 5 MeV).
    """
    p0 = self.p0
    if p0 < 1e-12 or self.sigma_z < 1e-15:
        return 0.0
    eps_geo = self.eps_nz / p0 / (self.gamma**2)   # ← 修复：εnz/(γ³β)
    return np.sqrt(eps_geo**2 / self.sigma_z**2 + self.nu_z**2)
```
等价写：`eps_geo = self.eps_nz / (p0 * self.gamma**2)`。

### 3.2 改动范围
- **仅 `theta_z`**；`theta_x`/`theta_y` 不动（横向斜率无相对论因子，已验证正确）
- 不触碰：SC 公式（Eq.15-17）、Fs_z、Fs_x/y、α 表、R56/C_zδ 输运（dC_zd=σδ²/γ² 已有正确因子）、RF、solenoid

## 4. 预期影响（必须知晓）

| 量 | 预期变化 |
|---|---|
| AG σz 演化（drift/RF 压缩） | 纵向膨胀显著减小，向 OCELOT 靠拢（论文案例 0.92→~0.04mm） |
| AG σδ 演化 | **不变**（drift 中 dσδ/dz=0 逻辑未动；RF chirp 路径因 σz 变小而 chirp 贡献变化） |
| AG 横向（σx/σy/εnx/ny） | **不变**（theta_x/y 未动；纵向 σz 变小经 Fs 耦合有次级影响） |
| **no-SC 回归** | **会变**：drift 测试 AG σz 从 1.75% → ~0.7%（与解析 σδ/γ² 一致）；full_beamline AG σz 参考值（477.001µm）变小；AG vs OCELOT dev 变化 |
| canonical hash（OCELOT） | **不变**（7790fd9c2a2b，OCELOT 侧零改动） |
| R56 冻结表征 | 不变（独立于 AG） |

**no-SC 数值变化是预期的、物理正确的修正**——不是回归。run_all 中涉及 AG σz 的测试可能需更新参考值（阈值不变）。

## 5. 验收计划

1. 论文案例（5 MeV/1 nC）：AG σz@10cm 应从 0.923mm → ~0.04mm（对照 OCELOT 0.037mm、论文 Fig.2 ~0.05mm）
2. 项目 full beamline（100 keV）：AG σz 样品面 477.001µm → 预期减小；与 OCELOT 474.022 的 dev 应改善
3. 0.5m drift @500 fC：AG σz 增长从 +1088% → ~+430%（对照 OCELOT +428%）
4. 回归：run_all 6 项（AG 相关参考值更新后 PASS）、r56 不变、OCELOT hash 不变、AG n_particles 不变性（test_ag_charge_semantics）保持
5. **重固化 AG baseline**（σx=1984.191 不变、σz=477.001 → 新值）到 CHECKPOINTS/AI_HANDOFF

## 6. 风险

- **AG no-SC 纵向数值全面变化**（预期修正）→ 所有引用 AG σz 的文档/测试参考值需同步更新
- RF 压缩预测变化（σz 变小 → chirp 作用减弱）——需重新评估压缩点/时间分辨率
- theta_z 修复后 F_ε_z 大幅减小 → 纵向 SC（Fs_z）重新成为主导——AG vs OCELOT 纵向对比的"剩余差异"将聚焦到 Fs_z 本身（下一轮核对）
- 不修改测试阈值（红线）

## 7. 审批

红线区改动（AG/beam_dynamics_6d.py），按项目规则需用户批准后实施。批准后流程：实施 → 论文案例验收 → run_all 回归 → 更新参考值/文档 → 独立 commit。
