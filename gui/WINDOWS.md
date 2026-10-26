# Windows 使用与验证说明（GUI v0.1）

> 结论先行（复核更新 2026-10-26）：**Windows 兼容代码、启动器、专项测试已实现；但本仓库没有 Windows 实机执行。**
> 已执行的验证全部在 macOS 上完成：POSIX 行为回归、Windows 分支的模拟单测、真实服务进程的端到端 GUI 测试。
> Windows 原生用例 `gui/test_windows_native.py` 在 macOS 上自动 skip；依赖的 Windows 可安装性只是 PyPI
> 元数据判断（每个 pin 都有 `cp312 win_amd64` 轮子），**不是安装实测**。

## 1. 环境要求

| 项目 | 要求 | 说明 |
|---|---|---|
| 系统 | Windows 10/11，64 位 | 未在 32 位或 ARM64 上验证 |
| Python | **CPython 3.12 x64**（python.org 安装包） | 安装时勾选 `Add python.exe to PATH` |
| 磁盘 | 约 1.5 GB | venv + 依赖 + matplotlib/numba 缓存 |
| 编译器 | 不需要 | `requirements-gui.txt` 的每个 pin 都有预编译轮子 |

为什么钉 Python 3.12：`requirements-gui.txt` 的版本与 macOS 验证环境（CPython 3.12.2）一致；3.12 是同时满足
`pyFFTW`（requires-python ≥ 3.11）、`ocelot-collab`（requires-python ≥ 3.10）和全部 pin 有 win_amd64 轮子的版本。
Python 3.13 未验证，且部分 pin 没有 cp313 轮子——安装器会直接要求 3.12。

## 2. 安装（一次性）

1. 安装 64 位 CPython 3.12（见上）。
2. 双击项目根目录的 **`安装环境.bat`**：验证 CPython 3.12 x64 → 创建或核对 `.venv` → 升级 pip → 按 pin 安装 → 校验导入。已有环境版本/位数不符会明确失败，不删除或覆盖它。
3. 看到 `core imports OK`（以及 `ocelot imports OK`）即完成；脚本最后会 `pause`，窗口不会一闪而过。

脚本的行为：
- 优先用 `py -3.12`，其次检查 `python` 是否恰好是 3.12；都找不到时报错并给出下载地址，不静默用错版本。
- 只在 `.venv` 不存在时创建；已有 `.venv` 也检查 CPython 3.12 / win-amd64，失败时不安装包。
- `ocelot` 导入失败只给 `[WARN]`：AG 路线仍可用，OCELOT 路线会在任务日志里报错（不伪装成功）。
- 离线/代理环境请先配置 `pip`（`pip config set global.index-url ...` 或 `HTTPS_PROXY`），再运行安装器。

## 3. 启动与关闭

| 操作 | 做法 |
|---|---|
| 启动 | 双击 **`启动界面.bat`**，浏览器会自动打开 `http://127.0.0.1:8765` |
| 换端口 | 命令行运行 `启动界面.bat --port 8766`（其余参数原样透传给 `run_gui.py`） |
| 关闭 | 在窗口按 `Ctrl+C`，或直接关闭窗口 |
| 运行数据 | 默认 `gui_runs/`；`--data-dir "D:\带 空格\目录"` 可改 |

关闭语义（实现约定；macOS 工程检查与 Windows 实机证据分开）：
- `Ctrl+C` → 服务端先取消未完成任务、再停 worker；正在运行的 worker 被杀掉，日志保留，任务标为 `cancelled`，**不发布未完成结果**。
- 直接关闭控制台窗口时，Windows 可能不执行 Python 的 `finally`；worker 使用启动时保留的父进程句柄，按 2 秒间隔检查；发现父进程退出或监控错误即中止。轮询间隔不是退出延迟保证，Windows 实际控制台关闭仍未计时。
- 重启界面后，上次未完成的任务标为 `interrupted`，**不会自动重跑**。

## 4. 兼容实现对照

只有一个模块知道平台差异：`gui/platform_compat.py`。`gui/server.py`、`gui/worker.py` 不再直接调用 POSIX 专有接口
（`gui/test_platform_compat.py::test_posix_only_calls_are_isolated` 把这条约束固化为测试）。

