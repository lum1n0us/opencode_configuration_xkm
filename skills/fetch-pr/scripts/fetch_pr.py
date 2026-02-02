#!/usr/bin/env python3
"""
Fetch PR script - Downloads PR metadata, comments, and diff from GitHub
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=True,
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        raise Exception(f"Command failed: {cmd}\nError: {e.stderr}")


def write_status_report(inter_dir, success, error_msg=None):
    """Write status report in new format"""
    status_file = Path(inter_dir) / "fetch-pr_status.md"

    if success:
        content = "SUCCESS"
    else:
        content = f"FAIL\n{error_msg}"

    status_file.write_text(content)
    return status_file


def checkout_pr(repo_path, pr_number):
    """Checkout PR to local branch using gh pr checkout and rename to pr/<pr-number>"""
    print(f"Checking out PR #{pr_number}...")

    # First checkout the PR (this creates a branch with the original name)
    cmd = f"gh pr checkout {pr_number}"
    run_command(cmd, cwd=repo_path, capture_output=False)

    # Get the current branch name that was created
    current_branch = run_command("git branch --show-current", cwd=repo_path)

    # Define the target branch name
    target_branch = f"pr/{pr_number}"

    # If the current branch is not already the target name, rename it
    if current_branch != target_branch:
        print(f"Renaming branch from '{current_branch}' to '{target_branch}'...")

        # Check if target branch already exists and delete it if so
        try:
            run_command(f"git branch -D {target_branch}", cwd=repo_path)
            print(f"Deleted existing branch '{target_branch}'")
        except:
            # Branch doesn't exist, which is fine
            pass

        # Rename current branch to target name
        run_command(f"git branch -m {target_branch}", cwd=repo_path)


def fetch_pr_metadata(repo_path, pr_number):
    """Fetch PR metadata using gh CLI"""
    cmd = f"gh pr view {pr_number} --json number,title,body,state,author,createdAt,updatedAt,url,headRefName,baseRefName,mergeable"
    result = run_command(cmd, cwd=repo_path)
    if result is None:
        raise Exception("Failed to fetch PR metadata")
    return json.loads(result)


def fetch_pr_comments(repo_path, pr_number):
    """Fetch PR comments using gh CLI"""
    # Get review comments
    try:
        review_comments_cmd = f"gh api repos/:owner/:repo/pulls/{pr_number}/comments"
        result = run_command(review_comments_cmd, cwd=repo_path)
        review_comments = json.loads(result) if result else []
    except:
        review_comments = []

    # Get issue comments (general PR comments)
    try:
        issue_comments_cmd = f"gh api repos/:owner/:repo/issues/{pr_number}/comments"
        result = run_command(issue_comments_cmd, cwd=repo_path)
        issue_comments = json.loads(result) if result else []
    except:
        issue_comments = []

    # Get review summaries
    try:
        reviews_cmd = f"gh api repos/:owner/:repo/pulls/{pr_number}/reviews"
        result = run_command(reviews_cmd, cwd=repo_path)
        reviews = json.loads(result) if result else []
    except:
        reviews = []

    return {
        "review_comments": review_comments,
        "issue_comments": issue_comments,
        "reviews": reviews,
    }


def fetch_pr_diff(repo_path, pr_number):
    """Fetch PR diff using gh CLI"""
    cmd = f"gh pr diff {pr_number}"
    result = run_command(cmd, cwd=repo_path)
    return result if result is not None else ""


def load_template():
    """Load the report template"""
    # Get the script directory to locate template
    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    template_path = skill_dir / "assets" / "report_template.md"

    if template_path.exists():
        return template_path.read_text()
    else:
        # Fallback template if file doesn't exist
        return """# Pull Request #{pr_number}: {title}

## Metadata
- **Author**: {author}
- **State**: {state}
- **URL**: {url}
- **Branch**: {head_branch} → {base_branch}
- **Mergeable**: {mergeable}
- **Created**: {created_at}
- **Updated**: {updated_at}

## Description
{description}

{reviews_section}

{general_comments_section}

