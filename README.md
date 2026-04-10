# Sniff 🐕
**AI Contribution Detection Engine for Git Repositories (CLI + Web)**

Sniff is an AI detection system designed to analyze Git repositories and estimate the likelihood that commits or code contributions were generated or heavily assisted by AI tools.

It combines deterministic structural analysis with a local Large Language Model (GPT-2 via HuggingFace) to provide explainable AI-likelihood scoring.

You can use Sniff in two ways:
- **Python CLI** (`sniff`) for interactive terminal workflows and local/remote repo analysis
- **Web App (JavaScript)** (`sniff_web_js`) for browser-based demos and deployment

The core detection approach is shared conceptually across both experiences.

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

## 3. Solution: Six-Engine ML Architecture

Sniff uses a **hybrid detection pipeline** consisting of 6 deterministic and statistical offline engines, combined with an optional prompt-engineered Claude API tie-breaker.

### Engine 1: Text Perplexity (NLP)
- Uses a local **HuggingFace GPT-2** model to calculate the log-probability perplexity of commit messages.
- LLMs produce mathematically "perfect" text (low perplexity). Human writing is chaotic and bursty.
- **Flag:** Perplexity < 30 → Score: 0.9

### Engine 2: Code AST Entropy (Structural)
- Parses code additions into a **Python Abstract Syntax Tree (AST)** to analyze structural complexity.
- Detects AI signatures: high docstring density, low lexical entropy, uniform scaffold patterns.
- Falls back to raw diff heuristics for non-Python code (React/JS/Go), detecting patterns like `useState + useEffect` bursts.
- **Flag:** Low variable uniqueness ratio → Score: 0.3–0.4

### Engine 3: Behavioral Velocity (Metadata)
- Cross-references **Lines of Code added per minute** by parsing GitPython commit timestamps.
- Flags physically impossible typing speeds (> 50 LPM).

### Engine 4: Semantic Alignment (Embeddings)
- Uses **Sentence Transformers (`all-MiniLM-L6-v2`)** to measure the cosine similarity between the commit text and the raw code diff.
- AI often perfectly describes exactly what the code does (high similarity). Humans are notoriously lazy (low similarity).

### Engine 5: Author Baseline (Z-Scores)
- Dynamically calculates the historical commit size for the current author.
- Flags massive multi-file PRs that break their own standard deviation (z > 3.0σ).

### Engine 6: SimHash Similarity
- Computes highly optimized, locality-sensitive hashes of the code diff.
- Flags developers who are committing code that is mathematically identical (85%+) to previous diffs—a strong signal of AI template copy-pasting.

### LLM Tie-Breaker (Optional)
If the 6 local engines return a "Borderline" score (0.35 to 0.50), Sniff will securely package the commit and send it to **Anthropic Claude 4.6 Sonnet** for a deterministic tie-breaker verification.

### Score Aggregation
```
final_score = weighted_average(text, code, structural, semantic, baseline, simhash) + velocity_boost
```
- Results in a deterministic, explainable AI-likelihood band: **Likely Human / Mixed / Likely AI-Assisted**

---

## 4. System Architecture

```
┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
│  Your Terminal   │               │ Sniff ML Engines │               │   Claude Model   │
│   (Sniff CLI)    │               │    (Offline)     │               │ (Anthropic API)  │
└────────┬─────────┘               └────────┬─────────┘               └────────┬─────────┘
         │                                  │                                  │
         │ 1. Run `scan` command            │                                  │
         │─────────────────────────────────>│                                  │
         │ Payload: [Git Commits + Diffs]   │                                  │
         │                                  │ 2. Sequence Offline Analyzers    │
         │                                  │─┐                                │
         │                                  │<┘                                │
         │                                  │ 3. Score Evaluated (e.g. 0.45)   │
         │                                  │─┐                                │
         │                                  │<┘                                │
         │                                  │ 4. Ask: "Is this AI or Human?"   │
         │                                  │─────────────────────────────────>│
         │                                  │                                  │
         │                                  │ 5. "Verdict: AI-Assisted"        │
         │                                  │<┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
         │ 6. Display Dashboard Result      │                                  │
         │<┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│                                  │
         │                                  │                                  │
┌────────┴─────────┐               ┌────────┴─────────┐               ┌────────┴─────────┐
│  Your Terminal   │               │ Sniff ML Engines │               │   Claude Model   │
│   (Sniff CLI)    │               │    (Offline)     │               │ (Anthropic API)  │
└──────────────────┘               └──────────────────┘               └──────────────────┘
```


