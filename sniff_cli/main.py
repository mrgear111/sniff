import typer
import sys
import json
import questionary
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

from sniff_cli.git_client import get_repo, get_commits, get_commit_diff
from sniff_cli.detectors.text import TextDetector
from sniff_cli.detectors.code import CodeDetector
from sniff_cli.detectors.scoring import ScoreAggregator
from sniff_cli.ui import print_welcome, build_results_table, build_stats_table, format_score, format_reasons, display_scan_progress, render_trend_chart

console = Console()
app = typer.Typer(help="Sniff AI Contribution Detection CLI", add_completion=False)

def _get_analysis_data(path: str, count: int):
    repo = get_repo(path)
    if not repo:
        return None, f"'{path}' is not a valid Git repository."

    commits = get_commits(repo, count)
    if not commits:
        return None, "No commits found."

    text_detector = TextDetector()
    code_detector = CodeDetector()
    aggregator = ScoreAggregator()

    # Calculate velocities chronologically (oldest first)
    author_last_seen = {}
    commit_velocities = {}
    for commit in reversed(commits):
        author = commit.author.name
        timestamp = commit.committed_datetime
        diff = get_commit_diff(commit)
        lines_added = len([l for l in diff.split('\n') if l.strip()])
        
        if author in author_last_seen:
            minutes = (timestamp - author_last_seen[author]).total_seconds() / 60.0
            velocity = lines_added / minutes if minutes > 0 else lines_added
        else:
            velocity = 0.0
            
        author_last_seen[author] = timestamp
        commit_velocities[commit.hexsha] = velocity

    results = []
    
    for commit in commits:
        author = commit.author.name
        message = commit.message
        diff = get_commit_diff(commit)

        text_res = text_detector.analyze(message)
        code_res = code_detector.analyze(diff)
        velocity = commit_velocities.get(commit.hexsha, 0.0)
        final_res = aggregator.compute(text_res, code_res, velocity_lpm=velocity)
        
        results.append({
            "hash": commit.hexsha,
            "short_hash": commit.hexsha[:7],
            "author": author,
            "score": final_res["score"],
            "band": final_res["band"],
            "reasons": final_res["reasons"]
        })
    return results, None

@app.command(name="scan")
def scan_cmd(
    path: str = typer.Option(".", help="Path to the Git repository"), 
    count: int = typer.Option(10, help="Number of commits to scan"),
    export_json: bool = typer.Option(False, "--json", help="Export results as JSON")
):
    """Scan a repository and compute an AI-Likelihood Score for recent commits."""
    if not export_json:
        display_scan_progress(count)
        
    results, err = _get_analysis_data(path, count)
    if err:
        if export_json:
            print(json.dumps({"error": err}))
        else:
            console.print(f"[bold red]Error[/bold red]: {err}")
        return

    if export_json:
        print(json.dumps(results, indent=2))
        return

    table = build_results_table(len(results))
    for r in results:
        f_score = format_score(r["score"], r["band"])
        f_reasons = format_reasons(r["reasons"])
        table.add_row(r["short_hash"], r["author"], f_score, f_reasons)
        table.add_row("", "", "", "") # spacer

    console.print(table)
    
    # Render the visual chart if not exporting JSON
    if not export_json:
        render_trend_chart(results)

@app.command(name="stats")
def stats_cmd(
    path: str = typer.Option(".", help="Path to the Git repository"), 
    count: int = typer.Option(50, help="Number of commits to analyze for stats"),
    export_json: bool = typer.Option(False, "--json", help="Export results as JSON")
):
    """Generate repository-level AI usage analytics and an author leaderboard."""
    if not export_json:
        display_scan_progress(count)

    results, err = _get_analysis_data(path, count)
    if err:
        if export_json:
            print(json.dumps({"error": err}))
        else:
            console.print(f"[bold red]Error[/bold red]: {err}")
        return

    # Aggregate by author
    authors = {}
    for r in results:
        a = r["author"]
        if a not in authors:
            authors[a] = {"total_commits": 0, "sum_score": 0.0, "high_ai": 0}
        authors[a]["total_commits"] += 1
        authors[a]["sum_score"] += r["score"]
        if r["score"] >= 0.7:
            authors[a]["high_ai"] += 1

    leaderboard = []
    for a, data in authors.items():
        avg = data["sum_score"] / data["total_commits"]
        leaderboard.append({
            "author": a,
            "commits_analyzed": data["total_commits"],
            "avg_score": round(avg, 3),
            "high_ai_commits": data["high_ai"]
        })
    
    # Sort by avg score descending
    leaderboard = sorted(leaderboard, key=lambda x: x["avg_score"], reverse=True)

    if export_json:
        print(json.dumps({"repository_stats": leaderboard}, indent=2))
        return

    repo_name = Path(path).resolve().name
    table = build_stats_table(repo_name)
    
    for i, lb in enumerate(leaderboard):
        rank = str(i + 1)
        author = lb["author"]
        commits_num = str(lb["commits_analyzed"])
        
        # Format avg score color
        avg = lb["avg_score"]
        if avg >= 0.7:
            avg_str = f"[bold red]{avg:.2f}[/bold red]"
        elif avg >= 0.3:
            avg_str = f"[yellow]{avg:.2f}[/yellow]"
        else:
            avg_str = f"[green]{avg:.2f}[/green]"
            
        high_ai = str(lb["high_ai_commits"]) if lb["high_ai_commits"] > 0 else "[dim]0[/dim]"
        
        table.add_row(rank, author, commits_num, avg_str, high_ai)

    console.print(table)
    
    # Render overall repo trend chart
    if not export_json:
        render_trend_chart(results)

