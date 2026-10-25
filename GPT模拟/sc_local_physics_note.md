# OCELOT SC局部数学参考与已检查边界

2026-10-25。对应安装版 OCELOT 26.06.1 的 `cpbd/sc.py::{potential,el_field,apply}`、`coord_transform.py`；项目正式调用为 `ued_beamline_v2.py::run_from_config/run_beamline`。本轮未修改SC公式、配置或基线。

## 1. 声明的模型和本轮目的

按[官方SpaceCharge文档](https://www.ocelot-collab.com/docs/docu/physics-processes/sc/)，在束团参考系解自由空间Poisson场，再变换到实验室系施加kick。检查的是该模型的局部数学一致性，不能代替真实设备、导体/镜像电荷、辐射或完整SC工况的物理验收。

安装源码实际链：原生过面坐标→同一实验室时刻坐标→平均动量方向→共同gamma的静止系电荷分布→NGP沉积/自由空间FFT卷积→有限差分/线性插值→场boost→共同速度kick→原生过面坐标。

当前正式输入采用等权宏粒子、正的电子束电荷幅值；电荷符号/权重约定必须连同受力约定解释，不能把正幅值算出的排斥力误作正电荷电子种类。自定义非等权云不在本轮结论范围；原生SC参考方向取未加权平均动量，沉积和项目诊断采用电荷权重。

## 2. 独立场参考与单位

Q用C、位置与RMS宽度sigma用m、E用V/m。球对称高斯由Gauss定律直接得到：

```
E_r(r)=Q/(4*pi*epsilon0*r²) *
       [erf(r/(sqrt(2)*sigma))-sqrt(2/pi)*(r/sigma)*exp(-r²/(2*sigma²))]
```

一般三维高斯从Coulomb核与高斯密度的卷积独立求导：

```
E_i(r)=Q*r_i/(4*pi*epsilon0*sqrt(2*pi)) * Integral(t=0..infinity)
 exp[-sum_j r_j²/(2*(sigma_j²+t))] /
 [(sigma_i²+t)*sqrt(product_j(sigma_j²+t))] dt
```

本轮用独立SciPy积分并以球高斯解析式互证，没有调用AG的alpha系数。积分器误差估计只属于这一数值积分，不是完整算法或实验不确定度上界。

直接Poisson测试将截断±6sigma内的高斯每个单元电荷用CDF差精确积分，再送入原生potential，以错开半格的有限差分场对上述连续参考。球高斯与项目100keV静止系尺寸分别用33³/63³，比较12个轴向点。残差包含单元平均密度近似、网格和有限差分；两层下降不等于完成渐近收敛。

el_field测试采用确定性单元权重与半格对齐点，排除随机抽样干扰；34³/64³只验证该特定几何，不能替默认N50000/63³给出误差保证。另补非圆、非轴向64³三对正负点，检验三分量与反对称性。该源不是均匀宏粒子权重的正式输入，仅作为场求解器的受控电荷分布。

## 3. 原生与同一时刻坐标参考

按[官方坐标](https://www.ocelot-collab.com/docs/docu/OCELOT%20fundamentals/coordinate_system/)，a=p_x/p0、b=p_y/p0、q=DeltaE/(p0c)，tau=cDelta t [m]。E0和mc²用eV，P=p*c用eV。

独立质量壳参考：P0=sqrt(E0²-m²c⁴)，E=E0+qP0，P_s=sqrt(E²-m²c⁴-P0²(a²+b²))。粒子到参考平面的交点是(x,y,0)，对应tau，因此同一时刻的位置为：

```
r_lab=(x,y,0)-(P/E)*tau
P_lab=(P0*a,P0*b,P_s)
```

反向用tau=-r_s*E/P_s、x_cross=r_x-r_s*P_x/P_s、y同形、a=P_x/P0、b=P_y/P0、q=(E-E0)/P0。参考实现用代数有理化避免小能差消减，不调用库坐标函数作参考。

100keV和1MeV的含位置、角度、时间及能差的测试状态，在256*机器epsilon对应的预设尺度内与库相符。零路径kick逐位恒等；规定零场、非零路径只产生舍入尺度内的往返残差。

## 4. kick、beta/gamma与有限步近似

令n为同时刻坐标下平均动量方向，gamma_av由该平均动量得到。对共同速度产生的准静态磁场，cB=beta_av*(n cross E_lab)。以共同速度计算Lorentz力，有：

```
F_eff = E_parallel + E_perpendicular/gamma_av²
Delta(P*c) = (ds/beta_ref)*F_eff
```

P*c单位eV、ds用m、E用V/m。该投影与库在平均动量轴上先乘横向(1-beta_av²)、再旋回全局坐标的实现一致。独立参考直接在全局坐标使用矢量投影。

这保留共同速度近似；每粒子的实际速度可以不同。冻结场诊断中，使用各粒子瞬时速度得到的Lorentz力与共同速度力有可量化差别，不能把实现一致性写成精确逐粒子Lorentz求解。

ds/beta_ref对应固定参考时长的冲量。匀强Ez中，它与精确空间功Ez*ds的有限步能量增益不完全相等；本轮误差随ds减半约缩小4倍，符合O(ds²)局部偏差。这不证明包含场自洽、分段和输运的整线算法具有某个全局收敛阶数。

## 5. 真实短链及结果

只运行1条2mm正式漂移：100keV/100fC、N4000、33³、dz0.5mm、SC开/RF关，发生4次原生SC事件。首步记录实际场和完整前后粒子状态，独立回坐标更新的q最大绝对差约7.30e-16；记录的PIC场只是该更新的输入，不是独立场真值。

直接Poisson场在选定点的最大误差：球高斯33³/63³约3.82%/1.10%；项目静止系尺寸约3.89%/1.15%。确定性el_field 34³/64³约7.82%/1.92%；非圆非轴64³约0.91%–1.85%。仅属这些分布、网格与点，不外推默认粒子云或整线。

45项数学/执行检查通过；网格数值误差单列，未新增全局物理PASS阈值。首步冻结场中，逐粒子速度与共同速度力向量RMS差约0.0534%；这不是发射度或整线误差界。输入输出的一阶delta适配、常量ppm差和自由空间假设仍保留。

## 6. 可复现证据与后续

脚本、独立reference.py、完整analysis.json、首步NPZ、输入、源/库SHA和HTML在：
`/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/ocelot_sc_local_20261025/`。

预算实际使用：potential11/12，apply18/20（规定场14、真实4）；完整束线0、ODE0。没有改生产物理、安装库或旧结果。完整run_all未重跑。

下一项是当前传输方法下、代表研究工况的有限数值资格，主要观测量分别给差异和误差依据。局部数学核对已完成；不为获得模型一致而追加经验项、放宽阈值或升级AG。
