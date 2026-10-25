# OCELOT 实际传输方法与局部参考

2026-10-25。对应 `ued_beamline_v2.py::build_lattice_from_shared`、`tracking_method_metadata`、`run_beamline` 和 `validation/test_ocelot_transport.py`。

## 目的、来源与选择

修复字符串 `"SecondTM"` 被全局接口静默退回一阶默认方法的问题。当前正式选择为：**Drift 使用 SecondTM；Solenoid 显式使用 TransferMap**。阴极/样品零长锚点和 RF 保留长度的 Drift body 按 Drift 处理；手工 RF kick 与原生 SC 过程另外执行。

采用类对象和逐元件类型的严格请求；构造后逐项检查活动 `tms`，方法不符立即报错。不得从用于 Twiss 的 `first_order_tms` 推断实际粒子追踪方法。低层调用者自建的 lattice 保持自选方法，元数据标为 `caller_supplied` 并记录实际方法。

依据：
- [官方元件架构与方法请求](https://www.ocelot-collab.com/docs/docu/elements/architecture/)。
- [官方原生坐标](https://www.ocelot-collab.com/docs/docu/OCELOT%20fundamentals/coordinate_system/)。
- [官方漂移](https://www.ocelot-collab.com/docs/docu/elements/drift/)。
- 本机 OCELOT 26.06.1：`SolenoidAtom` 只覆盖一阶 R；二阶 T 继承 `Element.create_second_order_main_params` 的无场表达式，不含磁场 k。该版本的 Solenoid 支持接口不代表二阶磁透镜物理已实现。独立 Astra high 复核报告保存在本轮报告目录。

## 坐标、变量与精确漂移参考

束线距离 s、x、y、τ=cΔt 均为 m。原生横向变量 a=p_x/p0、b=p_y/p0 与 q=ΔE/(p0c) 无量纲；E0 是固定参考总能量，γ=E0/(mc²)，β=sqrt(1-γ⁻²)。横向变量只在近轴/窄展宽时近似几何斜率。

由质量壳关系得到 P_s/p0=w=sqrt(1+2q/β+q²-a²-b²)。无场前进 L 时：

```
x_out = x_in + L*a/w
y_out = y_in + L*b/w
tau_out = tau_in + L*((1/beta+q)/w - 1/beta)
a_out=a_in, b_out=b_in, q_out=q_in
```

这是指定原生坐标下自由粒子的精确参考，不调用 OCELOT 的传输张量。要求正向运动 w>0、真实正能量；任意反向/接近停滞状态不在当前近轴模型范围内。

在 a,b,q 小量的二阶展开：

```
Delta x = L*a*(1-q/beta) + O(3)
Delta y = L*b*(1-q/beta) + O(3)
Delta tau = L*(-q/(beta²*gamma²)
              +(a²+b²)/(2*beta)+3*q²/(2*beta³*gamma²)) + O(3)
```

`SecondTM` 只保留这个展开，不是精确漂移。在固定非零输入下细分步长不能消除其截断误差。以不同输入跨度检查阶数，比只检查固定步长自洽更能辨别近似。

## 硬边界磁透镜的已验收范围

沿用 k=eB/(2p0)，单位 m⁻¹。对参考动量，近轴硬边界横向 Hamiltonian 为 H=((a+ky)²+(b-kx)²)/2；令 X=(x,a,y,b)，有 X'=AX：

```
A = [[0, 1, k, 0], [-k², 0, 0, k],
     [-k, 0, 0, 1], [0, -k, -k², 0]]
```

独立参考为 exp(L*A)，与当前一阶磁透镜矩阵比较。此约定含硬边界透镜的出入口处理，不能用只有均匀 Bz 的无边缘场 RK 轨迹直接替代。

非零 q 时磁刚度不同，x_out 对 x_in*q 的必要二阶系数是 kL sin(2kL)/β；本机 Solenoid SecondTM 为0，说明缺少该色差。其与同长度漂移的 T 完全相同。当前显式一阶方案不模拟这些色差、幅度相关飞行时间或高阶像差，不能称“整线二阶”。

## 调度、输入输出与回归

方法由正式 builder 决定；共享 YAML、元件位置/长度、粒子生成、RF 公式/事件、SC 网格/原生调度及共同诊断均保持原行为。无SC `tracking_step` 与有SC `Navigator.get_next_step` 消费同一活动元件方法。

正式 JSON 增加 `meta.ocelot_version`、`meta.transport_policy`、`meta.transport_limits`，并在 `meta.lattice_sequence` 每个元件记录 `tracking_methods`。`model` 不再硬编码为 SecondTM。省略或以标签代替实际方法的旧输出，不能被倒推为已使用二阶算法。

`validation/test_ocelot_transport.py` 独立检查漂移二阶公式与自由飞行截断阶数、硬边界一阶磁透镜、静默回退故障、CLI/API/validation/保存方法一致性和短SC执行契约。短SC测试不证明其物理精度。

本修复使漂移实际恢复二阶项，原无SC数组会按科学原因改变。旧回归文件保留；新日期基线同时记录实际方法、源/库摘要及原/新端点。不以旧一阶数组要求新方法逐位相同，不放宽任何物理阈值。见 `CHANGELOG_ocelot_transport_20261025.md`。

## 开放项

SC场与kick的独立参考、完整工况数值资格仍待后续；一阶输入/输出动量适配、ppm级质量常数差及实际磁场图未在本任务升级。磁透镜真二阶或含端场的场模型只在具体研究用途需要时再选择。本笔记的局部数学检查不能认证100keV整线的全部物理量。
