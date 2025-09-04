from __future__ import annotations

import os
import time
from typing import Any, Optional

from github import Github


def get_github(token: Optional[str] = None) -> Github:
    token = token or os.getenv("GITHUB_TOKEN")
    return Github(login_or_token=token) if token else Github()


def fetch_repo_readme(full_name: str, token: Optional[str] = None) -> dict[str, Any]:
    gh = get_github(token)
    repo = gh.get_repo(full_name)
    try:
        readme = repo.get_readme()
        content = readme.decoded_content.decode("utf-8", errors="ignore")
    except Exception:
        content = ""
    return {
        "full_name": full_name,
        "description": repo.description,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "open_issues": repo.open_issues_count,
        "default_branch": repo.default_branch,
        "homepage": repo.homepage,
        "readme": content,
        "html_url": repo.html_url,
        "fetched_at": time.time(),
    }
