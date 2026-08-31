# hermes-toolkit

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/your-org/hermes-toolkit/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Issues](https://img.shields.io/github/issues/your-org/hermes-toolkit.svg)](https://github.com/your-org/hermes-toolkit/issues)

## 项目简介

`hermes-toolkit` 是一个轻量、可扩展的 Python 开源工具集，致力于为日常脚本、数据预处理与命令行自动化提供统一的入口与一致的使用体验。它以简洁的模块化结构、清晰的 API 与完善的文档为核心理念，方便开发者快速集成到现有工程中。

主要特性：

- 零配置启动，开箱即用
- 基于标准库 `argparse` 构建的稳定 CLI
- 清晰的模块边界，方便二次开发与扩展
- 内置单元测试示例，便于快速接入 CI

## 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/hermes-toolkit.git
cd hermes-toolkit

# 2. 创建并激活虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 以开发模式安装
pip install -e .
```

安装完成后即可使用 `hermes-toolkit` 命令。

## 快速开始示例

```bash
# 查看版本号
hermes-toolkit --version

# 向指定名称打招呼
hermes-toolkit greet --name "Hermes"

# 不传 --name 时使用默认问候
hermes-toolkit greet
```

预期输出示例：

```
$ hermes-toolkit --version
hermes-toolkit 0.1.0

$ hermes-toolkit greet --name "Hermes"
Hello, Hermes! Welcome to hermes-toolkit.
```

在 Python 代码中也可以直接调用：

```python
from src.cli import build_parser, cmd_greet, cmd_version

parser = build_parser()
args = parser.parse_args(["greet", "--name", "World"])
print(cmd_greet(args))   # -> Hello, World! Welcome to hermes-toolkit.
```

## 贡献指南

我们欢迎任何形式的贡献，包括但不限于：提交 Issue、修复 Bug、补充文档、新增功能。在提交之前，请阅读以下流程：

1. **Fork** 本仓库并创建你的特性分支：`git checkout -b feature/your-feature`
2. **编写代码** 并保证通过现有测试套件：`python -m unittest discover tests`
3. **补充测试** — 任何新功能都必须配套单元测试（`unittest` 框架）。
4. **更新文档** — 修改行为时请同步更新 `docs/usage.md` 或 `docs/api.md`。
5. **提交 Pull Request**，并在 PR 描述中说明改动动机与测试结果。

请遵循以下约定：

- 代码风格遵循 [PEP 8](https://peps.python.org/pep-0008/)，建议配合 `black` 与 `ruff`。
- Commit 信息使用英文，推荐格式：`type(scope): subject`，如 `feat(cli): add --json output flag`。
- 重大变更请先在 Issue 中讨论。

## 许可证

本项目基于 MIT 许可证开源，详见 [LICENSE](LICENSE)。

---

> Badge 占位符说明：上面的 Build / License / Python / Code Style / Issues 均为占位符，请在正式接入 CI、PyPI、GitHub 后替换为真实链接。