{code_comments_section}"""


def format_reviews_section(reviews):
    """Format the reviews section"""
    if not reviews:
        return ""

    content = "## Reviews\n\n"
    for review in reviews:
        if review["state"] in ["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]:
            review_date = datetime.fromisoformat(
                review["submitted_at"].replace("Z", "+00:00")
            ).strftime("%Y-%m-%d %H:%M:%S UTC")
            content += f"### {review['user']['login']} - {review['state']}\n"
            content += f"*{review_date}*\n\n"
            if review.get("body"):
                content += f"{review['body']}\n\n"
    return content


def format_general_comments_section(comments):
    """Format the general comments section"""
    if not comments:
        return ""

    content = "## General Comments\n\n"
    for comment in comments:
        comment_date = datetime.fromisoformat(
            comment["created_at"].replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
        content += f"### {comment['user']['login']}\n"
        content += f"*{comment_date}*\n\n"
        content += f"{comment['body']}\n\n"
    return content


def format_code_comments_section(comments):
    """Format the code review comments section"""
    if not comments:
        return ""

    content = "## Code Review Comments\n\n"
    for comment in comments:
        comment_date = datetime.fromisoformat(
            comment["created_at"].replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
        content += f"### {comment['user']['login']} on {comment['path']}\n"
        content += f"*{comment_date} - Line {comment.get('line', comment.get('original_line', 'N/A'))}*\n\n"
        content += f"{comment['body']}\n\n"
    return content


def generate_markdown_report(metadata, comments, inter_dir):
    """Generate a human-readable markdown report using template"""
    report_file = Path(inter_dir) / "report.md"

    # Format creation and update dates
    created_at = datetime.fromisoformat(
        metadata["createdAt"].replace("Z", "+00:00")
    ).strftime("%Y-%m-%d %H:%M:%S UTC")
    updated_at = datetime.fromisoformat(
        metadata["updatedAt"].replace("Z", "+00:00")
    ).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Load template
    template = load_template()

    # Format sections
    reviews_section = format_reviews_section(comments["reviews"])
    general_comments_section = format_general_comments_section(
        comments["issue_comments"]
    )
    code_comments_section = format_code_comments_section(comments["review_comments"])

    # Fill template
    content = template.format(
        pr_number=metadata["number"],
        title=metadata["title"],
        author=metadata["author"]["login"],
        state=metadata["state"],
        url=metadata["url"],
        head_branch=metadata["headRefName"],
        base_branch=metadata["baseRefName"],
        mergeable=metadata.get("mergeable", "Unknown"),
        created_at=created_at,
        updated_at=updated_at,
        description=metadata.get("body", "No description provided."),
        reviews_section=reviews_section,
        general_comments_section=general_comments_section,
        code_comments_section=code_comments_section,
    )

    report_file.write_text(content)
    return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GitHub PR information and generate reports"
    )
    parser.add_argument("pr_number", type=int, help="Pull request number")
    parser.add_argument(
        "inter_dir", help="Directory to store temporary files and reports"
    )
    parser.add_argument(
        "--repo_path",
        default=".",
        help="Path to the git repository (default: current directory)",
    )

    args = parser.parse_args()

    # Ensure inter_dir exists
    inter_dir = Path(args.inter_dir)
    inter_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Validate that we're in a git repo and gh is available
        repo_path = Path(args.repo_path).resolve()
        if not (repo_path / ".git").exists():
            raise Exception(f"Not a git repository: {repo_path}")

        # Check if gh CLI is available
        run_command("gh --version")

        # Check if we're authenticated with gh
        run_command("gh auth status")

        # Checkout PR to local
        checkout_pr(repo_path, args.pr_number)

        # Fetch PR metadata
        print(f"Fetching PR #{args.pr_number} metadata...")
        metadata = fetch_pr_metadata(repo_path, args.pr_number)

        # Fetch PR comments
        print("Fetching PR comments...")
        comments = fetch_pr_comments(repo_path, args.pr_number)

        # Fetch PR diff
        print("Fetching PR diff...")
        diff = fetch_pr_diff(repo_path, args.pr_number)

        # Write diff file
        diff_file = inter_dir / "changes.diff"
        diff_file.write_text(diff)

        # Generate markdown report
        print("Generating markdown report...")
        report_file = generate_markdown_report(metadata, comments, inter_dir)

        # Write success status
        status_file = write_status_report(inter_dir, True)

        print(f"✅ Success! Files generated:")
        print(f"   Status: {status_file}")
        print(f"   Report: {report_file}")
        print(f"   Diff: {diff_file}")

    except Exception as e:
        # Write failure status
        status_file = write_status_report(inter_dir, False, str(e))
        print(f"❌ Failed: {e}")
        print(f"   Status: {status_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
