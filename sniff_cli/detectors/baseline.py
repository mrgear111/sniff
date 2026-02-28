"""
Author Style Baseline Engine
─────────────────────────────
Builds a statistical fingerprint of each developer's historical coding style 
from their first N commits, then flags deviations in new commits.

Signals tracked:
  - avg_function_length: average lines per function
  - avg_commit_size: average lines changed per commit
  - comment_ratio: fraction of lines that are comments
  - naming_style: dominant convention (snake_case, camelCase, etc.)
  - avg_line_length: mean line length
  - line_length_variance: how "regular" their line lengths are (low = AI)
"""

import re
import math
import statistics
from collections import defaultdict, Counter


def _mean(lst):
    return statistics.mean(lst) if lst else 0.0

def _stdev(lst):
    return statistics.stdev(lst) if len(lst) >= 2 else 0.0

def _comment_ratio(diff: str) -> float:
    lines = [l.strip() for l in diff.split('\n') if l.strip()]
    if not lines:
        return 0.0
    comments = sum(1 for l in lines if l.startswith(('#', '//', '/*', '*', '<!--')))
    return comments / len(lines)

def _avg_line_length(diff: str) -> float:
    lines = [l for l in diff.split('\n') if l.strip()]
    return _mean([len(l) for l in lines]) if lines else 0.0

def _line_length_variance(diff: str) -> float:
    """Low variance = suspiciously regular = AI-like."""
    lines = [len(l) for l in diff.split('\n') if l.strip()]
    return _stdev(lines) if lines else 0.0

def _detect_naming_style(diff: str) -> str:
    """Returns dominant naming style: 'snake_case', 'camelCase', 'mixed'."""
    identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', diff)
    snake = sum(1 for i in identifiers if '_' in i and i.islower())
    camel = sum(1 for i in identifiers if re.search(r'[a-z][A-Z]', i))
    if snake > camel * 1.5:
        return 'snake_case'
    elif camel > snake * 1.5:
        return 'camelCase'
    return 'mixed'

def _extract_function_lengths(diff: str) -> list:
    """Rough estimation of function sizes from indentation patterns."""
    lengths = []
    current_fn_lines = 0
    in_function = False
    for line in diff.split('\n'):
        stripped = line.strip()
        if re.match(r'^(def |function |async function |const \w+ = \(|class )', stripped):
            if in_function and current_fn_lines > 0:
                lengths.append(current_fn_lines)
            in_function = True
            current_fn_lines = 1
        elif in_function:
            current_fn_lines += 1
    if in_function and current_fn_lines > 0:
        lengths.append(current_fn_lines)
    return lengths


