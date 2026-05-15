import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

DEFAULT_RECORD_PATH = Path("records.jsonl")


def draw_double_ball() -> tuple[list[int], int]:
    """模拟一次双色球开奖：6 个红球（1-33，不重复，升序）+ 1 个蓝球（1-16）。"""
    red_balls = sorted(random.sample(range(1, 34), 6))
    blue_ball = random.randint(1, 16)
    return red_balls, blue_ball


def render_balls(red_balls: list[int], blue_ball: int) -> Panel:
    """把开奖结果渲染成一个漂亮的 Rich Panel。"""
    text = Text(no_wrap=True)
    for i, n in enumerate(red_balls):
        if i > 0:
            text.append("  ")
        text.append(f" {n:02d} ", style="bold white on red")
    text.append("   +   ", style="bold yellow")
    text.append(f" {blue_ball:02d} ", style="bold white on blue")

    return Panel(
        Align.center(text),
        title="[bold gold1]双色球开奖结果[/]",
        subtitle="[dim]红球 1-33 选 6 · 蓝球 1-16 选 1[/]",
        border_style="gold1",
        padding=(1, 2),
    )


def simulate_batch(
    n: int,
    path: Path = DEFAULT_RECORD_PATH,
    delay: float = 0.02,
    append: bool = True,
) -> None:
    """连续开奖 n 次，实时显示并按 JSONL 写入 path（每行一注）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as f, Live(
        console=console, refresh_per_second=30
    ) as live:
        for i in range(1, n + 1):
            red, blue = draw_double_ball()
            f.write(json.dumps({"red": red, "blue": blue}) + "\n")

            status = Text(
                f"已开奖 {i} / {n}   →   {path}",
                style="dim",
                justify="center",
            )
            live.update(Group(render_balls(red, blue), status))

            if delay > 0:
                time.sleep(delay)
    console.print(f"[green]✓[/] 已{'追加' if append else '写入'} {n} 注到 [bold]{path}[/]")


def compute_stats(
    path: Path = DEFAULT_RECORD_PATH,
) -> tuple[Counter[int], Counter[int], int]:
    """读取记录文件，返回 (红球计数, 蓝球计数, 总注数)。"""
    red_counter: Counter[int] = Counter()
    blue_counter: Counter[int] = Counter()
    total = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            red_counter.update(record["red"])
            blue_counter[record["blue"]] += 1
            total += 1
    return red_counter, blue_counter, total


def _build_freq_table(
    title: str,
    border: str,
    counter: Counter[int],
    total: int,
    number_range: range,
    theoretical: float,
) -> Table:
    table = Table(title=title, border_style=border, header_style=f"bold {border}")
    table.add_column("号码", justify="center")
    table.add_column("次数", justify="right")
    table.add_column("概率", justify="right")
    table.add_column("偏差", justify="right")
    for n in number_range:
        count = counter.get(n, 0)
        prob = count / total if total else 0.0
        diff = prob - theoretical
        diff_style = "green" if diff >= 0 else "red"
        table.add_row(
            f"{n:02d}",
            str(count),
            f"{prob:.2%}",
            f"[{diff_style}]{diff:+.2%}[/]",
        )
    return table


def render_stats(
    red_counter: Counter[int], blue_counter: Counter[int], total: int
) -> Group:
    """把统计结果渲染成并排的两个表格。"""
    red_theory = 6 / 33  # 每注 6 个红球，单个号码理论命中概率
    blue_theory = 1 / 16

    red_table = _build_freq_table(
        "[bold red]红球出现概率[/]", "red", red_counter, total, range(1, 34), red_theory
    )
    blue_table = _build_freq_table(
        "[bold blue]蓝球出现概率[/]", "blue", blue_counter, total, range(1, 17), blue_theory
    )

    header = Text(
        f"共 {total} 注  ·  红球理论概率 {red_theory:.2%}  ·  蓝球理论概率 {blue_theory:.2%}",
        style="bold",
        justify="center",
    )
    return Group(header, Text(""), Columns([red_table, blue_table], equal=True, expand=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="双色球模拟器")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("draw", help="单次开奖")

    p_sim = sub.add_parser("simulate", help="批量开奖并保存到文件")
    p_sim.add_argument("-n", type=int, default=100, help="开奖注数（默认 100）")
    p_sim.add_argument(
        "-o", "--output", type=Path, default=DEFAULT_RECORD_PATH, help="保存路径"
    )
    p_sim.add_argument(
        "--delay", type=float, default=0.02, help="每注之间的延时秒数（默认 0.02）"
    )
    p_sim.add_argument(
        "--overwrite", action="store_true", help="覆盖文件而不是追加"
    )

    p_stat = sub.add_parser("stats", help="统计已保存的记录")
    p_stat.add_argument(
        "-i", "--input", type=Path, default=DEFAULT_RECORD_PATH, help="记录文件路径"
    )

    args = parser.parse_args()

    if args.cmd == "simulate":
        simulate_batch(args.n, args.output, args.delay, append=not args.overwrite)
    elif args.cmd == "stats":
        if not args.input.exists():
            console.print(f"[red]✗[/] 找不到记录文件 [bold]{args.input}[/]，请先运行 simulate")
            return
        red, blue, total = compute_stats(args.input)
        console.print(render_stats(red, blue, total))
    else:
        red, blue = draw_double_ball()
        console.print(render_balls(red, blue))


if __name__ == "__main__":
    main()
