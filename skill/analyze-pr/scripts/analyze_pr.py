#!/usr/bin/env python3
"""
Analyze PR script - Analyzes PR changes and generates classification report
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def is_comment_line(line):
    """Detect if a diff line is a comment in C/C++ code"""
    # Remove diff prefix (+/-) and whitespace for analysis
    content = line[1:].strip() if line.startswith(("+", "-")) else line.strip()

    # Skip empty lines
    if not content:
        return False

    # Check for C/C++ style comments
    return (
        content.startswith("//")  # Single-line comment
        or content.startswith("/*")  # Multi-line comment start
        or content.startswith("*")  # Multi-line comment continuation
        or content.endswith("*/")  # Multi-line comment end
        or content == "/*"
        or content == "*/"  # Standalone comment markers
    )


def write_status_report(inter_dir, success, error_msg=None):
    """Write status report in specified format"""
    status_file = Path(inter_dir) / "analyze_pr_status.md"

    if success:
        content = "SUCCESS"
    else:
        content = f"FAIL\n{error_msg}"

    status_file.write_text(content)
    return status_file


def load_agents_config(repo_path):
    """Load AGENTS.md configuration file"""
    agents_file = Path(repo_path) / "AGENTS.md"

    if not agents_file.exists():
        raise Exception(
            f"AGENTS.md not found in repository root ({repo_path}). "
            "This file is required to define directory classifications for PR analysis. "
            "Every repository should have an AGENTS.md file with project structure definitions. "
            "Please ensure AGENTS.md exists in the repository root."
        )

    return agents_file.read_text()


def parse_agents_config(agents_content):
    """Parse AGENTS.md to extract directory and file classifications"""

    # Initialize empty classifications - no defaults
    classifications = {
        "core_components": [],
        "apis": [],
        "internal_headers": [],
        "tests": [],
        "samples": [],
        "documentation": [],
        "ci_cd": [],
        "build_system": [],
        "utilities": [],
    }

    # Parse AGENTS.md content to extract actual classifications
    lines = agents_content.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        # Look for section headers
        if "### Core Components" in line or "## Core Components" in line:
            current_section = "core_components"
        elif "### APIs" in line or "## APIs" in line:
            current_section = "apis"
        elif "### Internal Headers" in line or "## Internal Headers" in line:
            current_section = "internal_headers"
        elif "### Tests" in line or "## Tests" in line:
            current_section = "tests"
        elif "### Samples" in line or "## Samples" in line:
            current_section = "samples"
        elif "### Documentation" in line or "## Documentation" in line:
            current_section = "documentation"
        elif (
            "### CI/CD" in line
            or "## CI/CD" in line
            or "### CI" in line
            or "## CI" in line
        ):
            current_section = "ci_cd"
        elif (
            "### Build System" in line
            or "## Build System" in line
            or "### Build" in line
            or "## Build" in line
        ):
            current_section = "build_system"
        elif (
            "### Utilities" in line
            or "## Utilities" in line
            or "### Utils" in line
            or "## Utils" in line
        ):
            current_section = "utilities"
        elif line.startswith("- ") and current_section:
            # Extract directory/file pattern
            pattern = line[2:].strip()
            if pattern and current_section in classifications:
                classifications[current_section].append(pattern)

    # Check if any classifications were found
    total_patterns = sum(len(patterns) for patterns in classifications.values())
    if total_patterns == 0:
        raise Exception(
            "No directory classifications found in AGENTS.md. "
            "The file should contain sections like '### Core Components', '### APIs', etc. "
            "with directory patterns listed under each section using '- pattern' format."
        )

    return classifications


def classify_file_path(file_path, classifications):
    """Classify a file path based on the classification rules"""
    matched_categories = []

    # Normalize path for comparison
    norm_path = file_path.replace("\\", "/")

    for category, patterns in classifications.items():
        for pattern in patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                if norm_path.startswith(pattern) or f"/{pattern}" in norm_path:
                    matched_categories.append(category)
                    break
            # Handle specific file patterns
            elif norm_path.endswith(pattern) or f"/{pattern}" in norm_path:
                matched_categories.append(category)
                break
            # Handle filename patterns
            elif pattern in Path(norm_path).name:
                matched_categories.append(category)
                break

    # Special handling for documentation files
    if norm_path.endswith(".md") and "documentation" not in matched_categories:
        matched_categories.append("documentation")

    # If no classification found, mark as 'other'
    if not matched_categories:
        matched_categories = ["other"]

    return matched_categories


def validate_classifications(file_classifications, repo_path):
    """Validate that all files can be classified, stop if any can't be"""
    unclassified_files = []

    for file_path, classifications in file_classifications.items():
        if classifications == ["other"]:
            unclassified_files.append(file_path)

    if unclassified_files:
        error_msg = (
            f"Cannot classify the following files using AGENTS.md information:\n"
            + "\n".join(f"  - {f}" for f in unclassified_files[:10])  # Show first 10
            + ("\n  - ..." if len(unclassified_files) > 10 else "")
            + f"\n\nPlease update AGENTS.md in {repo_path} to include directory patterns "
            + "that cover these files, or provide clarification on how to classify them."
        )
        raise Exception(error_msg)