class AuthorBaseline:
    """Per-author style profile built from historical commits."""
    
    def __init__(self):
        self.profiles = {}  # author -> style dict

    def build_profiles(self, commits, get_commit_diff_fn):
        """
        Build a baseline from the OLDEST commits (which pre-date AI assistance).
        Uses the oldest 30 commits per author to establish the baseline,
        then flags the newest commits as deviations.
        """
        # Collect data per author (oldest commits first)
        author_data = defaultdict(list)
        for commit in reversed(commits):
            author = commit.author.name
            diff = get_commit_diff_fn(commit)
            if not diff.strip():
                continue
            lines = [l for l in diff.split('\n') if l.strip()]
            author_data[author].append({
                'diff': diff,
                'lines': len(lines),
                'comment_ratio': _comment_ratio(diff),
                'avg_line_length': _avg_line_length(diff),
                'line_length_variance': _line_length_variance(diff),
                'fn_lengths': _extract_function_lengths(diff),
                'naming_style': _detect_naming_style(diff),
            })

        for author, entries in author_data.items():
            # Use oldest half as baseline, newest half as subject of analysis
            baseline_entries = entries[:max(1, len(entries) // 2)]
            
            commit_sizes = [e['lines'] for e in baseline_entries]
            comment_ratios = [e['comment_ratio'] for e in baseline_entries]
            line_lengths = [e['avg_line_length'] for e in baseline_entries]
            variances = [e['line_length_variance'] for e in baseline_entries]
            fn_lengths = []
            for e in baseline_entries:
                fn_lengths.extend(e['fn_lengths'])
            naming_styles = [e['naming_style'] for e in baseline_entries]
            dominant_naming = Counter(naming_styles).most_common(1)[0][0] if naming_styles else 'mixed'

            self.profiles[author] = {
                'avg_commit_size': _mean(commit_sizes),
                'commit_size_stdev': _stdev(commit_sizes),
                'avg_comment_ratio': _mean(comment_ratios),
                'avg_line_length': _mean(line_lengths),
                'avg_line_variance': _mean(variances),
                'avg_fn_length': _mean(fn_lengths),
                'dominant_naming': dominant_naming,
                'total_baseline_commits': len(baseline_entries),
            }

    def analyze_deviation(self, author: str, diff: str) -> dict:
        """
        Compare a single commit's style against the author's baseline.
        Returns a score 0-1 where high score = strong deviation from baseline.
        """
        if author not in self.profiles or not diff.strip():
            return {"score": 0.0, "reason": "No baseline available"}
        
        profile = self.profiles[author]
        # Need at least 5 baseline commits for reliable comparison
        if profile['total_baseline_commits'] < 5:
            return {"score": 0.0, "reason": "Insufficient baseline history"}

        score = 0.0
        reasons = []

        lines = [l for l in diff.split('\n') if l.strip()]
        commit_size = len(lines)
        comment_ratio = _comment_ratio(diff)
        line_variance = _line_length_variance(diff)
        naming = _detect_naming_style(diff)
        fn_lengths = _extract_function_lengths(diff)
        avg_fn = _mean(fn_lengths) if fn_lengths else 0.0

        baseline_size = profile['avg_commit_size']
        baseline_stdev = profile['commit_size_stdev']

        # ── 1. Commit size deviation ────────────────────────────────────────
        if baseline_size > 0 and baseline_stdev > 0:
            z_score = abs(commit_size - baseline_size) / (baseline_stdev + 1)
            if z_score > 2.0:
                score += 0.4
                reasons.append(f"Commit size extreme outlier (z={z_score:.1f}σ from author baseline of {baseline_size:.0f} lines)")
            elif z_score > 1.2:
                score += 0.2
                reasons.append(f"Unusual commit size (z={z_score:.1f}σ from author baseline)")

        # ── 2. Comment ratio deviation ──────────────────────────────────────
        baseline_cr = profile['avg_comment_ratio']
        cr_diff = comment_ratio - baseline_cr
        if cr_diff > 0.10 and commit_size > 15:
            score += 0.25
            reasons.append(f"Comment density spike (+{cr_diff*100:.0f}% above author baseline)")

        # ── 3. Line length regularity (AI writes unnaturally consistent lines)─
        baseline_var = profile['avg_line_variance']
        if baseline_var > 4 and line_variance < (baseline_var * 0.5) and commit_size > 20:
            score += 0.3
            reasons.append(f"Abnormally regular line lengths (variance {line_variance:.1f} vs author baseline {baseline_var:.1f})")

        # ── 4. Naming style shift ────────────────────────────────────────────
        if naming != profile['dominant_naming'] and naming != 'mixed' and commit_size > 15:
            score += 0.2
            reasons.append(f"Naming style shift ({profile['dominant_naming']} → {naming})")

        # ── 5. Function length anomaly ───────────────────────────────────────
        baseline_fn = profile['avg_fn_length']
        if baseline_fn > 0 and avg_fn > 0:
            fn_ratio = avg_fn / baseline_fn
            if fn_ratio > 1.8:
                score += 0.25
                reasons.append(f"Functions {fn_ratio:.1f}x longer than author historical average")

        return {
            "score": min(score, 1.0),
            "reason": "; ".join(reasons) if reasons else "Style consistent with author baseline"
        }
