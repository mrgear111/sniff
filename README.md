# Sniff 🐕
**Offline AI Contribution Detection Engine for Git Repositories**

Sniff is a terminal-native AI detection system designed to analyze Git repositories and estimate the likelihood that commits or code contributions were generated or heavily assisted by AI tools.

It combines deterministic structural analysis with a local Large Language Model (GPT-2 via HuggingFace) to provide explainable AI-likelihood scoring — all within a beautiful, interactive terminal interface. **100% offline. Zero cloud APIs. Your code never leaves your machine.**

---

## 1. Problem Statement

**AI-Generated Code Transparency & Governance in Modern Development**

With the rapid rise of AI coding assistants such as GitHub Copilot and ChatGPT, developers are increasingly committing AI-generated code without fully understanding it.

This creates several risks:
- Technical debt accumulation
- Security vulnerabilities
- Loss of code ownership accountability
- Academic integrity violations
- Reduced code quality over time

Currently, Git platforms provide no structured transparency layer to detect or analyze AI-assisted contributions.

### Target Users
- DevSecOps Teams
- Enterprise Engineering Managers
- Academic Institutions
- Open Source Maintainers
- Security Auditors

### Existing Gaps
- No repository-level AI usage analytics
- No explainable AI-likelihood scoring for commits
- No structured governance tools for AI contribution transparency

---

## 2. Root Cause Analysis

AI-generated code often exhibits:
- Highly structured and formal commit messages with low linguistic entropy
- Boilerplate-heavy code patterns with repetitive variable naming
- Large bursts of code additions in physically impossible time windows
- Consistent function scaffolding (docstrings, uniform indentation, predictable naming)

Existing approaches rely on simple keyword matching (fragile) or fully black-box cloud APIs (non-transparent). Sniff is the first offline, explainable alternative.

---

## 3. Solution: Tri-Engine ML Architecture

Sniff uses a **three-signal hybrid detection pipeline** to compute a final probabilistic AI-likelihood score for every commit.

### Engine 1: Text Perplexity (NLP)
- Uses a local **HuggingFace GPT-2** model to calculate the log-probability perplexity of commit messages.
- LLMs produce mathematically "perfect" text (low perplexity). Human writing is chaotic and bursty (high perplexity).
- **Flag:** Perplexity < 30 → Score: 0.9

### Engine 2: Code AST Entropy (Structural)
- Parses code additions into a **Python Abstract Syntax Tree (AST)** to analyze structural complexity.
- Detects AI signatures: high docstring density, low lexical entropy, uniform scaffold patterns.
- Falls back to raw diff heuristics for non-Python code (React/JS/Go), detecting patterns like `useState + useEffect` bursts.
- **Flag:** Low variable uniqueness ratio → Score: 0.3–0.4

### Engine 3: Behavioral Velocity (Metadata)
- Cross-references **Lines of Code added per minute** by parsing GitPython commit timestamps.
- Flags physically impossible typing speeds (> 50 LPM).
- **Flag:** Velocity > 50 LPM → Instant +0.4 boost to final score.

### Score Aggregation
```
final_score = (text × 0.4) + (code × 0.4) + (velocity × 0.2) + amplification_boost
```
- Results in a deterministic, explainable AI-likelihood band: **Likely Human / Mixed / Likely AI-Assisted**

---

## 4. System Architecture

```
User → [sniff interactive] → Theme Selector → Repository Connect
     → Git Graph Extraction (GitPython)
     → Text Perplexity Engine (GPT-2 local)
     → AST Code Entropy Engine (Python ast)
     → Velocity Behavioral Engine (timestamps)
     → Score Aggregation → Rich Dashboard + Plotille Charts
```

Sniff is **stateless** and requires no external database. All analysis runs in-memory.

---

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| CLI Framework | Typer |
| UI & Layout | Rich (Tables/Panels) |
| ASCII Charts | Plotille |
| ASCII Typography | PyFiglet |
| Git Data | GitPython |
| NLP Model | HuggingFace Transformers (GPT-2) |
| Code Parsing | Python `ast` |
| ML Backend | PyTorch |

---

## 6. Installation

```bash
git clone https://github.com/mrgear111/sniff.git
cd sniff
python -m venv venv
source venv/bin/activate
pip install -e .
```

---

## 7. Usage

### Interactive REPL
```bash
sniff interactive
```

| Command | Description |
|---|---|
| `cd <path or url>` | Switch repo. Pastes GitHub URLs auto-clone to a local cache |
| `scan [count]` | Analyze the N most recent commits. Default: 10 |
| `stats [count]` | View contributor AI leaderboard. Default: 50 |
| `theme` | Switch syntax color theme (Dark / Light / Colorblind) |
| `clear` | Clear the terminal |
| `exit` | Quit the session |

### Headless / CI Mode
```bash
sniff scan --path /path/to/repo --json
sniff stats --path /path/to/repo --json
```

---

## 8. Disclaimer

Sniff relies on statistical ML models and behavioral heuristics. It is a powerful auditing signal, not a definitive legal claim of AI generation. Results should always be reviewed by a human auditor before action is taken.
