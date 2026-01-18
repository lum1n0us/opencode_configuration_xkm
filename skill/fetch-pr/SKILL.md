---
name: fetch-pr
description: Fetch GitHub Pull Request data and files to local directory for offline analysis. Use when ai-assistant needs to download PR files, metadata, reviews, and comments for code review preparation, local testing, or detailed analysis. Supports automatic repository detection or manual specification. Generates status reports and human-readable PR summaries.
compatibility: opencode
metadata:
  version: "1.0"
---

# Fetch PR

## Overview

This skill fetches complete GitHub Pull Request data to a local directory, including all changed files, metadata, reviews, and comments. Perfect for offline code review preparation and local testing scenarios.

## Quick Start

Use the main fetch script with PR number and output directory:

```bash
python scripts/fetch_pr.py <pr_number> <inter_dir> [<repo_owner> <repo_name>]
```

### Parameters
- `pr_number`: GitHub PR number to fetch
- `inter_dir`: Local directory to store all PR data and files
- `repo_owner` (optional): Repository owner/organization
- `repo_name` (optional): Repository name

If owner/repo not provided, automatically detects from git remote

### Authentication
Requires GitHub authentication via:
- `GITHUB_TOKEN` or `GH_TOKEN` environment variable
- GitHub CLI (`gh auth login`)

## Workflow

1. **Repository Detection**: Automatically identifies repo from git remote or uses provided parameters
2. **Authentication Check**: Verifies GitHub token availability
3. **Data Fetching**: Downloads PR metadata, files, commits, reviews, and comments
4. **File Storage**: Saves changed files and patch information to `files/` subdirectory
5. **Report Generation**: Creates status and detailed info reports

## Output Structure

The skill creates the following in your specified `inter_dir`:

```
inter_dir/
├── fetch-pr_status.md          # Success/failure status report
├── pr_info.md                  # Human-readable PR summary
├── pr_data.json                # Raw API data (JSON)
└── files/                      # Changed files and patches
    ├── path/to/file.py         # Actual file contents
    ├── path/to/file.py.patch   # Patch/diff information
    └── ...
```

### Status Report (`fetch-pr_status.md`)
Simple success/fail indicator with error details if applicable.

### PR Info Report (`pr_info.md`)
Comprehensive human-readable summary including:
- PR metadata (author, dates, branches, merge status)
- Description and statistics
- File changes with addition/deletion counts
- Commit history with authors and messages
- Reviews with status and comments
- All PR discussion comments
- List of downloaded files

## Usage Examples

### Basic Usage (Auto-detect repo)
```bash
cd my-project
python scripts/fetch_pr.py 123 ./pr-123-review
```

### Specify Repository
```bash
python scripts/fetch_pr.py 456 ./analysis/pr-456 facebook react
```

### With Environment Token
```bash
export GITHUB_TOKEN="ghp_xxx"
python scripts/fetch_pr.py 789 /tmp/pr-data
```

## Error Handling

The skill handles common failure scenarios:
- Missing GitHub authentication
- Invalid PR numbers
- Network connectivity issues
- Repository detection failures
- API rate limit exceeded

All errors are captured in the status report with actionable error messages.

## References

- **GitHub API**: See `references/github_api.md` for API endpoint details and authentication methods
- **Report Templates**: See `references/report_templates.md` for output format specifications

## Notes

- Files marked as "removed" in the PR are not downloaded, but their patch information is saved
- Large files may take longer to download depending on network speed
- The skill respects GitHub API rate limits (5,000 requests/hour for authenticated users)
- All timestamps are preserved from GitHub API responses