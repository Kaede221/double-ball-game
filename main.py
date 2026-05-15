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
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()

DEFAULT_RECORD_PATH = Path("records.jsonl")

BET_COST = 2  # 每注投注金额（元）

# (红球命中数, 蓝球命中数) -> (等级名, 奖金元)
PRIZE_TABLE: dict[tuple[int, int], tuple[str, int]] = {
    (6, 1): ("一等奖", 5_000_000),
    (6, 0): ("二等奖", 200_000),
    (5, 1): ("三等奖", 3_000),
    (5, 0): ("四等奖", 200),
    (4, 1): ("四等奖", 200),
    (4, 0): ("五等奖", 10),
    (3, 1): ("五等奖", 10),
    (2, 1): ("六等奖", 5),
    (1, 1): ("六等奖", 5),
    (0, 1): ("六等奖", 5),
}


def draw_double_ball() -> tuple[list[int], int]:
    """模拟一次双色球开奖：6 个红球（1-33，不重复，升序）+ 1 个蓝球（1-16）。"""
    red_balls = sorted(random.sample(range(1, 34), 6))
    blue_ball = random.randint(1, 16)
    return red_balls, blue_ball


def _balls_text(
    red_balls: list[int],
    blue_ball: int,
    matched_red: set[int] | None = None,
    blue_matched: bool = False,
) -> Text:
    """把一注球渲染成一行 Text；命中的号码用黄字突出（仍保留红/蓝底色）。"""
    matched_red = matched_red or set()
    text = Text(no_wrap=True)
    for i, n in enumerate(red_balls):
        if i > 0:
            text.append("  ")
        fg = "yellow" if n in matched_red else "white"
        text.append(f" {n:02d} ", style=f"bold {fg} on red")
    text.append("   +   ", style="bold yellow")
    blue_fg = "yellow" if blue_matched else "white"
    text.append(f" {blue_ball:02d} ", style=f"bold {blue_fg} on blue")
    return text


def render_balls(red_balls: list[int], blue_ball: int) -> Panel:
    """把开奖结果渲染成一个漂亮的 Rich Panel。"""
    return Panel(
        Align.center(_balls_text(red_balls, blue_ball)),
        title="[bold gold1]双色球开奖结果[/]",
        subtitle="[dim]红球 1-33 选 6 · 蓝球 1-16 选 1[/]",
        border_style="gold1",
        padding=(1, 2),
    )


def validate_picks(red: list[int], blue: int) -> None:
    """检查用户输入的号码是否合法，不合法抛 ValueError。"""
    if len(red) != 6:
        raise ValueError("红球必须是 6 个")
    if len(set(red)) != 6:
        raise ValueError("红球不能重复")
    if any(not 1 <= n <= 33 for n in red):
        raise ValueError("红球号码必须在 1-33 之间")
    if not 1 <= blue <= 16:
        raise ValueError("蓝球号码必须在 1-16 之间")


def judge_prize(
    user_red: list[int],
    user_blue: int,
    draw_red: list[int],
    draw_blue: int,
) -> tuple[int, int, str, int]:
    """对一注判奖，返回 (红球命中数, 蓝球命中数, 等级名, 奖金元)。未中奖时等级为 '未中奖'，奖金 0。"""
    red_matches = len(set(user_red) & set(draw_red))
    blue_matches = 1 if user_blue == draw_blue else 0
    tier, amount = PRIZE_TABLE.get((red_matches, blue_matches), ("未中奖", 0))
    return red_matches, blue_matches, tier, amount