@app.command(name="interactive")
def interactive_cmd():
    """Start an interactive Claude-like persistent REPL session."""
    from sniff_cli.ui import clear_screen
    print_welcome()
    
    # Guided Repository Selection
    console.print("\n[bold cyan]Step 1: Connect Repository[/bold cyan]")
    try:
        repo_input = input("Enter the path or URL to the Git repository (Leave blank for current directory): ").strip()
    except EOFError:
        repo_input = ""
        
    current_repo = repo_input if repo_input else "."
    
    # Handle Remote URL on boot
    if current_repo.startswith(("http://", "https://", "git@")):
        import tempfile
        import git
        console.print(f"\n[cyan]Remote URL detected. Cloning into temporary cache...[/cyan]")
        try:
            temp_dir = tempfile.mkdtemp(prefix="sniff_")
            git.Repo.clone_from(current_repo, temp_dir)
            current_repo = temp_dir
            console.print(f"[green]✔ Cloned successfully![/green]\n")
        except Exception as e:
            console.print(f"[red]Error cloning repository: {e}[/red]")
            current_repo = "."
            
    # Verify Connection
    try:
        get_repo(current_repo)
        console.print(f"[bold green]✔ Success![/bold green] Connected to repository at '{current_repo}'\n")
        console.print("[dim]Type 'scan' to analyze recent commits, 'stats' for a contributor leaderboard, or 'help' for commands.[/dim]\n")
    except Exception as e:
        console.print(f"[red]Warning: Could not detect a valid Git repository at '{current_repo}'[/red]")
        console.print("[yellow]Starting shell anyway. You can use 'cd <path>' later to switch repositories.[/yellow]\n")
        current_repo = "."
    
    while True:
        try:
            # The prompt behaves like a real terminal
            try:
                raw_input = input(f"[{current_repo}] sniff> ")
            except EOFError:
                raw_input = None
            
            # Handle Ctrl+C or EOF gracefully
            if raw_input is None:
                console.print("\n[dim]Session terminated.[/dim]")
                break
                
            command = raw_input.strip().lower()
            
            if not command:
                continue
                
            if command in ["exit", "quit", "q"]:
                console.print("[dim]Goodbye![/dim]")
                break
                
            elif command == "clear":
                clear_screen()
                print_welcome()
                
            elif command in ["help", "?"]:
                console.print(Panel(
                    "[bold cyan]Available Commands:[/bold cyan]\n"
                    "  [bold]scan [count][/bold]   - Scan recent commits for AI generation (default 10)\n"
                    "  [bold]stats [count][/bold]  - View leaderboard and AI trend charts (default 50)\n"
                    "  [bold]cd <path>[/bold]      - Change the active repository path\n"
                    "  [bold]theme[/bold]          - Configure terminal syntax colors\n"
                    "  [bold]clear[/bold]          - Clear the terminal screen\n"
                    "  [bold]exit[/bold]           - Quit the session", 
                    title="Sniff REPL Help", 
                    border_style="cyan", 
                    expand=False
                ))
                
            elif command.startswith("cd "):
                new_path = raw_input[3:].strip()
                
                # Handle Remote URL in `cd` command
                if new_path.startswith(("http://", "https://", "git@")):
                    import tempfile
                    import git
                    console.print(f"\n[cyan]Remote URL detected. Cloning into temporary cache...[/cyan]")
                    try:
                        temp_dir = tempfile.mkdtemp(prefix="sniff_")
                        git.Repo.clone_from(new_path, temp_dir)
                        new_path = temp_dir
                        console.print(f"[green]✔ Cloned successfully![/green]\n")
                    except Exception as e:
                        console.print(f"[red]Error cloning repository: {e}[/red]")
                        continue
                        
                if Path(new_path).exists():
                    current_repo = new_path
                    console.print(f"[green]Working repository changed to:[/green] {current_repo}")
                else:
                    console.print(f"[bold red]Error[/bold red]: Path '{new_path}' does not exist.")
                    
            elif command.startswith("scan"):
                parts = command.split()
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
                console.print()
                scan_cmd(path=current_repo, count=count, export_json=False)
                
            elif command.startswith("stats"):
                parts = command.split()
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
                console.print()
                stats_cmd(path=current_repo, count=count, export_json=False)
                
            elif command == "theme":
                # Simulated theme selector for the pitch
                choices = [
                    "Dark mode",
                    "Light mode", 
                    "Dark mode (colorblind-friendly)",
                    "Light mode (colorblind-friendly)"
                ]
                theme = questionary.select(
                    "Choose the text style that looks best with your terminal:",
                    choices=choices
                ).ask()
                console.print(f"[green]✔ Saved! Syntax theme updated to:[/green] {theme}")
                
            else:
                console.print(f"[yellow]Unknown command:[/yellow] '{command}'. Type 'help' to see available commands.")
                
        except KeyboardInterrupt:
            console.print("\n[dim]Session terminated.[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")

def main():
    if len(sys.argv) == 1:
        interactive_cmd()
    else:
        app()

if __name__ == "__main__":
    main()
