# 使用说明 (Usage)

本文档介绍如何安装、配置以及常见故障排查。

## 1. 安装

### 1.1 源码安装

```bash
git clone https://github.com/your-org/hermes-toolkit.git
cd hermes-toolkit
pip install -r requirements.txt
pip install -e .
```

### 1.2 环境要求

- Python >= 3.8
- 推荐使用虚拟环境：`python -m venv .venv`

## 2. 配置

hermes-toolkit 默认无需配置即可使用。如需自定义行为，可通过环境变量：

| 变量名 | 含义 | 默认值 |
| ------ | ---- | ------ |
| `HERMES_LOG_LEVEL` | 日志级别（DEBUG/INFO/WARNING/ERROR） | INFO |
| `HERMES_CONFIG_PATH` | 自定义配置文件路径 | ~/.hermes/config.yaml |

## 3. 快速开始

```bash
hermes-toolkit --version
hermes-toolkit greet --name "Alice"
```

## 4. 常见故障排查

| 问题 | 可能原因 | 解决方案 |
| ---- | -------- | -------- |
| `command not found: hermes-toolkit` | 未正确安装 | 重新执行 `pip install -e .` |
| `ModuleNotFoundError: src` | 运行目录不对 | 在项目根目录运行测试，或设置 `PYTHONPATH=.` |
| `argparse: error: the following arguments are required: --name` | 缺少 `--name` | 运行 `hermes-toolkit greet --name <你的名字>` |
| Python 版本过低 | 小于 3.8 | 升级 Python 或使用 pyenv 安装 3.8+ |

如问题仍未解决，请提交 Issue：https://github.com/your-org/hermes-toolkit/issues