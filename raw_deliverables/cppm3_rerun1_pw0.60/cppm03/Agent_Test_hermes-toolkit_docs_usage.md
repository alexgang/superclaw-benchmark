# 使用说明

本文档面向 `hermes-toolkit` 的中文使用者，涵盖安装、配置、常见故障排查三部分内容。

## 1. 安装

### 1.1 系统要求

- Python 3.8 及以上版本
- 支持的操作系统：Linux、macOS、Windows
- 任意主流终端（PowerShell、bash、zsh 等）

### 1.2 通过源码安装（推荐）

```bash
git clone https://github.com/your-org/hermes-toolkit.git
cd hermes-toolkit
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 1.3 最小依赖安装

如果仅希望使用 CLI 核心功能（不参与开发），可以直接运行 `python -m src.cli`，无需额外依赖：

```bash
python -m src.cli --version
python -m src.cli greet --name "张三"
```

## 2. 配置

`hermes-toolkit` 默认采用零配置策略即可运行。如需自定义，可通过以下方式覆盖默认行为。

### 2.1 环境变量

| 环境变量 | 作用 | 默认值 |
| --- | --- | --- |
| `HERMES_LOG_LEVEL` | 控制日志输出等级（`DEBUG`/`INFO`/`WARNING`/`ERROR`） | `INFO` |
| `HERMES_NO_COLOR` | 设置为 `1` 时禁用 ANSI 颜色输出 | 未设置 |

### 2.2 配置文件（可选）

可在项目根目录放置 `hermes.toml`，示例：

```toml
[greet]
default_name = "World"
template = "Hello, {name}! Welcome to hermes-toolkit."
```

> 当前版本（0.1.0）尚未启用配置文件的加载逻辑，相关功能将在后续小版本中加入。

## 3. 常见故障排查

### 3.1 提示 `command not found: hermes-toolkit`

可能原因：

1. 未执行 `pip install -e .`，仅克隆了源码。解决方案：在项目根目录执行 `pip install -e .`。
2. 多个 Python 环境并存，`pip` 安装到了与默认 `python` 不同的 site-packages。解决方案：使用 `python -m pip install -e .` 并保持 `python` 与 `pip` 一致。
3. Windows 用户未将 `Scripts` 目录加入 PATH。解决方案：直接通过 `python -m src.cli` 调用，或将 `<venv>\Scripts` 加入 PATH。

### 3.2 提示 `ModuleNotFoundError: No module named 'src'`

通常是直接以脚本方式调用了 `cli.py` 而没有把项目根目录加入 `PYTHONPATH`。解决方案：

```bash
# 在项目根目录下运行
PYTHONPATH=. python src/cli.py --version
```

或在 IDE / CI 中将 `hermes-toolkit/` 添加为工作根目录。

### 3.3 `greet` 命令输出乱码

- 终端编码不是 UTF-8：在 Windows CMD 中执行 `chcp 65001`，或在 PowerShell 中执行 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`。
- 命令行参数被错误编码：尽量避免在终端使用 GB18030 字符作为 `--name` 的取值。

### 3.4 单元测试无法发现

确保在项目根目录执行：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

如果出现 `ImportError`，请确认 `src/__init__.py` 存在，并优先采用 3.2 中的 `PYTHONPATH` 解决方案。

### 3.5 需要更多帮助

- 在 GitHub 仓库提交 Issue：<https://github.com/your-org/hermes-toolkit/issues>
- 查看 API 接口说明：[api.md](api.md)
- 阅读项目主页：[README.md](../README.md)