def parse_diff_file(diff_path):
    """Parse the diff file to extract changed files and statistics"""
    if not diff_path.exists():
        raise Exception(f"Diff file not found: {diff_path}")

    diff_content = diff_path.read_text()

    changed_files = []
    lines_added = 0
    lines_deleted = 0

    current_file = None

    for line in diff_content.split("\n"):
        # Parse file headers
        if line.startswith("diff --git"):
            # Extract file path
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3][2:]  # Remove 'b/' prefix
                changed_files.append(current_file)

        # Count added/deleted lines (excluding comments and whitespace-only)
        elif line.startswith("+") and not line.startswith("+++"):
            if (
                not is_comment_line(line) and line[1:].strip()
            ):  # Skip comments and empty lines
                lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            if (
                not is_comment_line(line) and line[1:].strip()
            ):  # Skip comments and empty lines
                lines_deleted += 1

    return {
        "files": list(set(changed_files)),  # Remove duplicates
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
    }


def analyze_file_types(files):
    """Analyze the types of files changed"""
    file_types = defaultdict(int)

    for file_path in files:
        ext = Path(file_path).suffix.lower()
        if ext:
            file_types[ext] = file_types.get(ext, 0) + 1
        else:
            file_types["no_extension"] = file_types.get("no_extension", 0) + 1

    return dict(file_types)


def is_code_file(file_path):
    """Determine if a file is considered 'code' based on extension"""
    code_extensions = {".c", ".h", ".cc"}
    return Path(file_path).suffix.lower() in code_extensions


def classify_pr_change_type(files):
    """Classify PR as CODE CHANGE or NON-CODE CHANGE based on modified files"""
    for file_path in files:
        if is_code_file(file_path):
            return "CODE CHANGE"
    return "NON-CODE CHANGE"


def assess_risk_level(classifications, diff_stats, files, file_classifications):
    """Assess the risk level based on the specified rules"""
    risk_score = 0

    # Check file types to determine base risk
    has_code_files = any(is_code_file(f) for f in files)
    has_core_components = "core_components" in classifications

    # Document modifications only → low risk
    only_docs = all(
        f.endswith(".md")
        or any("documentation" in cats for cats in file_classifications.get(f, []))
        for f in files
    )

    if only_docs:
        risk_score = 1  # Low risk

    # Core components code (including headers) modified → high risk
    elif has_core_components and has_code_files:
        risk_score = 6  # High risk

    # Test cases, samples, utilities only → low risk
    elif all(
        any(
            cat in ["tests", "samples", "utilities"]
            for cat in file_classifications.get(f, [])
        )
        for f in files
    ):
        risk_score = 1  # Low risk

    # Build system, CI only → medium risk
    elif all(
        any(cat in ["build_system", "ci_cd"] for cat in file_classifications.get(f, []))
        for f in files
    ):
        risk_score = 3  # Medium risk

    # Large amount of code modified → high risk
    total_changes = diff_stats["lines_added"] + diff_stats["lines_deleted"]
    if total_changes > 500 and has_code_files:
        risk_score = max(risk_score, 6)  # High risk
    elif total_changes > 200 and has_code_files:
        risk_score = max(risk_score, 4)  # Medium-high risk

    # Additional risk factors
    if "core_components" in classifications:
        risk_score += 2
    if "apis" in classifications:
        risk_score += 1
    if "build_system" in classifications:
        risk_score += 1

    # Determine risk level
    if risk_score >= 5:
        return "HIGH", risk_score
    elif risk_score >= 3:
        return "MEDIUM", risk_score
    else:
        return "LOW", risk_score


