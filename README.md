# double-ball-game

一个用 Python + [Rich](https://github.com/Textualize/rich) 写的命令行双色球模拟器。支持单次开奖、批量模拟（带实时动画）、把开奖记录持久化为 JSONL 文件，以及对历史记录做号码出现频率统计。

## 玩法说明（双色球规则）

- 红球：从 `1-33` 中**不重复**抽 6 个，按升序展示
- 蓝球：从 `1-16` 中独立抽 1 个
- 单个红球号码的理论命中概率 = `6/33 ≈ 18.18%`
- 单个蓝球号码的理论命中概率 = `1/16 = 6.25%`

## 环境要求

- Python `>= 3.14`
- 包管理：[uv](https://github.com/astral-sh/uv)
- 依赖：`rich >= 15.0.0`

## 快速开始

```bash
uv sync                       # 安装依赖
uv run main.py                # 单次开奖
```

## 命令一览

| 命令 | 作用 |
| --- | --- |
| `uv run main.py` | 单次开奖，展示在控制台 |
| `uv run main.py draw` | 同上（显式形式） |
| `uv run main.py simulate -n 1000` | 批量开奖 1000 注，实时动画并追加到 `records.jsonl` |
| `uv run main.py simulate -n 100 --delay 0.05` | 放慢动画，每注间隔 0.05 秒 |
| `uv run main.py simulate -n 100 --overwrite` | 覆盖原文件，而不是追加 |
| `uv run main.py simulate -o my.jsonl -n 500` | 指定输出文件 |
| `uv run main.py stats` | 读取 `records.jsonl`，输出红/蓝球频率统计表 |
| `uv run main.py stats -i my.jsonl` | 指定输入文件 |
| `uv run main.py play` | 交互式输入选号，开奖并计算中奖金额 |
| `uv run main.py play --random` | 机选号码后开奖 |
| `uv run main.py play -r 1 5 12 19 25 31 -b 7` | 直接传号码开奖 |

### `simulate` 参数

- `-n`（默认 `100`）：开奖注数
- `-o, --output`（默认 `records.jsonl`）：保存路径
- `--delay`（默认 `0.02` 秒）：每注之间的延时，`0` 表示尽快跑完
- `--overwrite`：覆盖文件，默认行为是**追加**

### `stats` 参数

- `-i, --input`（默认 `records.jsonl`）：读取的记录文件

读取大文件时会显示一个进度条（按字节数推进，读完自动消失）。

### `play` 参数

- `-r, --red N N N N N N`：6 个红球号码（1-33，不重复）
- `-b, --blue N`：1 个蓝球号码（1-16）
- `--random`：机选号码（忽略 `-r` / `-b`）
- 三种来源都不给时，会交互式提示输入

## 中奖等级（每注投注 2 元）

| 等级 | 命中条件 | 奖金 |
| --- | --- | --- |
| 一等奖 | 6 红 + 1 蓝 | 5,000,000 元 |
| 二等奖 | 6 红 | 200,000 元 |
| 三等奖 | 5 红 + 1 蓝 | 3,000 元 |
| 四等奖 | 5 红 / 4 红 + 1 蓝 | 200 元 |
| 五等奖 | 4 红 / 3 红 + 1 蓝 | 10 元 |
| 六等奖 | 2 红 + 1 蓝 / 1 红 + 1 蓝 / 0 红 + 1 蓝 | 5 元 |

注：现实中一、二等奖是浮动奖金，本模拟器采用固定值便于演示。

## 记录文件格式

每行一注，JSONL 格式：

```json
{"red": [3, 7, 12, 19, 25, 31], "blue": 9}
{"red": [1, 5, 14, 22, 28, 33], "blue": 4}
```

追加模式下不同批次会接连写入，统计时按累计样本一起算。

## 统计输出说明

`stats` 会渲染两张并排的表格：

- **号码**：红球 `01-33`、蓝球 `01-16`
- **次数**：在所有注里出现的总次数
- **概率**：`次数 / 总注数`
- **偏差**：实际概率 - 理论概率；绿色 = 高于理论值，红色 = 低于理论值

样本越大，偏差应该越接近 `0`。

## 项目结构

```
.
├── main.py            # 所有逻辑与 CLI 入口
├── pyproject.toml     # 项目元信息与依赖
├── records.jsonl      # 运行 simulate 后生成的开奖记录（git 忽略）
└── README.md
```

## 代码结构

`main.py` 里把"业务逻辑"和"展示渲染"做了拆分，方便后续扩展：

- `draw_double_ball()` → 纯逻辑，返回 `(red_balls, blue_ball)`
- `validate_picks()` / `judge_prize()` → 纯逻辑，校验号码 / 判奖
- `render_balls()` / `render_play_result()` / `render_stats()` → 渲染层
- `simulate_batch()` → 批量开奖 + `Live` 动画 + 写文件
- `compute_stats()` → 读 JSONL（带 Rich `Progress` 进度条），返回 `Counter`
- `prompt_user_picks()` → 交互式输入用户选号

新增功能时，建议保持"算 / 渲染 / IO"分离的写法。
