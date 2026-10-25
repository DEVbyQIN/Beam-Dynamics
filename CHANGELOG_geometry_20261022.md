# 配置几何校验（2026-10-22）

触发：用户希望自由调整装置配置；两模型原本分别使用显式位置和长度累加，非法配置可能产生不同束线。

- 新增 shared/geometry.py，统一拒绝间隙、重叠/乱序、非法长度/名称/类型、错误 sample 和越界诊断面；只允许 64 ULP 舍入差，不自动修复。
- 接入 YAML 加载、AG/OCELOT 正式 driver、OCELOT 独立 builder 和配置检查；两路线新增 meta.geometry 摘要。
- 新增 8 方法专项，真实 API/CLI 验证改变 RF 位置/长度后的事件与末端，含 SC ON/OFF；各阶段保留磁透镜/RF 占长。
- 旧 SC 零执行故障测试使用了“删掉实体元件但保留远处 sample”的无效几何；改为合法 50 mm 束线，抑制原生调度器交付 PhysProc，保持真实传输，确认失败确实来自 apply_count=0。未放宽原判据。
- README 给出“移动并加长 RF、样品固定”的成套修改示例；定义/边界见 shared/geometry_contract.md。
- 默认无 SC 正式结果：AG/OCELOT 各 15 条历史数组前后逐位保持。生产物理公式、默认 YAML、常量、旧阈值与基线均不改；仅新增执行前失败与输出摘要。
- 验证：run_all 11/11 组、8 个专项脚本、最终 config_schema 均退出 0；真实命令行读取 YAML 的 4 次合法运行退出 0、2 次非法运行按预期退出 1，旧输出保持。
- 完整运行日志、真实退出码与未完成边界以 outputs/geometry_contract_20261022/report.html 为准；首次测试预期写反及旧故障样例失败均保留。

不覆盖：低层手工 lattice 与配置的一致性、设备场图、有限长度 RF 或完整 SC 物理验收。
