# API 接口说明

本文档描述 `src/cli.py` 中暴露的所有可被外部调用的对象、函数及其签名、参数与返回值。

## 模块常量

### `PROG_NAME: str = "hermes-toolkit"`

CLI 在 `argparse` 与版本输出中使用的程序名称。

### `DEFAULT_GREET_NAME: str = "World"`

`greet --name` 在用户未显式提供名称时使用的默认名称。

---

## 函数签名

### `cmd_version(_args: argparse.Namespace) -> str`

返回 `hermes-toolkit` 的版本字符串。

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `_args` | `argparse.Namespace` | 由 `build_parser().parse_args()` 解析得到的命名空间。该参数当前未使用，保留是为了与其它 `cmd_*` 处理器保持签名一致。 |

**返回**：`str`，形如 `"hermes-toolkit 0.1.0"`。

---

### `cmd_greet(args: argparse.Namespace) -> str`

根据 `args.name` 构造问候语。

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `args` | `argparse.Namespace` | 解析后的参数对象。需包含 `name: str` 字段；如果为空或仅包含空白字符，将回退为 `DEFAULT_GREET_NAME`。 |

**返回**：`str`，形如 `"Hello, Hermes! Welcome to hermes-toolkit."`。

---

### `build_parser() -> argparse.ArgumentParser`

构造并返回顶层的 `argparse.ArgumentParser` 实例。

**返回**：配置完成的解析器，可直接调用其 `parse_args(argv)` 方法。

**支持的参数**：

- `--version`：`store_true`，触发后打印版本并退出。
- `greet` 子命令：
  - `--name`：字符串类型，默认值为 `DEFAULT_GREET_NAME`。

---

### `main(argv: Optional[Sequence[str]] = None) -> int`

CLI 主调度函数。

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `argv` | `Optional[Sequence[str]]` | 要解析的命令行参数序列。`None` 时使用 `sys.argv`。主要用于单元测试在不污染全局状态的前提下驱动 CLI。 |

**返回**：`int`，进程退出码（成功返回 `0`）。

**行为分支**：

1. `args.version` 为真 → 调用 `cmd_version` 并返回 `0`。
2. `args.command == "greet"` → 调用 `cmd_greet` 并返回 `0`。
3. 其它情况 → 调用 `parser.print_help()` 并返回 `0`。

---

## 顶层入口

`src/cli.py` 在被作为脚本直接执行时会调用 `main()`：

```python
if __name__ == "__main__":
    sys.exit(main())
```

等价于命令行 `hermes-toolkit ...`。

## 在 Python 代码中使用

```python
from src.cli import build_parser, cmd_greet, cmd_version, main

# 1) 以函数方式调用
parser = build_parser()
args = parser.parse_args(["greet", "--name", "World"])
print(cmd_greet(args))

# 2) 以 CLI 方式驱动
rc = main(["--version"])
print("exit code:", rc)
```

## 错误与异常

- `cmd_greet` 与 `cmd_version` 不会主动抛出业务异常；非法输入由 `argparse` 在解析时抛出 `SystemExit`。
- `main` 在正常路径下始终返回整数退出码，不会抛出未捕获异常。