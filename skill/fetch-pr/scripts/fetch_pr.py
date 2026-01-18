#!/usr/bin/env python3
"""
PR Fetcher Script - Fetch GitHub PR data to local directory
Usage: python fetch_pr.py <pr_number> <inter_dir> [<repo_owner> <repo_name>]
"""

import os
import sys
import json
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment or gh CLI"""
    # Try environment variable first
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token

    # Try gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_repo_info() -> tuple[str, str]:
    """Get repository owner and name from git remote"""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()

        # Parse GitHub URL
        if "github.com" in url:
            if url.startswith("git@"):
                # SSH format: git@github.com:owner/repo.git
                parts = url.split(":")[1].replace(".git", "").split("/")
            else:
                # HTTPS format: https://github.com/owner/repo.git
                parts = url.split("/")[-2:]
                parts[1] = parts[1].replace(".git", "")

            return parts[0], parts[1]
    except subprocess.CalledProcessError:
        pass

    raise ValueError("Could not determine repository from git remote")


def fetch_pr_data(owner: str, repo: str, pr_number: int, token: str) -> Dict[str, Any]:
    """Fetch PR data from GitHub API"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    base_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    data = {}

    # Fetch PR info
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()
    data["pr"] = response.json()

    # Fetch PR files
    response = requests.get(f"{base_url}/files", headers=headers)
    response.raise_for_status()
    data["files"] = response.json()

    # Fetch PR commits
    response = requests.get(f"{base_url}/commits", headers=headers)
    response.raise_for_status()
    data["commits"] = response.json()

    # Fetch PR reviews
    response = requests.get(f"{base_url}/reviews", headers=headers)
    response.raise_for_status()
    data["reviews"] = response.json()

    # Fetch PR comments (issue comments)
    response = requests.get(data["pr"]["_links"]["comments"]["href"], headers=headers)
    response.raise_for_status()
    data["comments"] = response.json()

    # Fetch review comments
    response = requests.get(f"{base_url}/comments", headers=headers)
    response.raise_for_status()
    data["review_comments"] = response.json()

    return data


def save_pr_files(
    pr_data: Dict[str, Any], inter_dir: Path, owner: str, repo: str, token: str
) -> List[str]:
    """Save PR files to local directory"""
    files_dir = inter_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    headers = {"Authorization": f"token {token}"}
    saved_files = []

    for file_data in pr_data["files"]:
        filename = file_data["filename"]
        file_path = files_dir / filename

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Download file content if it exists (not deleted)
        if file_data["status"] != "removed":
            try:
                # Get the file content from the raw URL
                raw_url = file_data.get("raw_url")
                if raw_url:
                    response = requests.get(raw_url, headers=headers)
                    response.raise_for_status()

                    with open(file_path, "wb") as f:
                        f.write(response.content)

                    saved_files.append(str(file_path))
            except requests.RequestException as e:
                print(f"Warning: Could not download {filename}: {e}")

        # Save patch/diff information
        patch_path = files_dir / f"{filename}.patch"
        patch_path.parent.mkdir(parents=True, exist_ok=True)

        with open(patch_path, "w") as f:
            f.write(f"File: {filename}\n")
            f.write(f"Status: {file_data['status']}\n")
            f.write(f"Changes: +{file_data['additions']} -{file_data['deletions']}\n")
            f.write("-" * 50 + "\n")
            if file_data.get("patch"):
                f.write(file_data["patch"])

        saved_files.append(str(patch_path))

    return saved_files


def generate_status_report(
    success: bool,
    error_msg: str = "",
    pr_number: int = 0,
    files_count: int = 0,
    inter_dir: Optional[Path] = None,
) -> str:
    """Generate status report content"""
    if success:
        return f"""# fetch-pr Status Report

**Status**: ✅ SUCCESS  
**PR Number**: #{pr_number}  
**Files Downloaded**: {files_count}  
**Output Directory**: {inter_dir}  
**Timestamp**: {Path().absolute()}  

The PR has been successfully fetched and all files have been downloaded to the specified directory.
"""
    else:
        return f"""# fetch-pr Status Report

**Status**: ❌ FAILED  
**PR Number**: #{pr_number}  
**Error**: {error_msg}  
**Timestamp**: {Path().absolute()}  

The PR fetch operation failed. Please check the error message above and try again.
"""


