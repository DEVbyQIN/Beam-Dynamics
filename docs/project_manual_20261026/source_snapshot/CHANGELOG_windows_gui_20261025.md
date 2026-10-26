# Windows 兼容改造（GUI）：启动器、进程管理、编码与专项测试

- 日期：2026-10-25
- 触发问题：GUI 只能从 macOS 启动；后台 worker 用 POSIX 进程组（`start_new_session` + `killpg`）停止，父进程存活用
  `os.getppid()` 比较，Windows 上分别不存在/不成立；文件读写未显式 UTF-8，中文与空格路径在 cp936 控制台有风险。
- 起因记录：`/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs/windows_support_20261025/`
  （2026-10-25 已定位，当时确认代码未修改）。本轮只做工程修复，不重做物理审计，不跑长 SC 扫描。

## 修改范围

| 文件 | 修改 |
|---|---|
| `gui/platform_compat.py`（新增） | 平台兼容层：`spawn_kwargs` / `request_stop` / `force_stop` / `terminate_tree` / `process_alive` / `parent_alive` / UTF-8 读写 / 原子 JSON 写 / `worker_env` / `configure_stdio` |
| `gui/server.py` | Popen 改用 `compat.spawn_kwargs()`；取消、超时、关闭清理走兼容层；worker 环境用 `compat.worker_env`；`run.log` 改二进制句柄；JSON/YAML 显式 UTF-8；端口占用给中文提示；`job.json` 记录 `worker_pid`（仅诊断，不用旧 PID 杀进程） |
| `gui/worker.py` | 父进程存活改用 `compat.parent_alive`；配置/结果读取与 progress/error 写入走兼容层（UTF-8） |
| `启动界面.bat`（新增） | Windows 启动器：`chcp 65001`、`cd /d "%~dp0"`、优先 `.venv`、`PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`、版本/依赖预检、`--open` 与额外参数透传 |
| `安装环境.bat`（新增） | 创建 `.venv`、升级 pip、按 pin 安装、导入校验；强制 CPython 3.12 |
| `运行GUI测试.bat`（新增） | Windows 上一键跑四个 GUI 测试模块，缓存指向项目内 `.gui_test_cache/` |
| `requirements-gui.txt`（新增） | 与 macOS 验证环境一致的精确 pin（11 个包） |
| `.gitattributes`（新增） | `*.bat` 强制 CRLF、`*.command` 保持 LF |
| `.gitignore` | 增加 `/.gui_test_cache/` |
| `gui/WINDOWS.md`（新增） | Windows 安装/启动/兼容对照/依赖证据/自检/排错/未验证项 |
| `gui/README.md`、`README.md` | 增补 Windows 入口、跨平台进程管理说明、测试命令 |
| `gui/test_platform_compat.py`（新增） | 29 项：启动器静态契约、POSIX 真实子进程、模拟 Windows 停止/超时/父进程探测、UTF-8、中文/空格路径 |
| `gui/test_windows_native.py`（新增） | 6 项：仅在 Windows 实机运行（其余平台 skip） |
| `gui/test_gui_e2e.py`（新增） | 3 项：真实服务进程的短例完成 / 取消 / 关闭清理 |
| `PROJECT_STATUS.md`、`AI_HANDOFF.md` | 记录本轮范围、证据与未验证项 |

物理影响：**无**。未改 AG/OCELOT 物理核心、`shared/` 参数与单位、默认束线 YAML、基线、历史结果；GUI 未产生新的
物理结论，也未新增或改变可信度阈值。

## 验证（2026-10-25，macOS，CPython 3.12.2）

| 检查 | 结果 |
|---|---|
| 改动前基线 `gui.test_gui` | 6/6 通过（0.32 s） |
| 改动后 `gui.test_gui` | 6/6 通过（0.42 s） |
| `gui.test_platform_compat` | 29/29 通过（0.9 s） |
| `gui.test_gui_e2e` | 3/3 通过（27.0 s） |
| `gui.test_windows_native` | 6 项 skip（无 Windows 主机） |

端到端（真实 `run_gui.py` 进程 + 真实 AG worker，数据目录含中文与空格）：

1. 短例（默认束线、N=2000、SC 关）跑到 `complete`；结果接口、日志接口、ZIP 内容可读；进度 `phase` 为 `已完成`（跨进程 UTF-8）。
2. 运行中取消（SC 开、0.5 mm 步长）：状态 `cancelled`，无 `result.json`，结果接口返回 409，worker 进程消失。
3. 运行中 `SIGINT` 关闭服务：服务退出码 0，无遗留 worker，任务在磁盘上标为 `cancelled`（不发布结果）。

专项要点：模拟 Windows 分支确认**不调用** `killpg` / `os.kill` / `os.getppid`；`taskkill` 以 argv 列表调用并带 `/T /F`，
失败时回退 `Popen.kill`；POSIX 仍用进程组 SIGTERM/SIGKILL 且子进程自开会话；JSON 输出为 UTF-8 且无 `\u` 转义；
中文+空格目录下任务文件、YAML 快照、日志均正确；原子写在目标被占用时重试；`.bat` 为 CRLF 且内容纯 ASCII。

## 依赖可安装性（元数据级，非实机）

11 个 pin（numpy/scipy/matplotlib/PyYAML/ocelot-collab/pandas/h5py/numexpr/pyFFTW/numba/llvmlite）均有
CPython 3.12 `win_amd64` 轮子；`ocelot-collab` 26.6.1 为 `py3-none-any` 纯 Python。`pyfftw` 在 ocelot 中是
`try/except` 可选加速（`ocelot/cpbd/sc.py:31-36`、`ocelot/__init__.py:131`）。逐项证据见 `gui/WINDOWS.md` §5。

## 限制与未验证项

- **没有 Windows 实机执行**：Windows 原生测试、Windows 端到端、`.bat` 双击流程均未运行；不宣称 Windows 全部通过。
- OCELOT 路线未在 Windows 运行；numba JIT/缓存、pyfftw 动态链接、`GPT模拟` 中文包名导入未实测。
- 超长路径（>260 字符）、杀毒/受控文件夹策略、OneDrive 同步目录、关闭控制台窗口（非 Ctrl+C）后的清理未实测。
- Windows 端口 `SO_REUSEADDR` 行为差异未实测；仅提供端口占用提示。
- 本轮未 commit / 未 push / 未上传；改动以工作区文件交付。
