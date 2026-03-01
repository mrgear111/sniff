---
description: How to use the Sniff AI Detection CLI Engine
---
# Using the Sniff CLI Engine

Sniff is a terminal-native AI-likelihood detection engine that analyzes Git contributions using a hybrid mixture of 4 local algorithms (Code, Velocity, Geometry, text) combined with a Claude Sonnet API tie-breaker.

### Prerequisites
Before using Sniff, ensure you have Python 3.9+ and pip installed.
It is highly recommended to export an Anthropic API key to enable the LLM tie-breaker protocol.

```bash
# Export the key (Optional, but recommended for maximum accuracy)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 1. Installation

// turbo
```bash
pip install sniff-cli
```

### 2. Booting the Engine

To start the interactive detection session, simply run:

```bash
sniff
```

During startup, Sniff will prompt you with an interactive arrow-key selector:
1. **Enable LLM Tie-Breaker Protocol**: If you select this, Sniff will automatically check `process.env`. If no key is found, it will securely prompt you to paste it in.
2. **Pure Offline Mode**: Select this if you do not have an API key. Sniff will run entirely offline using local ML models.

### 3. Connecting to a Repository

Sniff will ask you for a repository path. You can provide one of two formats:

1. **Local Filepath:** `/Users/username/Desktop/my-project` or just press Enter for the current directory `.`.
2. **Remote GitHub URL:** `https://github.com/facebook/react`. Sniff will automatically shallow-clone the repository to test it dynamically on the fly!

### 4. Running the Analysis (Interactive Commands)

Once inside the `sniff>` REPL shell, you can manage your analysis natively without leaving the session.

#### Analyzing Commits
To scan the last N commits of the codebase and generate an AI-Likelihood verdict (0% to 100%) for each commit:

```bash
# Inside the sniff> shell
scan 20
```
This forces the engines to build a custom sliding-window baseline for every author, evaluating syntax density, boilerplate patterns, and generation speed in realtime.

#### Generating the Author Leaderboard
To see a mathematical ranking of which code contributors rely the most heavily on generative AI (highlighting the "AI Density Percentage" and assigning a "Severity Intensity Bar"):

```bash
# Inside the sniff> shell
stats 100
```

#### Changing the Target Codebase
If you want to evaluate a different repository, use the `cd` command inside the session hook to remount a new local path or remote GitHub URL:

```bash
# Inside the sniff> shell
cd https://github.com/vercel/next.js
```

### System Architecture Pipeline

The detection protocol runs every commit through a layered sequence of 6 analysis engines:

```
             [Raw Commit Data]
                    │
                    ▼
          (Local Offline Mode)
    ┌───────────────────────────────────┐
    │ 1. SimHash Similarity Engine      │
    │ 2. AST Syntax Entropy Engine      │
    │ 3. Velocity Baseline Tracker      │
    │ 4. Semantic NLP Scoring Engine    │
    │ 5. Text Perplexity Engine         │
    │ 6. Author Z-Score Baseline        │
    └─────────────────┬─────────────────┘
                      │
                      ▼
               [Final ML Score]
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
      > 0.50     0.35 - 0.50     < 0.35
   (AI-Assisted) (Borderline) (Human Written)
                      │
                      ▼
               LLM Key Active?
             ┌────────┴────────┐
            Yes                No
             ▼                 ▼
   [Anthropic API]          (Mixed)
             │
      Claude Checks
   ┌─────────┴─────────┐
 AI Hallmarks      Human Quirks
   ▼                   ▼
(AI-Assisted)     (Human Written)
```
