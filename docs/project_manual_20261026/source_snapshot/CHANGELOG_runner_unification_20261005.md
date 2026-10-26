# 正式执行路径合并

日期：2026-10-05。

## 问题与统一行为

AG 和 OCELOT 各自有日常入口与 validation/backend.py 中重复的执行实现。共享配置不保证相同执行语义：AG 耦合默认值 False/True 不同；OCELOT 默认步长5/1 mm不同，验证的5-mm路径停在775 mm，日常路径到777 mm；日常 RF 全关仍记录一次 kick。

本次保留两种物理模型，每种共用一个正式 driver：

```text
AG CLI / backend.run_ag → AG.runner.run_from_config → 既有包络核心
OCELOT CLI / backend.run_ocelot → ued_beamline_v2.run_from_config
                               → builder / run_beamline → OCELOT
```

- 显式参数覆盖 cfg；省略 SC 参数继承 cfg。CLI step1–3 保持 SC OFF。
- AG 默认 coupling=False，与现有圆束日常入口一致；显式 True 及原 SC 模型选项保留。
- OCELOT 默认 dz 继承 output.step_size_m；补足尾步，RF 全关计0。
- RF 实例按索引计数，并记录名义/实际事件位置；非对齐 RF 仍可能较晚执行，未引入新时序算法。
- OCELOT 小数 probe 键不再被整数舍入覆盖；AG 超界插值报错。
- BeamResult 移到 shared，保留旧导入兼容；开关与来源规则集中到 run_contract。
- 解析测试保留独立参考；同模型入口测试改为严格数组一致，新增 runner_contract 并注册到 run_all。

## 物理影响与保护范围

AG/beam_dynamics_6d.py、AG/external_forces.py、AG/beamline_sim.py、OCELOT 库、shared/beamline_config.yaml 和冻结基线保持。本次没有更改既有力/坐标公式、调整物理参数或建立新模型。OCELOT CLI 的 chirp 参考显示去掉了与既有方程不符的多余负号；实际 kick 方程不变。

默认设置统一会改变以前隐含使用不同设置的后端结果。不能将默认变化描述为“所有输出不变”。AG 旧 CLI 与验证终点差约1e-16 m；统一保留旧验证运算顺序，旧 CLI 最大σx/y舍入差9.095e-13 μm。

## 验证结果

- 14组同参数修改前后完整数组逐位一致，包括分节、显式AG耦合True、短SC和原日常OCELOT 5-mm数组。
- AG full/SC OFF/coupling=False/n_points=2000：`41f69f8ace7d` 不变；样品面 σx=1984.191437 μm，σz=474.017607 μm。
- OCELOT full/SC OFF/seed42/N50000/显式dz=0.001：`7790fd9c2a2b` 不变；样品面 σx=1996.205133 μm，σz=474.021793 μm。
- config SHA `23e97edb733b` 前后不变。相同参数 CLI JSON history 与后端全部字段逐位一致。
- 最终 run_all：7/7 PASS，真实退出码0；9个相关专项组均退出0。检查在项目副本中运行，未重写原报告/基线/结果。
- 首次 run_all 螺线管项失败：5-mm采样下焦点附近插值最大偏差2.48% > 原1%。明确保留该解析曲线回归的原1-mm采样后为0.60% < 1%；阈值、种子、N和基线未放宽。默认5-mm行为由独立入口合同检查覆盖。首次失败日志保留。
- 补充定位：5-mm真实节点与1-mm轨迹对应值最大差1.183e-11 μm；5-mm节点对独立4×4参考最大偏差0.605%，而两条插值曲线在400个查询点最大相差2.453%。窄焦点附近的任意位置查询需要更细输出采样，本轮不声称默认5 mm满足这种精度。
- 真实子进程检查：AG CLI和OCELOT step1/2/3/4均退出0；OCELOT每阶段终点777 mm、section/RF/SC元数据正确；SC配置OFF时step3/4 history完全一致，AG CLI复现冻结数组。
- 短SC使用1500宏粒子/33³网格，不作为生产SC收敛证明。原生调度专项保留显式1-mm参考条件。

## 开放问题

AG 纵向状态闭合及 H=0 重设νz保留；OCELOT RF 事件精确对齐尚待设计；SC 网格/步长/粒子数/种子收敛、核心积分失败检测和配置几何校验尚未完成。历史 benchmark / 原型脚本不在本次正式入口合并范围。

详细差异、源码与原始检查见本轮 HTML / JSON / 增量patch / 证据包。所有旧工作均保留，未 commit、push 或自动同步 iCloud。
