# UED 本地工作台 v0.1

macOS：在项目根目录双击 `启动界面.command`，或运行：

```bash
/opt/anaconda3/bin/python3 run_gui.py --open
```

Windows：先双击 `安装环境.bat` 安装一次依赖（创建 `.venv`），之后双击 `启动界面.bat`。详见 [Windows 使用与验证说明](WINDOWS.md)。

浏览器访问 `http://127.0.0.1:8765`。终端保持运行，Ctrl+C 关闭服务并停止未完成任务。端口被占用时可传 `--port 8766`（Windows 上为 `启动界面.bat --port 8766`）。

## 使用流程

1. 左侧编辑束团初态和数值设置。界面位置、长度、追踪步长用 **mm**，内部配置仍是 **m**；其他单位在字段旁标明。
2. 点击束线中的磁透镜或 RF 展开元件表；编辑入口、长度、磁场、频率、有效积分电压和相位。可添加、删除漂移段、磁透镜和 RF。修改元件后须显式调整相邻漂移及样品面。
3. “检查几何与输入”调用共享几何校验；不会自动移动元件或忽略空隙。导入支持 JSON/YAML；导出为经检查的 JSON。
4. 分别运行 AG、OCELOT，或依次运行两者。一个批次共用一份冻结配置；后台子进程执行，界面可查看进度或停止。
5. 曲线可切换束长、横向束宽、chirp、展宽、三方向发射度、纵向相关矩和时宽；悬停显示各自实际记录位置。SVG/PNG 导出含单位、路线和配置标识。
6. 运行记录可查看历史配置与结果、日志，下载包含配置/共同 JSON/日志的 ZIP。修改工作配置后，旧结果仍明确标为旧结果。

## 数据与调用

- 默认记录在项目 `gui_runs/`，不改 `shared/beamline_config.yaml` 和 `shared/results/`。可用 `--data-dir /absolute/path` 指定位置。
- 每次运行保存 `config.json`、`config.yaml`、配置指纹、时间、退出状态、进度、日志及成功结果。取消、超时、失败不会发布完整成功结果；重启时未完成任务标为中断，不自动重跑。
- AG → `AG.runner.run_from_config`；OCELOT → `GPT模拟.ued_beamline_v2.run_from_config`。保存复用 `shared.output_schema.write_results`。GUI 只编辑、调度和显示，不复制力公式、粒子初态或束线积分循环。
- AG 进度按已完成积分段更新，段内不估算虚假百分比；OCELOT 进度来自实际诊断位置。
- 单任务默认上限 1800 秒，`--timeout` 须为有限正值。取消后 3 秒仍未退出则升级停止；强制停止后等待有上限，无法确认退出时暂停队列并报错，不能启动重叠 worker。两路线顺序执行；工作配置相同的结果才合并展示。
- 依赖沿用项目 Python 环境（NumPy/SciPy/PyYAML/Matplotlib/OCELOT）；界面自身没有额外前端安装或网络依赖。Windows 安装器使用 `requirements-gui.txt` 固定版本；这不是已完成 Windows 环境复现的证明。
- 运行管理跨平台：macOS/Linux 保留进程组（`start_new_session` + `killpg`）；Windows 用进程句柄停止、`taskkill /T /F` 强杀整树、可等待句柄探测父进程，集中在 `gui/platform_compat.py`。worker 保留父进程句柄并按 2 秒轮询；这不是清理延迟上界，Windows 控制台关闭行为仍待实机验收。重启将未完成任务标为中断，不自动重跑。

## 测试

```bash
# macOS / Linux
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest gui.test_gui gui.test_platform_compat gui.test_windows_native gui.test_review_regressions gui.test_gui_e2e -v
```

Windows 用 `运行GUI测试.bat`。`gui/test_windows_native.py` 只在 Windows 实机运行，其他平台自动 skip；端到端测试会启动真实服务进程与 worker（`UED_GUI_E2E=0` 可跳过）。2026-10-26 复核新增 taskkill 失败、句柄/API错误、拒绝停止和超时边界检查；结果及未验证项见 [WINDOWS.md](WINDOWS.md)、[复核记录](../docs/review_20261026/REVIEW.md)。

## 科学边界

完成表示计算与保存成功，不表示自动通过物理验收。AG 高斯闭合与 OCELOT 的传输、SC、固定参考等近似继续保留，见 `PROJECT_STATUS.md`。原默认步长 5 mm 不属于最近 1/0.5 mm 的有限数值检查；GUI 不更改默认值或生成新的可信度阈值。

本地监听 127.0.0.1；不上传配置或结果，不提供远程硬件控制。
