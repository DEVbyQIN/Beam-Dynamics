# 配置几何契约（2026-10-22）

## 目的与依据

两模型读取同一 YAML，但 OCELOT 按列表累加元件长度，AG 通过显式 `z_start` 设置场区和 RF 入口。
若只改一项，两模型可能解释成不同束线。`geometry.py::validate_geometry` 在计算前拒绝这种配置，
不自动补漂移、不排序、不移动元件，也不改变物理模型。

配置中的 `z_start` 实际是沿束线的 s 坐标，单位 m，不是束团内部纵向坐标。
按列表顺序对每个元件检查：

```text
s_cursor = 前面所有元件的 length 之和，起点为 0 m
本元件 z_start ≈ s_cursor
s_end = z_start + length
```

样品必须是唯一的末端零长 sample，整线长度必须为正。
位置/长度为有限非负数；bool、字符串、NaN/Inf 均不接受。
RF/磁透镜长度为正，cathode/sample 长度为零；允许零长 drift。
名称须非空且唯一；仅支持 cathode、sample、drift、solenoid、rf_cavity。
cathode 若存在须为第一个元件、位于原点；SC 模式另由既有运行契约要求覆盖锚点。
`output.z_diagnostics_mm` 是毫米位置列表，每项必须落在整线内。

## 数值边界与输出

位置比较只容纳浮点累加舍入：

```text
|a-b| ≤ 64 × ulp(max(1 m, |a|, |b|))
```

在本项目小于 1 m 的束线上，绝对容差约 1.42e-14 m。
这是明确的工程舍入策略，不是允许物理间隙的设计参数，也不声称对任意数量元件给出严格累加误差界。
测试证明 1e-16 m 的扰动可读入且不被改写，而 1e-10 m 的真实间隙被拒绝。
保留原坐标和原有轨迹采样，因此 AG 末点可能是 776.9999999999999 mm，而非强制改成 777。

非法输入统一抛出 `ValueError("Beamline geometry: ...")`，包含出错元件、间隙/重叠、实际位置和预期位置。
合法配置返回的共同摘要保存在两路线 JSON 的 `meta.geometry`，包括各段起止、RF 入口和样品面。
它是配置摘要，实际执行须另外核对 `meta.rf_events`、`history.z_mm` 和 SC 的 `sc_coverage_*`。

## 调用路径与配置修改

- `shared.params.load_config`：YAML 读入后校验。
- `AG.runner.run_from_config`：接收内存配置后、创建束团/传播前再次校验。
- `GPT模拟.ued_beamline_v2.run_from_config`：接收内存配置后校验。
- OCELOT 独立 `build_lattice_from_shared`：组装前校验，覆盖直接调用 builder 的脚本。
- `validation.config_check`：复用同一规则；`run_all` 的 `config_schema` 组包含几何专项。

修改 RF 长度或位置须同时检查邻段漂移、其后元件/样品位置以及想要采样的诊断面。
保持样品固定、还是保持末段漂移长度，由研究者配置，不由程序猜测。
固定样品的具体示例见根 README「调整元件位置或长度」。
当前 RF 薄透镜在入口作用，腔长只是几何占长；加长腔体不会自动引入有限长度场分布。
关闭 RF 或磁透镜的运行阶段仍保留几何占长。

## 验收范围

`validation/test_geometry_contract.py` 共 8 个测试方法，覆盖：默认几何且不改输入；非法位置/长度/名称；
顺序、样品及诊断面；数值/结构非法输入；舍入边界；各阶段的磁透镜与 RF 几何；
正式 API、CLI 和独立 builder 提前拒绝错误；两模型 API/CLI 在 SC ON/OFF 下的实际 RF 入口与样品面。
实际短案例为 RF 入口 25 mm、腔长 30 mm、样品 67 mm，SC 使用 N=300、33³ 网格；
仅验证事件与覆盖，不据此判断 SC 精度或物理适用范围。

前后默认无 SC 正式计算，两模型各 15 条历史数组逐位相同（包含 chirp、发射度等共同诊断）。
公共集成回归 11/11 组、8 个相关专项脚本及最终 config_schema 定向检查均退出 0。
独立命令行进程另直接读取隔离副本中的 YAML：SC ON/OFF 共 4 次合法运行退出 0；
两条路线的非法配置各退出 1、错误原因明确，且不改写已有结果。
日志、实际输入/保存输出、哈希和最终验收矩阵见本轮 `geometry_contract_20261022` HTML 报告。

低层 `run_beamline(lat, ...)` 仍允许研究脚本传入手工 lattice，不保证它与配置几何相符。
本轮不改变该接口，不等于验收任意旧脚本或有限长度 RF/完整 SC 物理。
