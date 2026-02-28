import git
from pathlib import Path

def get_repo(path: str = "."):
    try:
        return git.Repo(path)
    except git.exc.InvalidGitRepositoryError:
        return None

def get_commits(repo: git.Repo, max_count: int = 50):
    try:
        return list(repo.iter_commits(max_count=max_count))
    except (ValueError, git.exc.GitCommandError):
        # ValueError implies no commits on the reference (like 'main' doesn't exist yet)
        return []

def get_commit_diff(commit: git.Commit):
    if not commit.parents:
        return ""
    
    parent = commit.parents[0]
    diffs = parent.diff(commit, create_patch=True)
    
    added_lines = []
    for d in diffs:
        # decode diff to string
        try:
            diff_text = d.diff.decode('utf-8')
            for line in diff_text.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    added_lines.append(line[1:])
        except Exception:
            pass # ignore binary files or decode errors
            
    return "\n".join(added_lines)