def render_play_result(
    user_red: list[int],
    user_blue: int,
    draw_red: list[int],
    draw_blue: int,
    red_matches: int,
    blue_matches: int,
    tier: str,
    amount: int,
) -> Panel:
    """渲染选号 + 开奖 + 中奖结果。"""
    matched_red = set(user_red) & set(draw_red)
    blue_matched = bool(blue_matches)

    label_user = Text(" 您的选号 ", style="bold white on grey35")
    label_draw = Text(" 开奖结果 ", style="bold white on grey35")

    user_line = Text.assemble(label_user, "  ", _balls_text(sorted(user_red), user_blue))
    draw_line = Text.assemble(
        label_draw, "  ", _balls_text(draw_red, draw_blue, matched_red, blue_matched)
    )

    net = amount - BET_COST
    if amount == 0:
        verdict_style = "bold dim"
        verdict_text = f"未中奖（投注 {BET_COST} 元，净 -{BET_COST} 元）"
        border = "grey50"
    elif tier in ("一等奖", "二等奖"):
        verdict_style = "bold gold1 on grey15"
        verdict_text = f"🎉 {tier}！奖金 {amount:,} 元（净 {net:+,} 元）"
        border = "gold1"
    else:
        verdict_style = "bold green"
        verdict_text = f"中奖 · {tier} · 奖金 {amount:,} 元（净 {net:+,} 元）"
        border = "green"

    summary = Text.assemble(
        ("命中:  ", "bold"),
        (f"红球 {red_matches}/6", "bold red"),
        ("   ·   ", "dim"),
        (f"蓝球 {blue_matches}/1", "bold blue"),
    )

    body = Group(
        Align.center(user_line),
        Align.center(draw_line),
        Text(""),
        Align.center(summary),
        Text(""),
        Align.center(Text(verdict_text, style=verdict_style)),
    )

    return Panel(
        body,
        title=f"[bold {border}]双色球对奖[/]",
        subtitle=f"[dim]每注投注 {BET_COST} 元 · 命中号码用[yellow]黄字[/]显示[/]",
        border_style=border,
        padding=(1, 2),
    )


def prompt_user_picks() -> tuple[list[int], int]:
    """交互式提示用户输入选号，返回 (红球, 蓝球)。"""
    while True:
        raw = console.input("[bold red]请输入 6 个红球号码（1-33，空格分隔）：[/] ")
        try:
            red = sorted(int(x) for x in raw.split())
            validate_picks(red, 1)  # 用占位 blue 先校验红球
            break
        except ValueError as e:
            console.print(f"[red]✗ {e}[/]")

    while True:
        raw = console.input("[bold blue]请输入 1 个蓝球号码（1-16）：[/] ")
        try:
            blue = int(raw.strip())
            validate_picks(red, blue)
            break
        except ValueError as e:
            console.print(f"[red]✗ {e}[/]")

    return red, blue


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
    show_progress: bool = True,
) -> tuple[Counter[int], Counter[int], int]:
    """读取记录文件，返回 (红球计数, 蓝球计数, 总注数)。

    show_progress=True 时显示 Rich 进度条，按字节数推进，读完自动消失。
    """
    red_counter: Counter[int] = Counter()
    blue_counter: Counter[int] = Counter()
    total = 0
    file_size = path.stat().st_size

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]读取 {task.fields[name]}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[dim]{task.completed:>10,} / {task.total:<10,} bytes[/]"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
        disable=not show_progress or file_size == 0,
    )

    with progress, path.open("rb") as f:
        task_id = progress.add_task("", total=file_size, name=path.name)
        for raw in f:
            progress.advance(task_id, len(raw))
            stripped = raw.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
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

    p_play = sub.add_parser("play", help="选号开奖并计算中奖金额")
    p_play.add_argument(
        "-r", "--red", type=int, nargs=6, metavar="N", help="6 个红球号码 (1-33)"
    )
    p_play.add_argument(
        "-b", "--blue", type=int, metavar="N", help="1 个蓝球号码 (1-16)"
    )
    p_play.add_argument("--random", action="store_true", help="机选号码")

    args = parser.parse_args()

    if args.cmd == "simulate":
        simulate_batch(args.n, args.output, args.delay, append=not args.overwrite)
    elif args.cmd == "stats":
        if not args.input.exists():
            console.print(f"[red]✗[/] 找不到记录文件 [bold]{args.input}[/]，请先运行 simulate")
            return
        red, blue, total = compute_stats(args.input)
        console.print(render_stats(red, blue, total))
    elif args.cmd == "play":
        if args.random:
            user_red, user_blue = draw_double_ball()
            console.print("[dim]已机选号码[/]")
        elif args.red is not None and args.blue is not None:
            user_red, user_blue = sorted(args.red), args.blue
        else:
            user_red, user_blue = prompt_user_picks()
        try:
            validate_picks(user_red, user_blue)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/]")
            return
        draw_red, draw_blue = draw_double_ball()
        red_m, blue_m, tier, amount = judge_prize(user_red, user_blue, draw_red, draw_blue)
        console.print(
            render_play_result(
                user_red, user_blue, draw_red, draw_blue, red_m, blue_m, tier, amount
            )
        )
    else:
        red, blue = draw_double_ball()
        console.print(render_balls(red, blue))


if __name__ == "__main__":
    main()