| 关注点 | macOS 原行为（保留） | Windows 处理 | 位置 |
|---|---|---|---|
| 启动器 | `启动界面.command`（zsh） | `启动界面.bat`：禁用延迟展开、`%~dp0` 全引号、`chcp 65001`、优先 `.venv` | 新增 `.bat` |
| 子进程会话 | `start_new_session=True`（setsid） | `CREATE_NEW_PROCESS_GROUP`，不会把控制台 Ctrl+C 二次投递给 worker | `spawn_kwargs()` |
| 停止任务 | `killpg(SIGTERM)` | `Popen.terminate()`（进程句柄） | `request_stop()` |
| 超时/强杀 | `killpg(SIGKILL)` | 检查 `taskkill /PID <pid> /T /F` 的退出码，失败退回原 `Popen.kill()` 句柄 | `force_stop()` |
| 关闭服务清理 | `wait(3)` + `killpg(SIGKILL)` | `terminate_tree(grace=3)`：先句柄停止，未退出则整树强杀 | `terminate_tree()` |
| 父进程存活 | `os.getppid()` 比较 | 显式声明 Win32 ABI；worker 保留一次 `OpenProcess(SYNCHRONIZE)` 句柄，再 `WaitForSingleObject(handle, 0)`；错误显式报错；**不用** `os.kill(pid, 0)`（Windows 上它会杀进程） | `ParentMonitor` / `parent_alive()` |
| 进程存活 | `os.kill(pid, 0)` | 同上句柄探测 | `process_alive()` |
| 文本编码 | 默认 UTF-8 | 全部显式 `encoding='utf-8'`；子进程注入 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8` | `read_text/write_json/worker_env` |
| 运行日志 | 文本模式 | 二进制句柄 `run.log`，子进程 UTF-8 字节原样落盘（无换行/编码转换） | `open_log()` |
| 原子 JSON 写 | `Path.replace` | 保留原子性；Windows 上读句柄占用会短暂 `PermissionError`，写侧重试 5 次 | `write_json()` |
| 中文/空格路径 | 列表参数 | 全部 `subprocess` 都传 argv 列表（无 shell 字符串），`cwd` 为项目根；`%~dp0` 带引号 | 启动器 + `server.py` |

## 5. 依赖与 Windows 可安装性证据（元数据级）

版本取自 macOS 已验证环境（`pip list`，2026-10-25），并写进 `requirements-gui.txt`。下表由 PyPI JSON 元数据核对
（`https://pypi.org/pypi/<包>/<版本>/json`），并用
`python -m pip download --no-deps --only-binary=:all: --platform win_amd64 --python-version 3.12 <包>` 在本机解析确认：

| 包 | pin | CPython 3.12 win_amd64 轮子 | 证据 |
|---|---|---|---|
| numpy | 1.26.4 | ✅ `numpy-1.26.4-cp312-cp312-win_amd64.whl` | PyPI JSON |
| scipy | 1.13.1 | ✅ `scipy-1.13.1-cp312-cp312-win_amd64.whl` | PyPI JSON |
| matplotlib | 3.9.2 | ✅ `matplotlib-3.9.2-cp312-cp312-win_amd64.whl` | PyPI JSON |
| PyYAML | 6.0.1 | ✅ `PyYAML-6.0.1-cp312-cp312-win_amd64.whl` | PyPI JSON |
| ocelot-collab | 26.6.1 | ✅ 纯 Python：`ocelot_collab-26.6.1-py3-none-any.whl`（requires-python ≥ 3.10） | PyPI JSON |
| pandas | 2.2.2 | ✅ `pandas-2.2.2-cp312-cp312-win_amd64.whl` | PyPI JSON |
| h5py | 3.11.0 | ✅ `h5py-3.11.0-cp312-cp312-win_amd64.whl` | PyPI JSON |
| numexpr | 2.8.7 | ✅ `numexpr-2.8.7-cp312-cp312-win_amd64.whl` | PyPI JSON |
| pyFFTW | 0.15.1 | ✅ `pyfftw-0.15.1-cp312-cp312-win_amd64.whl` | PyPI JSON |
| numba | 0.59.1 | ✅ `numba-0.59.1-cp312-cp312-win_amd64.whl` | PyPI JSON |
| llvmlite | 0.42.0 | ✅ `llvmlite-0.42.0-cp312-cp312-win_amd64.whl` | PyPI JSON |

补充说明：
- PyPI 发行名是 `ocelot-collab`，导入名是 `ocelot`（本项目 `GPT模拟/` 用 `import ocelot`）。
- `pyfftw` 是 ocelot 的**可选加速**：`ocelot/cpbd/sc.py:31-36` 用 `try/except` 回退到 `numpy.fft`；
  `ocelot/__init__.py:131` 也只在 `try` 里导入并打印提示。因此缺 pyfftw 不会让 OCELOT 路线无法导入——
  但该版本在 Windows 上有预编译轮子，默认仍安装。
- 这些是「元数据/轮子可用性」判断。**没有** Windows 安装实测，也没跑过 `pip install` 的动态链接检查。

## 6. 测试与自检

双击 **`运行GUI测试.bat`**（自动选择 `.venv` 或系统 Python，并把 numba/matplotlib 缓存指到项目内
`.gui_test_cache/`，避免权限问题），等价命令：

