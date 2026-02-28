import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import plotille
import os
import pyfiglet

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

import random

def type_text(text: str, style: str = "bold white", delay: float = 0.01):
    """Simulates typing text to the console, like a game or Claude Code."""
    for char in text:
        console.print(f"[{style}]{char}[/{style}]", end="")
        time.sleep(delay)
    console.print()

def print_welcome():
    clear_screen()
    
    # Generate the banner but print it instantly
    ascii_banner = pyfiglet.figlet_format("SNIFF", font="slant")
    console.print(f"[bold magenta]{ascii_banner}[/bold magenta]")
    console.print("[dim]" + "─" * 80 + "[/dim]\n")
    
    # Animated typing for the welcome text
    type_text("Let's get started.", style="bold white", delay=0.03)
    time.sleep(0.3)
    
    console.print("\n[bold white]Choose the text style that looks best with your terminal[/bold white]")
    console.print("[dim]To change this later, type 'theme' in the REPL[/dim]\n")
    
    import questionary
    theme = questionary.select(
        "",
        choices=[
            "Dark mode ✓",
            "Light mode",
            "Dark mode (colorblind-friendly)",
            "Light mode (colorblind-friendly)",
            "Dark mode (ANSI colors only)",
            "Light mode (ANSI colors only)"
        ],
        qmark=">"
    ).ask()
    
    console.print("[dim]" + "─" * 80 + "[/dim]")
    
    # Code Preview Block
    console.print("[dim]1[/dim]  [cyan]def[/cyan] [green]analyze_commit[/green]():")
    console.print("[on red][white]2 -     print(\"Likely Human!\")[/white][/on red]")
    console.print("[on green][white]2 +     print(\"Likely AI!\")[/white][/on green]")
    console.print("[dim]3[/dim]  }")
    
    console.print("[dim]" + "─" * 80 + "[/dim]")
    console.print("[dim]Syntax theme: Sniff Default (ctrl+t to disable)[/dim]\n")
    
    time.sleep(0.5)

def build_results_table(count: int) -> Table:
    table = Table(title=f"Last {count} Commits AI Analysis", show_header=True, header_style="bold magenta")
    table.add_column("Commit Hash", style="dim", width=12)
    table.add_column("Author", width=20)
    table.add_column("AI Score", justify="center", width=25)
    table.add_column("Reasoning")
    return table

def build_stats_table(repo_name: str) -> Table:
    table = Table(title=f"Repository AI Stats: {repo_name}", show_header=True, header_style="bold cyan")
    table.add_column("Rank", style="dim", width=6)
    table.add_column("Author", width=25)
    table.add_column("Commits Analyzed", justify="center")
    table.add_column("Average AI Score", justify="center")
    table.add_column("High-AI Commits (>0.7)", justify="center", style="red")
    return table

def format_score(score: float, band: str) -> str:
    if score >= 0.7:
        color = "red bold"
    elif score >= 0.3:
        color = "yellow"
    else:
        color = "green"
    return f"[{color}]{score:.2f} ({band})[/{color}]"

def format_reasons(reasons: list) -> str:
    if not reasons or (len(reasons) == 1 and reasons[0] == "Organic changes"):
        return "[dim]No strong AI signals detected[/dim]"
    
    formatted = []
    for r in reasons:
        if "verbose" in r.lower() or "large block" in r.lower() or "high usage" in r.lower() or "template" in r.lower():
             formatted.append(f"[bold red]•[/bold red] {r}")
        else:
             formatted.append(f"[yellow]•[/yellow] {r}")
    return "\n".join(formatted)

def display_scan_progress(total_commits: int):
    # Dummy progress for visual effect
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Sniffing commits...", total=total_commits)
        for i in range(total_commits):
            time.sleep(0.01)
            progress.advance(task)

def render_trend_chart(results: list):
    if not results or len(results) < 3:
        console.print("[dim]Not enough commits to generate a trend chart (need at least 3).[/dim]")
        return
        
    console.print("\n[bold cyan]AI Usage Trend Over Time (High = AI, Low = Human)[/bold cyan]")
    
    # Extract scores in chronological order (oldest to newest)
    scores = [r["score"] for r in reversed(results)]
    x_data = list(range(1, len(scores) + 1))
    
    # Create the plot
    fig = plotille.Figure()
    fig.width = 60
    fig.height = 15
    fig.set_x_limits(min_=1, max_=len(scores))
    fig.set_y_limits(min_=0.0, max_=1.0)
    fig.y_label = "AI Score"
    fig.x_label = "Commits (Oldest -> Newest)"
    
    # Color based on average trend
    avg_score = sum(scores) / len(scores)
    plot_color = 'green' if avg_score < 0.3 else 'yellow' if avg_score < 0.7 else 'red'
    
    fig.plot(x_data, scores, lc=plot_color)
    
    print(fig.show())