Sniff is **stateless** and requires no external database. All analysis runs in-memory.

---

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Core ML / CLI Language | Python 3.9+ |
| Web App Language | Node.js (JavaScript, Node 18+) |
| CLI Framework | Typer / Questionary |
| CLI UI & Layout | Rich (Tables/Panels) |
| Web UI/API | Express + Vanilla JS + HTML/CSS |
| ASCII Charts | Plotille / PyFiglet |
| Git Data | GitPython |
| NLP Model | HuggingFace Transformers (GPT-2) |
| Semantic Engine | Sentence Transformers |
| ML Backend | PyTorch |
| Verification API | Anthropic API |

---

## 6. Project Structure

Top-level folders:
- `sniff_cli/` - Python CLI implementation and detection engines
- `sniff_web_js/` - JavaScript web interface for browser usage and deployment
- `demo_repo/` - Sample repository for testing

---

## 7. Installation

### Python CLI

The easiest way to globally install the Sniff engine is via PyPI:
```bash
pip install sniff-cli
```

*(Optional)* To enable the LLM tie-breaker protocol, export your Anthropic key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Web App (JavaScript)

```bash
cd sniff_web_js
npm install
```

Optional environment variables:
- `GITHUB_TOKEN` (recommended for higher GitHub API rate limits)
- `ANTHROPIC_API_KEY` (only needed for LLM tie-breaker mode)

---

## 8. Usage

### CLI Usage

Sniff operates purely inside a unified, persistent terminal session. Start the engine by typing:
```bash
sniff
```

During startup, Sniff will prompt you to select your LLM settings, and then ask for the target repository. You can pass a local filepath (`.`) or a Remote GitHub URL (`https://github.com/mrgear111/sniff`).

### Interactive Commands
Once inside the `sniff>` REPL shell, type these commands natively:

| Command | Description |
|---|---|
| `scan [count]` | Analyze the N most recent commits (Default: 10). Pass `--no-llm` to bypass Anthropic for this run. |
| `stats [count]` | Analyze codebase and view the AI-Density Contributor Leaderboard. |
| `cd <path/url>` | Dynamically switch to a new local directory or remote GitHub URL workspace. |
| `clear` | Clear the terminal screen |
| `exit` | Quit the active session |

---

### Web App Usage (Browser UI)

Sniff now also includes a browser-based interface that reuses the same detection engines.

Start the web app:
```bash
cd sniff_web_js
npm run dev
```

Then open:
```text
http://localhost:8080
```

In the web UI, you can:
- Enter a public GitHub repository URL
- Set commit count to analyze
- Optionally enable LLM tie-breaker mode
- View commit-level scores and an author leaderboard in the browser

For production-style local run:
```bash
npm start
```

---

## 9. Deployment (Web App)

The web app in `sniff_web_js` is designed to be deployable (for example on Render or Railway):
- Build command: `npm install`
- Start command: `npm start`
- Root directory: `sniff_web_js`
- Recommended env var: `GITHUB_TOKEN`
- Optional env var: `ANTHROPIC_API_KEY`

## 10. Disclaimer

Sniff relies on statistical ML models and behavioral heuristics. It is a powerful auditing signal, not a definitive legal claim of AI generation. Results should always be reviewed by a human auditor before action is taken.