```bat
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set NUMBA_CACHE_DIR=%CD%\.gui_test_cache\numba
set MPLCONFIGDIR=%CD%\.gui_test_cache\mpl
python -m unittest gui.test_gui gui.test_platform_compat gui.test_windows_native gui.test_review_regressions gui.test_gui_e2e -v
```

| 模块 | 内容 | macOS 结果（2026-10-25） |
|---|---|---|
| `gui/test_gui.py` | 原有 GUI 契约（非法输入、配置冻结、子进程失败/超时、重启不重跑） | 6/6 通过 |
| `gui/test_platform_compat.py` | 启动器静态契约、POSIX 真实子进程、模拟 Windows 停止/超时/父进程探测、UTF-8 与中文空格路径 | 29/29 通过 |
| `gui/test_windows_native.py` | 仅 Windows 实机：无 `killpg`、句柄停止、父进程探测、中文路径取消 | macOS 全部 skip（6 项） |
| `gui/test_gui_e2e.py` | 真实服务进程：短例完成、取消运行中任务、关闭服务后无遗留 worker | 通过（macOS） |

## 7. 已知风险与未验证项（重要）

1. **无 Windows 实机执行**（本轮最大限制）。所有 Windows 结论来自代码路径模拟、静态契约和 PyPI 元数据。
2. **OCELOT 路线未在 Windows 上运行过**：numba 首次 JIT/缓存行为、pyfftw 实际链接、`GPT模拟` 中文包名导入均未实机验证。
   本机（macOS）确认了 `import ocelot` 在写入型 `NUMBA_CACHE_DIR` 下可导入；Windows 上由 worker 环境变量指向
   `gui_runs/cache/numba`，但未实测。
3. **超长路径未验证**：项目/数据目录总路径超过 260 字符时 Windows 可能失败（未启用 `\\?\` 前缀）。
4. 杀毒软件、OneDrive 同步目录、受控文件夹访问可能拦截 `.venv` 或 `taskkill`；未实测。
5. 端口被占用时给出中文提示并建议 `--port 8766`，但 Windows 上 `SO_REUSEADDR` 行为与 macOS 不同（未实测）。
6. 直接关闭控制台窗口（而非 `Ctrl+C`）时服务端清理可能不执行；依靠保留句柄的父进程监控中止，2 s 是轮询间隔而非保证，未实机计时。
7. 若在普通 `cmd` 里手工运行 `python run_gui.py` 而不是用启动器，未设置 `PYTHONUTF8=1`，中文可能显示为乱码或报编码错误。

## 8. 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `[ERROR] No working Python 3.10+ was found` | `python` 是 Microsoft Store 别名或未勾选 PATH | 装 python.org 3.12 并勾选 PATH；或直接用 `py -3.12` |
| 安装器提示需要 3.12 | 系统 Python 是 3.11/3.13 | 安装 3.12（pin 的轮子只覆盖 3.12） |
| `[ERROR] Missing packages` | 未装依赖或用了另一个解释器 | 运行 `安装环境.bat`；启动器优先用 `.venv` |
| `ocelot` 导入失败 | 依赖未装全或版本不符 | 看 `安装环境.bat` 输出；AG 路线可先用 |
| `无法监听 127.0.0.1:8765` | 端口被占用/权限策略 | `启动界面.bat --port 8766` |
| 中文乱码 | 控制台代码页不是 65001 | 用 `.bat` 启动；或先 `chcp 65001` 并设 `PYTHONUTF8=1` |
| 关窗口后仍有 python 进程 | 关闭语义见 §3 | 检查任务状态和 PID；确认长期残留时在任务管理器结束该 worker（任务记录里 `worker_pid`） |

## 2026-10-26 独立复核与修复

- `taskkill` 非零退出码曾被当成功，超时后 `wait()` 无界；现检查返回值、回退原进程句柄、限定等待。停止仍无法确认时明确失败并阻断新 worker。
- Win32 句柄声明、访问拒绝/WAIT_FAILED 分类、保留父进程对象已补齐；写 error.json 失败也不能绕过退出。
- 测试不再无条件 patch Windows 不存在的 `killpg/getpgid`；Windows 服务结束测试改用定向 CTRL_BREAK，并在服务端进入正常清理路径。
- 原“short AG”测试实际使用默认777 mm；本次改为明确10 mm，同时新增 OCELOT 短例。停止测试等待正式 AG 积分开始，而不是只看到进程刚启动。
- 本轮 macOS：52项契约/平台/故障/原生选择测试中46通过、6个Windows原生项跳过；另4项真实服务端到端通过（两条10 mm短例、积分中取消、积分中关闭服务）。没有Windows实机结果。
- 原10月25日日志保留历史意义；当前证据和具体边界见 [复核报告](../docs/review_20261026/REVIEW.md)。
