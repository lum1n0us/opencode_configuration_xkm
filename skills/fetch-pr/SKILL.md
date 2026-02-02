---
name: fetch-pr
description: Fetch GitHub Pull Request metadata, comments, and diff files with local checkout. Use when Claude needs to analyze, review, or work with GitHub PR information including PR details, review comments, general comments, and code changes. Automatically checks out PR locally and generates structured reports using templates.
---

# Fetch PR

## Overview

This skill fetches comprehensive GitHub Pull Request information, checks out the PR locally, and generates structured reports. It retrieves PR metadata, all types of comments, and code changes, then outputs them in organized formats for analysis and review using a customizable template system.

## Quick Start

Use the `fetch_pr.py` script to download PR information and checkout locally:

```bash
python scripts/fetch_pr.py <pr_number> <output_directory> [--repo_path <path>]
```

**Parameters:**
- `pr_number`: GitHub PR number to fetch
- `output_directory`: Directory to store all output files
- `--repo_path`: Path to git repository (defaults to current directory)

**Requirements:**
- GitHub CLI (`gh`) must be installed and authenticated
- Must be run from within a git repository or specify `--repo_path`

## Key Features

### 1. Local PR Checkout
The script automatically checks out the PR branch locally using `gh pr checkout` and renames it to `pr/<pr-number>` for consistent branch naming, allowing immediate code inspection and testing.

### 2. Template-Based Reports
Uses a customizable markdown template (`assets/report_template.md`) for consistent report formatting. The template supports placeholders for all PR metadata and comment sections.

### 3. Structured Status Reporting
Status reports follow a specific format for easy parsing by other tools.

## Output Files

The script generates three files in the specified output directory:

### 1. Status Report (`fetch-pr_status.md`)
**Success format:**
```
SUCCESS
```

**Failure format:**
```
FAIL
Error description here
Additional error details...
```

### 2. Human-Readable Report (`report.md`)
Comprehensive markdown report generated from template containing:
- **Metadata**: Author, state, branch info, creation/update dates
- **Description**: Full PR description
- **Reviews**: Approval/rejection summaries with dates
- **General Comments**: Issue-level comments
- **Code Review Comments**: Line-specific review comments with file paths

### 3. Code Changes (`changes.diff`)
Complete diff in unified format showing all modifications made in the PR.

## Template Customization

The report template is located at `assets/report_template.md` and supports these placeholders:

**Metadata placeholders:**
- `{pr_number}`, `{title}`, `{author}`, `{state}`
- `{url}`, `{head_branch}`, `{base_branch}`, `{mergeable}`
- `{created_at}`, `{updated_at}`, `{description}`

**Section placeholders:**
- `{reviews_section}` - Formatted review summaries
- `{general_comments_section}` - General PR comments
- `{code_comments_section}` - Line-specific code comments

## Usage Examples

**Basic usage with checkout:**
```bash
python scripts/fetch_pr.py 123 ./pr_analysis
```

**Fetch PR from different repository:**
```bash
python scripts/fetch_pr.py 456 ./review_data --repo_path /path/to/repo
```

**Batch processing multiple PRs:**
```bash
for pr in 100 101 102; do
  python scripts/fetch_pr.py $pr ./prs/pr_$pr
done
```

## Error Handling

The script validates:
- Git repository existence and accessibility
- GitHub CLI installation and authentication
- PR existence, accessibility, and checkout capability
- Network connectivity and API access

All errors are captured in the status report with descriptive messages for easy troubleshooting.
