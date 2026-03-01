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


def scan_cmd(
    path: str = ".",
    count: int = 10,
    export_json: bool = False,
    no_llm: bool = False
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

def stats_cmd(
    path: str = ".", 
    count: int = 50,
    export_json: bool = False,
    no_llm: bool = False
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
        ai_density = data["high_ai"] / data["total_commits"]
        
        # Build colored density string
        pct_color = "red" if ai_density >= 0.15 else "yellow" if ai_density > 0 else "green"
        density_str = f"[{pct_color}]{int(ai_density * 100)}%[/{pct_color}]"
        
        # Build Heat Bar (10 blocks)
        total_blocks = 10
        filled = int(avg * total_blocks)
        empty = total_blocks - filled
        bar = f"[{pct_color}]{'█' * filled}[/{pct_color}][dim]{'▬' * empty}[/dim]"
        
        leaderboard.append({
            "author": a,
            "commits_analyzed": data["total_commits"],
            "avg_score": round(avg, 3),
            "high_ai_commits": data["high_ai"],
            "ai_density": density_str,
            "bar": bar
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
        
        table.add_row(rank, author, commits_num, high_ai, avg_str, lb["ai_density"], lb["bar"])

    console.print()
    console.print(table)
    console.print()

@app.callback(invoke_without_command=True)
def interactive_cmd(ctx: typer.Context):
    """Start an interactive Claude-like persistent REPL session."""
    if ctx.invoked_subcommand is not None:
        return
        
    from sniff_cli.ui import clear_screen
    print_welcome()

    import os
    import questionary

    console.print("[bold cyan]Step 1: LLM Verification (Optional)[/bold cyan]")
    use_llm_choice = questionary.select(
        "Enable LLM Tie-Breaker Protocol for borderline commits?",
        choices=[
            "Yes (Requires Anthropic API Key)",
            "No (Pure Offline Mode)"
        ]
    ).ask()

    global_use_llm = True
    if use_llm_choice and "No" in use_llm_choice:
        global_use_llm = False
    elif use_llm_choice:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            api_key = questionary.password("Enter Anthropic API Key (sk-ant-...):").ask()
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key.strip()
            else:
                console.print("[yellow]No API key provided. Falling back to Pure Offline Mode.[/yellow]")
                global_use_llm = False
    else:
        # User hit Ctrl+C on the prompt
        return

    console.print()
    # Guided Repository Selection
    console.print("[bold cyan]Step 2: Connect Repository[/bold cyan]")
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
                # Find the actual nested .git folder dropped inside the temporary directory
                cloned_repos = [f.parent for f in Path(temp_dir).rglob(".git") if f.is_dir()]
                if cloned_repos:
                    current_repo = str(cloned_repos[0])
                    console.print(f"[green]✔ Cloned successfully![/green]\n")
                else:
                    console.print("[red]Clone succeeded but no .git directory was found.[/red]")
                    current_repo = "."
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
            
    # Validate the directory contains a Git repo
    try:
        repo = get_repo(current_repo)
        if not repo:
            raise ValueError()
            
        repo_name = Path(current_repo).resolve().name
        console.print(f"\n[bold green]✔ Connected to repository:[/bold green] [cyan]{repo_name}[/cyan]")
        console.print("[dim]Type 'scan' to analyze recent commits, 'stats' for a contributor leaderboard, or 'help' for commands.[/dim]\n")
        console.print("[dim]Tip: You can use 'cd <path>' anytime to switch to a different repository.[/dim]\n")
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
                            cloned_repos = [f.parent for f in Path(temp_dir).rglob(".git") if f.is_dir()]
                            if cloned_repos:
                                new_path = str(cloned_repos[0])
                                console.print(f"[green]✔ Cloned successfully![/green]\n")
                            else:
                                console.print("[red]Clone succeeded but no .git directory was found.[/red]")
                                continue
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
                
                # If the user explicitly passed the flag, respect it for this run. Otherwise use the global session choice.
                run_without_llm = True if no_llm_flag else (not global_use_llm)
                scan_cmd(path=current_repo, count=count, export_json=False, no_llm=run_without_llm)
                
            elif command.startswith("stats"):
                parts = command.split()
                no_llm_flag = "--no-llm" in parts
                parts = [p for p in parts if p != "--no-llm"]
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
                console.print()
                
                run_without_llm = True if no_llm_flag else (not global_use_llm)
                stats_cmd(path=current_repo, count=count, export_json=False, no_llm=run_without_llm)
                
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
    app()

if __name__ == "__main__":
    main()
