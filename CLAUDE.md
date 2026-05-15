# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 工作流约定（重要）

**任何对代码功能的新增或修改，完成后必须回头检查 [README.md](README.md) 是否需要同步更新。** 重点核对：

- 命令一览表 / 子命令列表
- 参数清单（默认值、新增/移除/改名的 flag）
- 记录文件格式 / 字段
- 统计输出列的含义
- 项目结构、代码结构概述

不要等用户来问。如果改动影响了任何上述内容，主动改 README 并在回复里告知用户改了哪些段落；如果你判断不需要改，也简短说明一句"已确认 README 无需更新"。

## 项目概览

命令行版"双色球"模拟器。所有代码集中在 [main.py](main.py) 一个文件里，通过 argparse 子命令（`draw` / `simulate` / `stats`）调度。用 [Rich](https://github.com/Textualize/rich) 做控制台美化。

## 常用命令

```bash
uv sync                                       # 安装依赖
uv run main.py                                # 单次开奖（默认行为）
uv run main.py simulate -n 1000 --delay 0     # 批量开奖，无延时
uv run main.py simulate -n 100 --delay 0.05   # 慢动画
uv run main.py simulate --overwrite           # 覆盖而不是追加
uv run main.py stats                          # 读 records.jsonl 输出统计
uv run main.py stats -i other.jsonl           # 指定记录文件
```

仓库里**没有**配置 lint / test / format 工具，也没有测试套件。新增功能时不要假设这些存在。

## 架构要点

模块内部刻意按 **"算 / 渲染 / IO"** 分层，新增功能时请保持这个分层：

| 层 | 函数 | 职责 |
| --- | --- | --- |
| 算 | `draw_double_ball()` | 纯逻辑，返回 `(red_balls, blue_ball)`，可单测 |
| 算 | `compute_stats(path)` | 读 JSONL，返回 `(Counter, Counter, total)` |
| 渲染 | `render_balls()` | 把一注结果渲染成 Rich `Panel` |
| 渲染 | `render_stats()` / `_build_freq_table()` | 把统计渲染成两张并排表格 |
| IO + 协调 | `simulate_batch()` | 循环调用 `draw_double_ball`，用 `Live` 实时刷新，同时追加写 JSONL |

`main()` 仅做参数解析和分发，不放业务逻辑。

## 数据格式

记录文件是 **JSONL**（每行一个 JSON 对象）：

```json
{"red": [3, 7, 12, 19, 25, 31], "blue": 9}
```

`simulate` **默认追加**，不是覆盖 —— 这是有意为之，便于跨多次运行累计样本提升统计精度。要重置请加 `--overwrite` 或手动删文件。新增字段时直接加 key 即可，`compute_stats` 只读它需要的键。

## 关键坑：Rich 居中会裁切末尾样式段

如果用 `Text(justify="center")`，行末带背景色的样式段会被裁掉一部分（具体表现：最右边的蓝球看着比红球窄一截）。**正确做法**：用普通 `Text` + 外层 `Align.center(text)` 包一下。`render_balls()` 现在就是这么写的，参考它。新增任何"居中 + 末尾带背景色样式段"的渲染时务必沿用此模式。

## 环境

- Python `>= 3.14`（pyproject 强制）
- 包管理用 **uv**，不要切到 pip / poetry
- 唯一运行时依赖：`rich >= 15.0.0`
