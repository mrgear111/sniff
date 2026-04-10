function parseGitHubRepoUrl(input) {
  const raw = (input || "").trim();

  if (!raw) {
    throw new Error("Repository URL is required");
  }

  const sshMatch = raw.match(/^git@github\.com:([^/]+)\/([^/]+?)(?:\.git)?$/i);
  if (sshMatch) {
    return { owner: sshMatch[1], repo: sshMatch[2] };
  }

  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("Please provide a valid GitHub repository URL");
  }

  if (!/github\.com$/i.test(url.hostname)) {
    throw new Error("Only github.com repositories are supported in the JS web app");
  }

  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length < 2) {
    throw new Error("Repository URL must look like https://github.com/owner/repo");
  }

  const owner = parts[0];
  const repo = parts[1].replace(/\.git$/i, "");

  return { owner, repo };
}

async function githubFetch(path, token) {
  const headers = {
    Accept: "application/vnd.github+json",
    "User-Agent": "sniff-web-js"
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`https://api.github.com${path}`, { headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`GitHub API failed (${response.status}): ${body.slice(0, 200)}`);
  }

  return response.json();
}

async function fetchCommits(owner, repo, count, token) {
  return githubFetch(`/repos/${owner}/${repo}/commits?per_page=${count}`, token);
}

async function fetchCommitDetail(owner, repo, sha, token) {
  return githubFetch(`/repos/${owner}/${repo}/commits/${sha}`, token);
}

module.exports = {
  parseGitHubRepoUrl,
  fetchCommits,
  fetchCommitDetail
};
