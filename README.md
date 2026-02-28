# Sniff 🐕

**Sniff** is an interactive, ML-powered CLI tool that detects AI-generated code contributions in Git repositories. It uses a tri-engine architecture (AST Entropy, LLM Perplexity, and Behavioral Velocity) to analyze commits with high accuracy and explainability.

## Key Features
- **Interactive REPL**: A Claude Code style interactive session (`sniff interactive`) with persistent state, gorgeous PyFiglet ASCII art, and dynamic syntax theming.
- **Tri-Engine ML**:
  - **Text Perplexity**: Uses a local HuggingFace GPT-2 model to flag low-entropy AI-generated commit messages and PR descriptions.
  - **Code AST Entropy**: Parses structural additions directly into Abstract Syntax Trees (AST) to detect the rigid scaffolding common to LLM outputs (e.g. Copilot).
  - **Behavioral Velocity**: Identifies impossible human typing speeds (e.g. >50 Lines Per Minute) from Git timestamps.
- **Visual Analytics**: Instant contributor leaderboards and `plotille` ASCII trend charts straight from your terminal.
- **Local-First & Private**: Analyzes code against local Git graphs without sending your proprietary IP to cloud black boxes.

## Installation
Ensure you have Python 3.10+ installed.

```bash
git clone https://github.com/[your-username]/sniff.git
cd sniff
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage
Start the interactive REPL:
```bash
sniff interactive
```

Inside the REPL, you can:
- **`cd <path or url>`**: Switch to a local repository folder, or paste a remote GitHub URL to instantly clone and cache it for analysis.
- **`scan [count]`**: Analyze the target repository's most recent commits.
- **`stats [count]`**: View the aggregated AI leaderboard for the authors in the repo.
- **`theme`**: Change the syntax UI color theme (Dark, Light, Colorblind).
- **`clear`**: Wipe the terminal.

## Headless Mode (CI/CD)
To use Sniff in an automated pipeline without the interactive REPL:
```bash
sniff scan --path /path/to/repo --json
sniff stats --path /path/to/repo --json
```

## Disclaimer
Sniff relies on statistical ML models and heuristical behavioral data. It is highly accurate, but no AI detector is perfect. Results should be used as an auditing signal rather than a definitive legal claim of academic or professional dishonesty.
