# GitHub API Reference for PR Fetching

## Authentication

The skill supports multiple authentication methods:

1. **Environment Variables**:
   - `GITHUB_TOKEN`
   - `GH_TOKEN`

2. **GitHub CLI**: If `gh` CLI is installed and authenticated, the skill will use `gh auth token`

## Required API Endpoints

### Pull Request Data
- `GET /repos/{owner}/{repo}/pulls/{pull_number}` - Basic PR information
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/files` - Changed files
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits` - PR commits
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews` - PR reviews
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/comments` - Review comments

### Comments
- `GET /repos/{owner}/{repo}/issues/{issue_number}/comments` - Issue comments (from PR._links.comments.href)

## API Rate Limits

- Authenticated requests: 5,000 per hour
- The skill fetches multiple endpoints, so plan accordingly
- Consider caching for frequently accessed PRs

## Repository Detection

The skill automatically detects the repository from git remote origin:
- SSH format: `git@github.com:owner/repo.git`
- HTTPS format: `https://github.com/owner/repo.git`

Can be overridden by providing owner and repo as arguments.

## File Download

Files are downloaded using the `raw_url` field from the files API response.
Patch information is saved separately for each file showing the diff.