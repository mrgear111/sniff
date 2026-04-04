# Sniff JS (Deployable Web Version)

This is a JavaScript web app version of Sniff, designed for recruiter demos and cloud deployment.

## What It Does
- Accepts a public GitHub repository URL
- Fetches recent commits via GitHub API
- Computes AI-likelihood signals from commit text and commit metadata
- Lets you choose offline heuristics or an Anthropic LLM tie-breaker for borderline commits
- Shows summary, commit-level results, and contributor leaderboard

## Run Locally
1. Install dependencies
```bash
cd sniff_web_js
npm install
```

2. Start app
```bash
npm run dev
```

3. Open
```text
http://localhost:8080
```

## Analysis Modes
- Offline mode uses the local heuristics only.
- LLM mode uses Anthropic only when the score is borderline.
- If no Anthropic key is provided, LLM mode falls back to offline heuristics.

## Deploy (Render)
1. Push `sniff_web_js` to GitHub.
2. Create a new Web Service on Render.
3. Set:
- Build command: `npm install`
- Start command: `npm start`
- Root Directory: `sniff_web_js`
4. Add env var (optional): `GITHUB_TOKEN`.
5. Deploy and use the generated URL.

## Deploy (Railway)
1. New project from GitHub repo.
2. Set root to `sniff_web_js`.
3. Railway auto-detects Node and runs `npm start`.
4. Add env var `GITHUB_TOKEN` if needed.

## Notes
- This JS app is intentionally separate from the Python CLI implementation.
- It supports GitHub URLs (public repos) so it works in deployed environments.
