# API 接口说明

本文档描述 `src/cli.py` 中暴露的所有公开函数及其签名。

## 模块：`src.cli`

### `build_parser() -> argparse.ArgumentParser`

构建并返回顶层参数解析器。

- **参数**：无
- **返回**：`argparse.ArgumentParser`
- **说明**：包含 `--version` 与 `greet` 子命令。

### `greet(name: str) -> str`

根据传入的 `name` 返回问候语。

- **参数**：
  - `name` (`str`)：被问候者的名字。
- **返回**：`str` —— 格式为 `Hello, <name>! Welcome to hermes-toolkit.`

### `main(argv: list[str] | None = None) -> int`

CLI 入口函数。

- **参数**：
  - `argv` (`list[str] | None`)：可选的命令行参数列表；为 `None` 时使用 `sys.argv[1:]`。
- **返回**：`int` —— 进程退出码，0 表示成功。
- **行为**：
  - `greet --name <name>`：打印问候语。
  - 无子命令：打印帮助信息。

## 模块：`src`（`__init__.py`）

### `__version__: str`

当前版本号字符串，遵循语义化版本 (SemVer)。

## 调用示例

```python
from src.cli import greet
print(greet("Alice"))  # Hello, Alice! Welcome to hermes-toolkit.
```