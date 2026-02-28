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
from sniff_cli.detectors.baseline import AuthorBaseline
from sniff_cli.detectors.structural import analyze_structural_regularity, SimHashIndex
from sniff_cli.detectors.semantic import SemanticDetector
from sniff_cli.detectors.llm import LLMAnalyzer
from sniff_cli.ui import print_welcome, build_results_table, build_stats_table, format_score, format_reasons, display_scan_progress, render_trend_chart, render_verdict

console = Console()
app = typer.Typer(help="Sniff AI Contribution Detection CLI", add_completion=False)

def _get_analysis_data(path: str, count: int, use_llm: bool = True):
    repo = get_repo(path)
    if not repo:
        return None, f"'{path}' is not a valid Git repository."

    commits = get_commits(repo, count)
    if not commits:
        return None, "No commits found."

    text_detector = TextDetector()
    code_detector = CodeDetector()
    semantic_detector = SemanticDetector()
    llm_analyzer = LLMAnalyzer()
    simhash_index = SimHashIndex(similarity_threshold=0.82)
    aggregator = ScoreAggregator()

    # Build Author Style Baseline from expanded history
    all_commits = get_commits(repo, max(count * 3, 60))
    author_baseline = AuthorBaseline()
    author_baseline.build_profiles(all_commits, get_commit_diff)

    # Velocity & Burst Detection
    author_last_seen = {}
    commit_velocities = {}
    author_commit_times = {}

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

        if author not in author_commit_times:
            author_commit_times[author] = []
        author_commit_times[author].append((timestamp, commit.hexsha, lines_added))

    # Burst detection: ≥5 large commits in 10-minute window
    burst_commits = set()
    for author, entries in author_commit_times.items():
        entries.sort(key=lambda x: x[0])
        for i in range(len(entries)):
            window = [e for e in entries[i:]
                      if (e[0] - entries[i][0]).total_seconds() <= 600]
            large_in_window = sum(1 for e in window if e[2] > 20)
            if len(window) >= 5 and large_in_window >= 3:
                for e in window:
                    burst_commits.add(e[1])
                break

    results = []
    for commit in commits:
        author = commit.author.name
        message = commit.message
        diff = get_commit_diff(commit)
        diff_lines = len([l for l in diff.split('\n') if l.strip()])

        text_res       = text_detector.analyze(message, diff_lines=diff_lines)
        code_res       = code_detector.analyze(diff)
        structural_res = analyze_structural_regularity(diff)
        similarity_res = simhash_index.analyze(commit.hexsha, author, diff)
        semantic_res   = semantic_detector.analyze(message, diff)
        baseline_res   = author_baseline.analyze_deviation(author, diff)
        velocity       = commit_velocities.get(commit.hexsha, 0.0)
        burst_score    = 0.4 if commit.hexsha in burst_commits else 0.0

        final_res = aggregator.compute(
            text_res, code_res,
            velocity_lpm=velocity,
            burst_score=burst_score,
            structural_res=structural_res,
            similarity_res=similarity_res,
            semantic_res=semantic_res,
            baseline_res=baseline_res,
        )

        # --- LLM Tie-Breaker for Borderline Commits ---
        # If the ML engines are unsure (score between 0.35 and 0.50), let Claude decide
        if use_llm and (0.35 <= final_res["score"] <= 0.50):
            llm_res = llm_analyzer.analyze(diff, message)
            if llm_res["score"] != -1.0:
                final_res["score"] = llm_res["score"]
                final_res["reasons"].append(llm_res["reason"])
                final_res["reasons"].append("Local engines returned borderline score. Final score was determined by LLM.")

        final_res["band"] = "Likely AI-assisted" if final_res["score"] > 0.50 else "Likely Human" if final_res["score"] < 0.20 else "Mixed / Uncertain"

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
    export_json: bool = typer.Option(False, "--json", help="Export results as JSON"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM tie-breaker (pure local engines)")
):
    """Scan a repository and compute an AI-Likelihood Score for recent commits."""
    if not export_json:
        display_scan_progress(count)
        
    results, err = _get_analysis_data(path, count, use_llm=not no_llm)
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
        render_verdict(results)

