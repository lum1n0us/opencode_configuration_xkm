# Report Templates

## Status Report Template (`fetch-pr_status.md`)

### Success Format
```markdown
# fetch-pr Status Report

**Status**: ✅ SUCCESS  
**PR Number**: #{pr_number}  
**Files Downloaded**: {files_count}  
**Output Directory**: {output_path}  
**Timestamp**: {timestamp}  

The PR has been successfully fetched and all files have been downloaded to the specified directory.
```

### Failure Format
```markdown
# fetch-pr Status Report

**Status**: ❌ FAILED  
**PR Number**: #{pr_number}  
**Error**: {error_message}  
**Timestamp**: {timestamp}  

The PR fetch operation failed. Please check the error message above and try again.
```

## PR Info Report Template (`pr_info.md`)

### Structure
1. **Overview** - Basic PR metadata (author, state, dates, branches)
2. **Description** - PR body/description 
3. **Statistics** - Files changed, commits, additions/deletions, review counts
4. **Files Changed** - List of modified files with change counts
5. **Commits** - Commit history with messages and authors
6. **Reviews** - Review status and comments (if any)
7. **Issue Comments** - General PR discussion (if any)
8. **Review Comments** - Line-specific code comments (if any)
9. **Downloaded Files** - List of locally saved files

### Formatting Notes
- Use emojis for review status (✅ approved, ❌ changes requested, 💬 commented)
- Truncate long comments to 200 characters with "..."
- Include clickable links where applicable
- Show file paths relative to the inter-dir