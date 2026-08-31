# 使用说明 (Usage)

本文档介绍如何安装、配置以及排查 `hermes-toolkit` 的常见问题。

## 安装

推荐使用 `pip` 在虚拟环境中安装：

```bash
# 1. 创建并激活虚拟环境（可选，但强烈推荐）
python -m venv .venv
source .venv/bin/activate   # Windows 上使用：.venv\Scripts\activate

# 2. 从源码安装
pip install -e .

# 3. 或者仅安装运行时依赖
pip install -r requirements.txt
```

依赖说明：

- `argparse` 是 Python 标准库的一部分，无需额外安装。
- `pytest>=7.0` 用于运行测试套件（仅开发环境需要）。

## 配置

`hermes-toolkit` 当前不需要任何外部配置文件即可运行。CLI 接受的所有参数
都通过命令行传递，例如：

```bash
hermes-toolkit --version
hermes-toolkit greet --name "张三"
```

如果您希望通过环境变量进行自定义，可以将 `HERMES_TOOLKIT_*` 形式的变量
注入到 shell 环境中，例如：

```bash
export HERMES_TOOLKIT_LANG=zh_CN
```

> **提示**：未来的版本可能会增加 YAML/TOML 配置文件的支持。

## 常见故障排查

### 1. `command not found: hermes-toolkit`

- 确认已经激活虚拟环境。
- 确认已经执行 `pip install -e .`，否则 `console_scripts` 入口不会注册。
- 临时解决方案：直接运行 `python -m src.cli`。

### 2. `ModuleNotFoundError: No module named 'src'`

在项目根目录下运行命令，而不是 `src/` 内部。可以使用：

```bash
cd /path/to/hermes-toolkit
python -m src.cli greet --name World
```

或者设置 `PYTHONPATH`：

```bash
export PYTHONPATH=$(pwd)
```

### 3. `--name` 参数缺失

`greet` 子命令的 `--name` 是必填项。如果省略，会得到如下提示：

```
usage: hermes-toolkit greet [-h] --name NAME
hermes-toolkit greet: error: the following arguments are required: --name
```

请显式传入 `--name`，例如 `hermes-toolkit greet --name World`。

### 4. 中文显示乱码

请确认终端使用 UTF-8 编码：

```bash
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8
```

### 5. 测试无法运行

确保在项目根目录下使用 `unittest` 或 `pytest`：

```bash
python -m unittest tests.test_cli -v
# 或
pytest tests/ -v
```

如果仍有疑问，请在 GitHub Issue 中提交反馈，并附上完整的错误堆栈。
