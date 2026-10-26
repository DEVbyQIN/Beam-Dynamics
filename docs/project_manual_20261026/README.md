# UED 项目文档 v1.1（2026-10-26）

先读 `UED项目文档_20261026.pdf`。这是一份当前工作区说明，不是新增物理精度认证；包含本轮 Windows 工程修复。两轮端到端检查共 4 条完整 10 mm 短轨迹和 4 次中断 SC 调用；物理核心、共享默认配置、科学阈值和旧基线未改。旧 v1 ZIP 保留，当前源码快照是修订后的 v1.1。

- `main.tex`、`content.tex`、`appendices.tex`：封面/正文/附录。
- `references.tex`：11 条论文、官方文档和方法学参考，正文有对应引用。
- `appendix_code.tex`、`snippets/`：13 段原文代码，保留原始行号。
- `source_snapshot/`、`source_manifest.json`：数量见 `source_manifest.json`，显式选择的代码、测试、配置和说明文件及 SHA256；不是完整软件发行包。
- `evidence/`、`evidence_manifest.json`：历史证据及 E11 本轮复核副本/摘要与来源；HTML 中部分图片仍在原研究目录，大粒子云没有复制。
- `version.json`：Git 基点、工作区状态和本机关键包版本。
- `pdf_build.json`、`document_qa.json`：PDF 构建和最终检查。

## 重编译

需要 TeX Live/MacTeX（XeLaTeX、latexmk、ctex/Fandol）与 Python 的 `pypdf`。在本目录执行：

```sh
python build_pdf.py
```

脚本先由 XeLaTeX 生成 PDF，再为 Fandol 字体补齐 Adobe-GB1 Unicode 字符映射，改善不同 PDF 阅读器的中文显示、搜索和复制；不改变文字内容、公式或版面。`fonts/Adobe-GB1-UCS2` 保留原许可；DejaVu 等宽字体许可在同目录。普通 `latexmk -xelatex -outdir=build main.tex` 也能编译，但本机 TeX 工具链可能省略中文 ToUnicode 映射，交付应使用构建脚本输出。

只重编译不需要运行 `prepare.py` 或 `make_figures.py`，也不需要 OCELOT。`prepare.py` 会重新抓取当前源码；不要无意覆盖这个归档快照。`make_figures.py` 仅画概念图并读取既有 JSON，没有 driver/ODE/PIC 调用。

Windows 平台工程证据只到 macOS 测试和模拟 Windows 分支；原生 Windows 测试在保存日志中跳过。数值研究的预算、超时和有限适用范围在正文独立说明。

本地基点 f9810dab 与审核到的 GitHub b4aa241 分别记录；本轮修复未提交/推送。报告见 `../review_20261026/REVIEW.md`。工程证据 46 通过、6 Windows 原生跳过，真实 GUI E2E 4 通过。