def generate_pr_info_report(pr_data: Dict[str, Any], saved_files: List[str]) -> str:
    """Generate detailed PR information report"""
    pr = pr_data["pr"]

    report = f"""# PR #{pr["number"]}: {pr["title"]}

## Overview
- **Author**: {pr["user"]["login"]}
- **State**: {pr["state"]} 
- **Created**: {pr["created_at"]}
- **Updated**: {pr["updated_at"]}
- **Base Branch**: {pr["base"]["ref"]}
- **Head Branch**: {pr["head"]["ref"]}
- **Mergeable**: {pr.get("mergeable", "Unknown")}

## Description
{pr["body"] or "No description provided."}

## Statistics
- **Files Changed**: {len(pr_data["files"])}
- **Commits**: {len(pr_data["commits"])}
- **Additions**: {pr["additions"]}
- **Deletions**: {pr["deletions"]}
- **Reviews**: {len(pr_data["reviews"])}
- **Comments**: {len(pr_data["comments"])} issue comments, {len(pr_data["review_comments"])} review comments

## Files Changed
"""

    for file_data in pr_data["files"]:
        report += f"- `{file_data['filename']}` ({file_data['status']}) +{file_data['additions']} -{file_data['deletions']}\n"

    # Add commits section
    report += "\n## Commits\n"
    for commit in pr_data["commits"]:
        report += f"- [{commit['sha'][:8]}]({commit['html_url']}) {commit['commit']['message'].splitlines()[0]}\n"
        report += f"  *by {commit['commit']['author']['name']} on {commit['commit']['author']['date']}*\n"

    # Add reviews section if any
    if pr_data["reviews"]:
        report += "\n## Reviews\n"
        for review in pr_data["reviews"]:
            status_emoji = {
                "APPROVED": "✅",
                "CHANGES_REQUESTED": "❌",
                "COMMENTED": "💬",
            }.get(review["state"], "📝")
            report += f"- {status_emoji} **{review['user']['login']}** ({review['state']}) - {review['submitted_at']}\n"
            if review["body"]:
                report += f"  > {review['body']}\n"

    # Add comments section if any
    if pr_data["comments"]:
        report += "\n## Issue Comments\n"
        for comment in pr_data["comments"]:
            report += f"- **{comment['user']['login']}** - {comment['created_at']}\n"
            report += f"  > {comment['body'][:200]}{'...' if len(comment['body']) > 200 else ''}\n"

    # Add review comments if any
    if pr_data["review_comments"]:
        report += "\n## Review Comments\n"
        for comment in pr_data["review_comments"]:
            report += f"- **{comment['user']['login']}** on `{comment['path']}` - {comment['created_at']}\n"
            report += f"  > {comment['body'][:200]}{'...' if len(comment['body']) > 200 else ''}\n"

    report += f"\n## Downloaded Files\n"
    for file_path in saved_files:
        report += f"- {file_path}\n"

    return report


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python fetch_pr.py <pr_number> <inter_dir> [<repo_owner> <repo_name>]"
        )
        sys.exit(1)

    pr_number = int(sys.argv[1])
    inter_dir = Path(sys.argv[2])

    # Get repo info
    try:
        if len(sys.argv) >= 5:
            owner, repo = sys.argv[3], sys.argv[4]
        else:
            owner, repo = get_repo_info()
    except ValueError as e:
        error_msg = f"Repository detection failed: {e}"
        print(f"Error: {error_msg}")

        # Generate failed status report
        status_content = generate_status_report(False, error_msg, pr_number)
        with open(inter_dir / "fetch-pr_status.md", "w") as f:
            f.write(status_content)
        sys.exit(1)

    # Get GitHub token
    token = get_github_token()
    if not token:
        error_msg = "GitHub token not found. Set GITHUB_TOKEN environment variable or use 'gh auth login'"
        print(f"Error: {error_msg}")

        # Generate failed status report
        status_content = generate_status_report(False, error_msg, pr_number)
        inter_dir.mkdir(parents=True, exist_ok=True)
        with open(inter_dir / "fetch-pr_status.md", "w") as f:
            f.write(status_content)
        sys.exit(1)

    # Create output directory
    inter_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Fetching PR #{pr_number} from {owner}/{repo}...")

        # Fetch PR data
        pr_data = fetch_pr_data(owner, repo, pr_number, token)

        # Save PR files
        saved_files = save_pr_files(pr_data, inter_dir, owner, repo, token)

        # Save raw PR data as JSON
        with open(inter_dir / "pr_data.json", "w") as f:
            json.dump(pr_data, f, indent=2)

        # Generate reports
        status_content = generate_status_report(
            True, "", pr_number, len(saved_files), inter_dir
        )
        with open(inter_dir / "fetch-pr_status.md", "w") as f:
            f.write(status_content)

        pr_info_content = generate_pr_info_report(pr_data, saved_files)
        with open(inter_dir / "pr_info.md", "w") as f:
            f.write(pr_info_content)

        print(f"✅ Successfully fetched PR #{pr_number}")
        print(f"📁 Files saved to: {inter_dir}")
        print(f"📊 Status report: {inter_dir / 'fetch-pr_status.md'}")
        print(f"📋 PR info: {inter_dir / 'pr_info.md'}")

    except Exception as e:
        error_msg = f"Failed to fetch PR: {str(e)}"
        print(f"Error: {error_msg}")

        # Generate failed status report
        status_content = generate_status_report(False, error_msg, pr_number)
        with open(inter_dir / "fetch-pr_status.md", "w") as f:
            f.write(status_content)
        sys.exit(1)


if __name__ == "__main__":
    main()
