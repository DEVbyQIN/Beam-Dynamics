# 项目文档、README 与 Windows 适配复核

日期：2026-10-26。结论：发现了实际工程缺陷与过时说明，已在本地修复；现有物理核心、共享默认配置和科学基线未改。Windows 兼容仍须真实 Windows 验收，不能用本机测试替代。

## 复核对象与版本

- 本地工作区基点 `f9810dab40037ef8bfb5c1cb4cf99baefa9bf9d2`，包含已有未提交工作，未重置或覆盖。
- 实际 GitHub `DEVbyQIN/Beam-Dynamics` main 为 `b4aa241fc8e3ca8e3aad98ecdf6c1e058a56c51f`。本轮开始时核对的 README 和 Windows 相关文件与远端内容一致；不是仅看本地 README。详见 `context.json` 和 `github_README_before.md`。
- 修订后的项目说明为 v1.1；旧 v1 源码 ZIP 保留。本轮没有 commit/push，GitHub 页面尚未包含这些修复。

## 发现与修改

| 优先级 | 问题及触发条件 | 影响 | 已做修改与依据 |
|---|---|---|---|
| P1 | `taskkill` 已执行却返回非零，旧代码仍认定成功 | 不再用原进程句柄兜底，随后无限等待；任务可能一直占用计算资源 | 检查退出码、失败后句柄 kill；强停后有限等待，无法确认退出就暂停队列。`gui/platform_compat.py:81`、`gui/server.py:126`。旧行为受控复现见 `before_repro.json`，新增失败分支测试通过。 |
| P1 | Win32 函数未声明 HANDLE 参数/返回类型；访问或等待失败当作父进程已死 | ABI 不正确，可能误停正常 worker；反复按 PID 打开也无法固定原进程身份 | 显式 Win32 类型，启动时保留父进程句柄；访问/等待错误单独报错。`gui/platform_compat.py:158`。这是 ABI 与错误语义修复，未声称在本机重现了真实 Windows 句柄故障。 |
| P2 | 父进程监视线程写错误文件失败后不能执行退出 | 文件占用/权限故障可能留下无服务端的计算 | `finally` 保证退出尝试；`gui/worker.py:15`，写失败注入测试通过。 |
| P2 | 取消仅发一次停止请求；超时允许 NaN/无穷等输入 | 不响应普通停止的进程拖到总超时；非有限等待可破坏调度 | 取消宽限后强停；超时须为有限正数；停止失败保留句柄并禁止后续并发。真 POSIX 拒绝 SIGTERM 子进程和模拟停止失败均检查。 |
| P2 | Windows 上测试去 patch 不存在的 `killpg/getpgid`，E2E 发送不支持的 SIGINT | 适配代码可能尚未被测试就因测试自身不兼容而失败 | patch 允许缺失属性；Windows 改定向 CTRL_BREAK_EVENT，服务端登记 SIGBREAK 清理。`gui/test_platform_compat.py`、`gui/test_gui_e2e.py`。原生信号行为仍待 Windows。 |
| P2 | 安装器复用任意 `.venv`，没有核实解释器/架构；继承 delayed expansion | 装入不匹配环境；含 `!` 的路径可能被解释；切目录失败后误在别处继续 | 校验新旧环境均为 CPython 3.12 x64，禁延迟展开，引用路径并检查 cd 失败。三个 `.bat` 保持 ASCII/CRLF；未宣称已双击实测。 |
| P2 | “短 AG”测试只减少宏粒子数，实际束线仍长 777 mm；取消只等到 running | AG 计算量没因此变小；取消可能未触及实际积分 | 改真实 10 mm 几何，补 OCELOT 正式短例；取消等待进入 AG 积分再执行。`gui/test_gui_e2e.py:134`。 |
| P2 | README 保留旧 RF beta² 公式/约 −9.78，旧电荷缺陷仍写未修；配置少漂移段 | 用户照文档理解或配置，会与真实代码不一致 | 改共同 RF beta³ 公式，默认 H 约 −17.8374 m⁻¹；Ne=abs(Q)/e；完整示例通过实际几何/配置校验。`README.md`。没有改生产物理公式。 |
| P2 | README 混用 7/11 组与当前 12 组，弱化新旧方法/平台边界 | 历史通过可能被误读成当前全套或 Windows 通过 | 明确当前注册 12 组，历史完整运行日期、O3 有限设置范围、原生 Windows 待验；删除绝对复现和过期全局禁止修改表述。 |
| P2 | v1 PDF 的平台章节只能证明实现存在，未覆盖上述错误路径 | 文档与代码一起遗漏了失效模式 | v1.1 增加 E11 复核证据，更新代码摘录/哈希、平台说明和版本来源；补充 RMS 发射度与几何椭圆面积的区别。 |