def load_template():
    """Load the analysis report template"""
    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    template_path = skill_dir / "assets" / "analysis_template.md"

    if template_path.exists():
        return template_path.read_text()
    else:
        # Fallback template
        return """# Pull Request Analysis Report

## PR Summary
- **PR Number**: {pr_number}
- **Analysis Date**: {analysis_date}
- **Total Files Changed**: {total_files}
- **Lines Added**: {lines_added}
- **Lines Deleted**: {lines_deleted}

## Change Type Classification
**{change_type}**

## Change Classification

{classification_summary}

### Detailed File Classification

{detailed_classification}

## Impact Assessment

### Risk Level: {risk_level}
**Risk Score**: {risk_score}

{risk_assessment}

### Affected Components

{affected_components}

## Code Quality Analysis

### File Types Modified
{file_types}

### Change Patterns
{change_patterns}

## Recommendations

{recommendations}

---
*Analysis generated by analyze-pr skill*"""


def format_classification_summary(file_classifications):
    """Format the classification summary section"""
    category_counts = defaultdict(int)

    for classifications in file_classifications.values():
        for category in classifications:
            category_counts[category] += 1

    if not category_counts:
        return "No files classified."

    summary_lines = []
    for category, count in sorted(category_counts.items()):
        category_name = category.replace("_", " ").title()
        summary_lines.append(f"- **{category_name}**: {count} file(s)")

    return "\n".join(summary_lines)


def format_detailed_classification(file_classifications):
    """Format the detailed file classification section"""
    if not file_classifications:
        return "No files to classify."

    # Group files by classification
    classification_groups = defaultdict(list)

    for file_path, classifications in file_classifications.items():
        for category in classifications:
            classification_groups[category].append(file_path)

    detailed_lines = []

    for category, files in sorted(classification_groups.items()):
        category_name = category.replace("_", " ").title()
        detailed_lines.append(f"#### {category_name}")
        for file_path in sorted(files):
            detailed_lines.append(f"- `{file_path}`")
        detailed_lines.append("")

    return "\n".join(detailed_lines)


def format_file_types(file_types):
    """Format the file types section"""
    if not file_types:
        return "No file type information available."

    type_lines = []
    for ext, count in sorted(file_types.items(), key=lambda x: -x[1]):
        if ext == "no_extension":
            type_lines.append(f"- Files without extension: {count}")
        else:
            type_lines.append(f"- `{ext}`: {count} file(s)")

    return "\n".join(type_lines)


def generate_recommendations(classifications, risk_level, file_types):
    """Generate recommendations based on the analysis"""
    recommendations = []

    if risk_level == "HIGH":
        recommendations.append("🔴 **High Risk Changes Detected**")
        recommendations.append("- Conduct thorough code review")
        recommendations.append("- Ensure comprehensive test coverage")
        recommendations.append("- Consider breaking into smaller PRs")

    if "core_components" in classifications:
        recommendations.append("⚠️ **Core Component Changes**")
        recommendations.append("- Review impact on system stability")
        recommendations.append("- Verify backward compatibility")

    if "apis" in classifications:
        recommendations.append("📋 **API Changes Detected**")
        recommendations.append("- Review API documentation updates")
        recommendations.append("- Check for breaking changes")
        recommendations.append("- Validate client compatibility")

    if "tests" not in classifications and risk_level in ["HIGH", "MEDIUM"]:
        recommendations.append("🧪 **Missing Test Updates**")
        recommendations.append("- Consider adding tests for new functionality")
        recommendations.append("- Update existing tests if behavior changed")

    if not recommendations:
        recommendations.append("✅ **Low Risk Changes**")
        recommendations.append("- Standard review process should be sufficient")

    return "\n".join(recommendations)


