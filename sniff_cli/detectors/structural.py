"""
Structural Regularity & SimHash Similarity Engine
──────────────────────────────────────────────────
Two complementary signals:

1. Structural Regularity
   AI-generated code has unnaturally narrow line length distributions
   (tight Gaussian around 60-80 chars). Human code has fat tails.
   We measure the coefficient of variation of the line length histogram.

2. SimHash Code Similarity
   AI tools produce near-duplicate code across different commits and authors.
   We hash each diff using a rolling token hash and flag near-duplicates
   within the same repo's commit history.
"""

import re
import math
import statistics
from collections import Counter


# ─── Structural Regularity ──────────────────────────────────────────────────

def _line_stats(diff: str):
    """Return (mean, stdev, cv) of line lengths."""
    lines = [len(l) for l in diff.split('\n') if l.strip()]
    if len(lines) < 5:
        return 0, 0, 0
    mean = statistics.mean(lines)
    stdev = statistics.stdev(lines) if len(lines) >= 2 else 0
    cv = stdev / mean if mean > 0 else 0  # Coefficient of Variation
    return mean, stdev, cv


def analyze_structural_regularity(diff: str) -> dict:
    """
    Low CV (coefficient of variation) = line lengths are suspiciously uniform = AI.
    Very high CV = chaotic, inconsistent = human style.
    
    Typical CV ranges:
      AI-generated:  0.15 - 0.35 (tight distribution)
      Human code:    0.40 - 0.80 (fat tails, short one-liners + long complex lines)
    """
    lines = [l for l in diff.split('\n') if l.strip()]
    if len(lines) < 8:
        return {"score": 0.0, "reason": "Diff too small for structural analysis"}

    mean, stdev, cv = _line_stats(diff)
    score = 0.0
    reasons = []

    # Very low CV = AI-style regularity
    if cv < 0.25 and len(lines) > 15:
        score += 0.5
        reasons.append(f"Abnormally uniform line lengths (CV={cv:.2f}) — AI-generated code signature")
    elif cv < 0.35 and len(lines) > 20:
        score += 0.25
        reasons.append(f"Suspicious line length regularity (CV={cv:.2f})")

    # Check for suspiciously narrow line length range
    lengths = [len(l) for l in diff.split('\n') if l.strip()]
    p10 = sorted(lengths)[int(len(lengths) * 0.1)]
    p90 = sorted(lengths)[int(len(lengths) * 0.9)]
    range_ratio = (p90 - p10) / (mean + 1)

    if range_ratio < 0.5 and len(lines) > 20:
        score += 0.2
        reasons.append(f"Narrow line length range (P10={p10}, P90={p90}) — uniform AI formatting")

    # Blank line pattern — AI inserts exactly one blank line between every function
    blank_gaps = []
    gap = 0
    for l in diff.split('\n'):
        if not l.strip():
            gap += 1
        else:
            if gap > 0:
                blank_gaps.append(gap)
            gap = 0
    if len(blank_gaps) >= 3:
        gap_cv = statistics.stdev(blank_gaps) / (statistics.mean(blank_gaps) + 0.001)
        if gap_cv < 0.3:
            score += 0.15
            reasons.append("Perfectly regular blank-line spacing (AI formatting pattern)")

    return {
        "score": min(score, 1.0),
        "reason": "; ".join(reasons) if reasons else "Organic structural variation"
    }


# ─── SimHash Code Similarity ────────────────────────────────────────────────

def _tokenize(text: str) -> list:
    """Tokenize code into meaningful tokens, stripping whitespace noise."""
    # Strip comments
    text = re.sub(r'//.*?\n', '\n', text)
    text = re.sub(r'#.*?\n', '\n', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Extract identifiers and keywords
    tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{1,}\b', text)
    return tokens


def _simhash(tokens: list, bits: int = 64) -> int:
    """
    Compute a SimHash of the token list.
    Two diffs with >85% similar tokens will have small Hamming distance.
    """
    if not tokens:
        return 0
    
    v = [0] * bits
    for token in tokens:
        # Simple rolling hash per token
        h = hash(token) % (2 ** bits)
        for i in range(bits):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    
    fingerprint = 0
    for i in range(bits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def _hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two hashes."""
    xor = h1 ^ h2
    return bin(xor).count('1')


def _similarity(h1: int, h2: int, bits: int = 64) -> float:
    """Return similarity score 0-1 based on Hamming distance."""
    dist = _hamming_distance(h1, h2)
    return 1.0 - (dist / bits)


class SimHashIndex:
    """Maintains a rolling index of commit diff hashes for similarity detection."""
    
    def __init__(self, similarity_threshold: float = 0.80):
        self.threshold = similarity_threshold
        self.index = []  # list of (hexsha, author, simhash)

    def add(self, hexsha: str, author: str, diff: str):
        tokens = _tokenize(diff)
        if len(tokens) < 10:
            return
        h = _simhash(tokens)
        self.index.append((hexsha, author, h))

    def find_duplicates(self, hexsha: str, author: str, diff: str) -> list:
        """
        Returns list of (other_hexsha, other_author, similarity) 
        for commits that are suspiciously similar to this diff.
        """
        tokens = _tokenize(diff)
        if len(tokens) < 10:
            return []
        h = _simhash(tokens)
        matches = []
        for other_sha, other_author, other_hash in self.index:
            if other_sha == hexsha:
                continue
            sim = _similarity(h, other_hash)
            if sim >= self.threshold:
                matches.append((other_sha[:7], other_author, sim))
        return sorted(matches, key=lambda x: x[2], reverse=True)

    def analyze(self, hexsha: str, author: str, diff: str) -> dict:
        """Analyze a diff for similarity to previously seen commits."""
        matches = self.find_duplicates(hexsha, author, diff)
        if not matches:
            self.add(hexsha, author, diff)
            return {"score": 0.0, "reason": "No near-duplicate commits found"}

        top_match = matches[0]
        score = 0.0
        reasons = []

        sim = top_match[2]
        other_sha = top_match[0]
        other_author = top_match[1]

        if sim >= 0.92:
            score = 0.8
            reasons.append(f"Near-identical code to commit {other_sha} by {other_author} ({int(sim*100)}% token similarity) — strong AI copy-paste signal")
        elif sim >= 0.85:
            score = 0.5
            reasons.append(f"High code similarity to {other_sha} by {other_author} ({int(sim*100)}% match) — possible AI template reuse")
        elif sim >= 0.80:
            score = 0.25
            reasons.append(f"Moderate code similarity to {other_sha} ({int(sim*100)}% match)")

        # Cross-author duplicate is especially suspicious
        if other_author != author and sim >= 0.85:
            score = min(score + 0.2, 1.0)
            reasons[0] += " [cross-author]"

        self.add(hexsha, author, diff)
        return {
            "score": min(score, 1.0),
            "reason": "; ".join(reasons) if reasons else "No strong similarity signals"
        }
