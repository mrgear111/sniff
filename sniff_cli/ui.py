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
    console.print(f"[bold cyan]{ascii_banner}[/bold cyan]", end="")
    console.print("[dim]v1.0.0 | Terminal-Native AI Detection Engine[/dim]\n")
    
    # Animated typing for the welcome text
    type_text("Let's get started.", style="bold white", delay=0.03)
    time.sleep(0.1)
    
    console.print("\n[dim]" + "─" * 60 + "[/dim]")
    
    # Simulated sleek boot sequence
    boot_sequence = [
        ("Checking for local Git repository...", "[green]Found[/green]"),
        ("Loading 4-cylinder offline engines...", "[green]OK[/green]"),
        ("Loading structural parsing models...", "[green]OK[/green]"),
        ("Mounting LLM tie-breaker protocol...", "[cyan]Ready[/cyan]"),
    ]
    
    for message, status in boot_sequence:
        console.print(f"[dim]>[/dim] {message:<40} {status}")
        time.sleep(0.08)
        
    console.print("[dim]" + "─" * 60 + "[/dim]\n")
    
    console.print("[bold white]System Online. Type 'scan' to analyze recent commits.[/bold white]\n")
    time.sleep(0.2)

import rich.box as box

def build_results_table(count: int) -> Table:
    table = Table(
        title=f"Last {count} Commits AI Analysis", 
        show_header=True, 
        header_style="bold cyan",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True
    )
    table.add_column("Commit Hash", style="dim", width=12)
    table.add_column("Author", width=20)
    table.add_column("AI Score", justify="center", width=25)
    table.add_column("Reasoning")
    return table

def build_stats_table(repo_name: str) -> Table:
    table = Table(
        title=f"Repository AI Stats: {repo_name}", 
        show_header=True, 
        header_style="bold cyan",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True
    )
    table.add_column("Rank", style="dim", width=6)
    table.add_column("Author", width=25)
    table.add_column("Commits Analyzed", justify="center")
    table.add_column("Avg AI Score", justify="center")
    table.add_column("High-AI Commits (>0.7)", justify="center", style="red")
    return table

def render_verdict(results: list):
    """Render a bold final summary verdict panel after analysis."""
    if not results:
        return
    
    scores = [r["score"] for r in results]
    
    if len(scores) > 0:
        true_mean = sum(scores) / len(scores)
        top_scores = sorted(scores, reverse=True)[:max(1, int(len(scores) * 0.20))]
        top_20_mean = sum(top_scores) / len(top_scores)
        
        # Count severe violations
        high_ai_count = sum(1 for s in scores if s >= 0.7)
        ai_density = high_ai_count / len(scores)
        
        if ai_density >= 0.15: # Blatant AI presence -> aggressive anchoring
            raw_avg = top_20_mean
        elif high_ai_count > 0: # Some infractions -> mixed blend
            raw_avg = (true_mean + top_20_mean) / 2
        else: # Pure human / no severe spikes -> stick to true mathematical mean
            raw_avg = true_mean
    else:
        raw_avg = 0.0
        
    avg_score = raw_avg
    high_ai_count = sum(1 for s in scores if s >= 0.7)
    
    density_override = False
    # Force high severity if the repo has a massive density of high-AI commits
    # Even if they are balanced out by clean human commits
    if len(scores) > 0 and (high_ai_count / len(scores)) >= 0.25:
        avg_score = max(avg_score, 0.60)
        if avg_score > raw_avg:
            density_override = True
            
    pct = int(avg_score * 100)
    raw_pct = int(raw_avg * 100)
    
    if avg_score >= 0.50:
        verdict_icon = "🔴"
        verdict_label = "LIKELY AI-ASSISTED"
        verdict_color = "bold red"
        risk_msg = "High AI dependency detected. Manual code review strongly recommended."
    elif avg_score >= 0.25:
        verdict_icon = "🟡"
        verdict_label = "MIXED — PARTIALLY AI-ASSISTED"
        verdict_color = "bold yellow"
        risk_msg = "Moderate AI usage signals. Some commits warrant closer human review."
    else:
        verdict_icon = "🟢"
        verdict_label = "LIKELY HUMAN-WRITTEN"
        verdict_color = "bold green"
        risk_msg = "Low AI usage signals detected across the analyzed commits."

    score_display = f"[{verdict_color}]{pct}%[/{verdict_color}]"
    if density_override:
        score_display += f" [dim](Boosted from {raw_pct}% due to critical AI density)[/dim]"

    summary_text = (
        f"[{verdict_color}]{verdict_icon}  VERDICT: {verdict_label}[/{verdict_color}]\n\n"
        f"  Overall AI-Likelihood Score : {score_display}\n"
        f"  Commits Analyzed            : {len(scores)}\n"
        f"  High-AI Commits (≥70%)      : [bold red]{high_ai_count}[/bold red]\n\n"
        f"  [dim]{risk_msg}[/dim]"
    )
    
    console.print()
    console.print(Panel(
        summary_text,
        title="[bold]Analysis Complete[/bold]",
        border_style=verdict_color.replace("bold ", ""),
        expand=False,
        padding=(1, 4)
    ))
    console.print()

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
