# API 参考 (API Reference)

本文档列出 `src/cli.py` 中暴露的所有函数及其参数说明。

## 模块：`src.cli`

> 导入方式：`from src.cli import build_parser, greet, main`

### `greet(name: str) -> str`

构造一个针对给定姓名的问候语。

| 参数     | 类型  | 描述                              |
| -------- | ----- | --------------------------------- |
| `name`   | `str` | 要问候的对象的名字（不能为空字符串）。 |

**返回值**

- `str`：格式为 `"Hello, <name>!"` 的字符串。

**示例**

```python
>>> from src.cli import greet
>>> greet("World")
'Hello, World!'
```

---

### `build_parser() -> argparse.ArgumentParser`

构造并返回顶层的 `ArgumentParser` 实例。该解析器已注册以下动作：

- `--version`：打印 `hermes-toolkit` 的版本号并退出。
- `greet` 子命令：包含必需的 `--name` 选项。

| 返回值类型                  | 描述                                            |
| --------------------------- | ----------------------------------------------- |
| `argparse.ArgumentParser`   | 已经配置好顶层解析器与 `greet` 子命令。         |

**示例**

```python
>>> from src.cli import build_parser
>>> parser = build_parser()
>>> parser.parse_args(["greet", "--name", "World"])
Namespace(command='greet', name='World')
```

---

### `main(argv: Optional[Sequence[str]] = None) -> int`

CLI 的入口函数。解析参数并执行相应的子命令。

| 参数   | 类型                        | 描述                                                                     |
| ------ | --------------------------- | ------------------------------------------------------------------------ |
| `argv` | `Optional[Sequence[str]]`   | 命令行参数序列；若为 `None` 则使用 `sys.argv[1:]`，便于测试时注入参数。 |

**返回值**

- `int`：进程退出码；成功为 `0`。

**异常**

- `SystemExit`：当 `--version` 或参数错误时由 `argparse` 抛出。

**示例**

```python
>>> from src.cli import main
>>> main(["greet", "--name", "World"])
Hello, World!
0
```

---

### 程序入口（`__main__` 守卫）

`src/cli.py` 末尾包含：

```python
if __name__ == "__main__":
    sys.exit(main())
```

因此可以直接通过以下方式运行：

```bash
python -m src.cli --version
python -m src.cli greet --name World
```

---

## 版本号

包级版本号定义在 `src/__init__.py`：

```python
__version__ = "0.1.0"
```

可通过 `import hermes_toolkit.src; hermes_toolkit.src.__version__` 访问。
