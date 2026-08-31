# hermes-toolkit

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

## 1. 项目简介

`hermes-toolkit` 是一个极简的 Python 命令行工具骨架，旨在提供一个清晰、
可扩展的起点，方便快速搭建新的 CLI 项目。它基于 Python 标准库 `argparse`
构建，没有引入任何重型依赖，适合作为学习和小型工具开发的基础模板。

主要特性：

- 零运行时外部依赖（仅标准库）。
- 清晰的 `build_parser` / `main` 分层，便于单元测试。
- 自带中文文档（`docs/usage.md`）与 API 参考（`docs/api.md`）。

## 2. 安装步骤

```bash
# 克隆仓库
git clone https://github.com/your-org/hermes-toolkit.git
cd hermes-toolkit

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate

# 安装依赖与可编辑模式包
pip install -r requirements.txt
pip install -e .
```

> **环境要求**：Python 3.8 或更高版本。

## 3. 快速开始示例

安装完成后，可以通过以下命令验证安装是否成功：

```bash
# 查看版本
hermes-toolkit --version
# 输出：hermes-toolkit 0.1.0

# 问候某人
hermes-toolkit greet --name World
# 输出：Hello, World!
```

也可以直接以模块方式运行：

```bash
python -m src.cli --version
python -m src.cli greet --name "张三"
```

运行测试：

```bash
python -m unittest tests.test_cli -v
# 或
pytest tests/ -v
```

## 4. 贡献指南

我们欢迎任何形式的贡献！请遵循以下流程：

1. **Fork** 本仓库，并基于 `main` 创建特性分支：
   ```bash
   git checkout -b feature/my-awesome-change
   ```
2. 编写代码与测试，确保 `python -m unittest tests.test_cli -v` 全部通过。
3. 遵循 [PEP 8](https://peps.python.org/pep-0008/) 代码风格；建议在提交前
   运行 `ruff` 或 `flake8` 进行静态检查。
4. 在 `docs/` 中补充必要的使用说明与 API 变更。
5. 提交 **Pull Request**，并在描述中说明：
   - 解决的问题（链接到 Issue，如果有）。
   - 主要改动点。
   - 测试覆盖情况。

> 提交信息建议使用 [Conventional Commits](https://www.conventionalcommits.org/)
> 规范，例如 `feat: add new subcommand`。

## 5. Badge 占位符

下方的 Badge 用于展示项目的构建与发布状态，可根据 CI 实际情况替换 URL：

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)

---

## 许可证

本项目基于 [MIT 许可证](./LICENSE) 开源。
