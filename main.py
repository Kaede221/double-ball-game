import random

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


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


def main() -> None:
    red_balls, blue_ball = draw_double_ball()
    console.print(render_balls(red_balls, blue_ball))


if __name__ == "__main__":
    main()