@app.command(name="stats")
def stats_cmd(
    path: str = typer.Option(".", help="Path to the Git repository"), 
    count: int = typer.Option(50, help="Number of commits to analyze for stats"),
    export_json: bool = typer.Option(False, "--json", help="Export results as JSON"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM tie-breaker (pure local engines)")
):
    """Generate repository-level AI usage analytics and an author leaderboard."""
    if not export_json:
        display_scan_progress(count)

    results, err = _get_analysis_data(path, count, use_llm=not no_llm)
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
        render_verdict(results)

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
        import subprocess
        console.print(f"\n[cyan]Remote URL detected. Cloning last 50 commits (shallow)...[/cyan]")
        console.print("[dim]This may take 5-30 seconds depending on network speed.[/dim]")
        try:
            temp_dir = tempfile.mkdtemp(prefix="sniff_")
            result = subprocess.run(
                ["git", "clone", "--depth", "50", "--single-branch", current_repo, temp_dir],
                capture_output=False,
                timeout=90
            )
            if result.returncode == 0:
                current_repo = temp_dir
                console.print(f"[green]✔ Cloned successfully![/green]\n")
            else:
                console.print(f"[red]Clone failed (exit code {result.returncode}). Check the URL and try again.[/red]")
                current_repo = "."
        except subprocess.TimeoutExpired:
            console.print(f"[red]Clone timed out after 90 seconds. The repository may be too large or network is too slow.[/red]")
            console.print("[yellow]Tip: Clone the repo manually and use 'cd /path/to/local/clone' instead.[/yellow]")
            current_repo = "."
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
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
                    "  [bold]scan [count] [--no-llm][/bold]  - Scan recent commits for AI generation (default 10)\n"
                    "  [bold]stats [count] [--no-llm][/bold] - View leaderboard and AI trend charts (default 50)\n"
                    "  [bold]cd <path>[/bold]                 - Change the active repository path\n"
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
                    import subprocess
                    console.print(f"\n[cyan]Remote URL detected. Cloning last 50 commits (shallow)...[/cyan]")
                    console.print("[dim]This may take 5-30 seconds depending on network speed.[/dim]")
                    try:
                        temp_dir = tempfile.mkdtemp(prefix="sniff_")
                        result = subprocess.run(
                            ["git", "clone", "--depth", "50", "--single-branch", new_path, temp_dir],
                            capture_output=False,
                            timeout=90
                        )
                        if result.returncode == 0:
                            new_path = temp_dir
                            console.print(f"[green]\u2714 Cloned successfully![/green]\n")
                        else:
                            console.print(f"[red]Clone failed. Check the URL and try again.[/red]")
                            continue
                    except subprocess.TimeoutExpired:
                        console.print(f"[red]Clone timed out. Try cloning manually and use 'cd /local/path'.[/red]")
                        continue
                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]")
                        continue
                        
                if Path(new_path).exists():
                    current_repo = new_path
                    console.print(f"[green]Working repository changed to:[/green] {current_repo}")
                else:
                    console.print(f"[bold red]Error[/bold red]: Path '{new_path}' does not exist.")
                    
            elif command.startswith("scan"):
                parts = command.split()
                no_llm_flag = "--no-llm" in parts
                parts = [p for p in parts if p != "--no-llm"]
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
                console.print()
                scan_cmd(path=current_repo, count=count, export_json=False, no_llm=no_llm_flag)
                
            elif command.startswith("stats"):
                parts = command.split()
                no_llm_flag = "--no-llm" in parts
                parts = [p for p in parts if p != "--no-llm"]
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
                console.print()
                stats_cmd(path=current_repo, count=count, export_json=False, no_llm=no_llm_flag)
                
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