def generate_analysis_report(
    pr_number, diff_stats, file_classifications, repo_path, inter_dir
):
    """Generate the final analysis report"""

    # Calculate aggregate classifications
    all_classifications = set()
    for classifications in file_classifications.values():
        all_classifications.update(classifications)

    # Determine change type (CODE CHANGE or NON-CODE CHANGE)
    change_type = classify_pr_change_type(diff_stats["files"])

    # Assess risk level with new rules
    risk_level, risk_score = assess_risk_level(
        all_classifications, diff_stats, diff_stats["files"], file_classifications
    )

    # Analyze file types
    file_types = analyze_file_types(diff_stats["files"])

    # Load template
    template = load_template()

    # Prepare template variables
    template_vars = {
        "pr_number": pr_number,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_files": len(diff_stats["files"]),
        "lines_added": diff_stats["lines_added"],
        "lines_deleted": diff_stats["lines_deleted"],
        "change_type": change_type,
        "classification_summary": format_classification_summary(file_classifications),
        "detailed_classification": format_detailed_classification(file_classifications),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_assessment": f"Based on the analysis, this PR has a **{risk_level}** risk level (score: {risk_score}).",
        "affected_components": ", ".join(
            [c.replace("_", " ").title() for c in sorted(all_classifications)]
        ),
        "file_types": format_file_types(file_types),
        "change_patterns": f"Total of {len(diff_stats['files'])} files modified across {len(all_classifications)} component categories.",
        "recommendations": generate_recommendations(
            all_classifications, risk_level, file_types
        ),
    }

    # Fill template
    content = template.format(**template_vars)

    # Write analysis report
    analysis_file = Path(inter_dir) / "analysis.md"
    analysis_file.write_text(content)

    return analysis_file


def main():
    parser = argparse.ArgumentParser(
        description="Analyze GitHub PR changes and generate classification report"
    )
    parser.add_argument("pr_number", type=int, help="Pull request number")
    parser.add_argument(
        "inter_dir",
        help="Directory containing report.md and changes.diff from fetch-pr",
    )
    parser.add_argument(
        "--repo_path",
        default=".",
        help="Path to the git repository (default: current directory)",
    )

    args = parser.parse_args()

    # Ensure inter_dir exists and contains required files
    inter_dir = Path(args.inter_dir)
    if not inter_dir.exists():
        print(f"❌ Inter directory does not exist: {inter_dir}")
        sys.exit(1)

    report_file = inter_dir / "report.md"
    diff_file = inter_dir / "changes.diff"

    try:
        # Validate required files exist
        if not report_file.exists():
            raise Exception(f"Required file not found: {report_file}")
        if not diff_file.exists():
            raise Exception(f"Required file not found: {diff_file}")

        # Load AGENTS.md configuration
        repo_path = Path(args.repo_path).resolve()
        print("Loading AGENTS.md configuration...")
        agents_content = load_agents_config(repo_path)
        classifications = parse_agents_config(agents_content)

        # Parse diff file
        print("Parsing diff file...")
        diff_stats = parse_diff_file(diff_file)

        # Classify all changed files
        print("Classifying changed files...")
        file_classifications = {}
        for file_path in diff_stats["files"]:
            file_classifications[file_path] = classify_file_path(
                file_path, classifications
            )

        # Validate that all files can be classified - stop if any can't be
        print("Validating file classifications...")
        validate_classifications(file_classifications, repo_path)

        # Generate analysis report
        print("Generating analysis report...")
        analysis_file = generate_analysis_report(
            args.pr_number, diff_stats, file_classifications, repo_path, inter_dir
        )

        # Write success status
        status_file = write_status_report(inter_dir, True)

        print(f"✅ Analysis completed successfully!")
        print(f"   Status: {status_file}")
        print(f"   Analysis: {analysis_file}")

    except Exception as e:
        # Write failure status
        status_file = write_status_report(inter_dir, False, str(e))
        print(f"❌ Analysis failed: {e}")
        print(f"   Status: {status_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