## 文档中的物理内容核对到什么程度

复核了 AG 独立纵向状态关系、RF 协方差变换的行列式不变量、OCELOT 漂移二阶展开与文中坐标，以及当前有效薄透镜 RF 系数。保存的独立符号核对残差为零，默认 H=−17.837445429727307 m⁻¹，K=6.238239461556977 m⁻¹（`math_review.json`）。

这支持相关公式与当前实现的一致性，不等于重新推导整篇论文、证明完整 AG 闭合模型或真实腔体。原有 AG 发射度适用限制、OCELOT 有限数值资格、真实设备标定缺口继续保留。本轮没有用调参或放宽阈值使两模型一致。

## 验证与计算账本

- 最终单元/契约测试：52 项中 46 通过、6 项 Windows 原生测试跳过，退出码 0，2.172 s。`unit_tests.log`。
- 最后一次真实 GUI 端到端测试：4 项通过，退出码 0，20.581 s。AG/OCELOT 各一条无 SC、含磁透镜与 RF 的 10 mm 正式调用，结果确到 10 mm，RF 各执行一次；另外两项在 AG 进入积分后取消/关服务，未发布完成结果且确认 worker 退出。`e2e_tests.log`、`e2e/`。
- 先后两轮端到端总计：4 条完整 10 mm 短轨迹、4 次被中断的 SC driver 调用。首次受限环境不能绑定端口，尚未启动测试/driver；换允许本地监听的执行环境后完成。没有新增完整 SC 研究，没有运行全套 `validation/run_all.py`。
- 最后的“停止失败后队列永久暂停直至重启”守门由最终单元测试覆盖；正常路径由第二轮 E2E 覆盖，没有为此再重跑物理轨迹。
- README YAML 通过实际 `validate_config`，样品面 0.777 m；三个 `.bat` 的 ASCII/CRLF 检查通过。代码/文档快照及数学证据另列。

## 仍需做的事

1. 在真实 Windows x64 / CPython 3.12 上从干净目录安装，执行 `运行GUI测试.bat`，确认 6 个原生项不再 skip。保留环境版本、完整日志、退出码。
2. Windows 上实际验证双路线短例、取消/超时/关闭服务和直接关控制台、中文空格及 `!` 路径。mock 无法证明 Win32、控制台、杀毒软件或文件占用的真实行为。
3. 暂不扩展物理模型。GUI 可调参数仍需按现有适用边界解释；若改变电荷、能量、几何并要求定量精度，应另定有限数值检查。
4. 确认要发布后再单独提交/推送；当前本地 origin 指向另一份本机仓库，实际 GitHub 远端身份应在发布时再次核对。

## 官方依据

- [Python ctypes：函数签名和返回类型](https://docs.python.org/3/library/ctypes.html)。未声明返回类型默认 C int，HANDLE 必须明确为指针宽度类型。
- [Microsoft OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess) 和 [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)：进程句柄及不同等待结果。
- [Microsoft taskkill](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill)：进程树与强制终止选项。程序需同时检查实际命令结果。

本报告区分已证实旧行为、静态 ABI 风险、当前测试通过和原生平台未验证。原始前态副本位于 `before/`，便于逐项复核；不把这些有限测试写成“所有漏洞已解决”。
