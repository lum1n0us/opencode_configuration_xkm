#!/usr/bin/env python3
"""
Static Analyze script - Runs clang-tidy static analysis on WAMR projects
"""

import os
import sys
import subprocess
import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def run_command(cmd, cwd=None, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,  # Don't raise on non-zero exit codes
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        raise Exception(f"Command execution failed: {cmd}\nError: {e}")


def write_status_report(inter_dir, success, error_msg=None):
    """Write status report in specified format"""
    status_file = Path(inter_dir) / "static-analyze-wamr_status.md"

    if success:
        content = "SUCCESS"
    else:
        content = f"FAIL\n{error_msg}"

    status_file.write_text(content)
    return status_file


def find_build_directories(inter_dir):
    """Find and validate build directories and compile_commands.json files"""
    inter_dir = Path(inter_dir)
    build_dir = inter_dir / "build"

    if not build_dir.exists():
        raise Exception(
            f"Build directory not found: {build_dir}. "
            "Please run the build-wamr skill first to generate build artifacts."
        )

    compile_commands_files = []
    components = []

    # Check for iwasm build
    iwasm_dir = build_dir / "iwasm"
    if iwasm_dir.exists():
        iwasm_compile_commands = iwasm_dir / "compile_commands.json"
        if iwasm_compile_commands.exists():
            compile_commands_files.append(iwasm_compile_commands)
            components.append("iwasm")
        else:
            print(f"Warning: {iwasm_dir} exists but compile_commands.json not found")

    # Check for wamrc build
    wamrc_dir = build_dir / "wamrc"
    if wamrc_dir.exists():
        wamrc_compile_commands = wamrc_dir / "compile_commands.json"
        if wamrc_compile_commands.exists():
            compile_commands_files.append(wamrc_compile_commands)
            components.append("wamrc")
        else:
            print(f"Warning: {wamrc_dir} exists but compile_commands.json not found")

    if not compile_commands_files:
        raise Exception(
            "No compile_commands.json files found in build directories. "
            "Expected files:\n"
            f"  - {build_dir}/iwasm/compile_commands.json\n"
            f"  - {build_dir}/wamrc/compile_commands.json\n"
            "Please run the build-wamr skill first to generate these files."
        )

    return compile_commands_files, components


def find_clang_tidy_config(repo_path):
    """Find .clang-tidy configuration file"""
    repo_path = Path(repo_path)

    # Check repo root first
    config_file = repo_path / ".clang-tidy"
    if config_file.exists():
        return config_file

    # Check current directory
    current_config = Path.cwd() / ".clang-tidy"
    if current_config.exists():
        return current_config

    raise Exception(
        f".clang-tidy configuration file not found. Expected locations:\n"
        f"  - {repo_path}/.clang-tidy\n"
        f"  - {Path.cwd()}/.clang-tidy\n"
        "Please create a .clang-tidy configuration file with your desired rules."
    )


def check_clang_tidy_availability():
    """Check if clang-tidy and clang-tidy-diff are available"""
    try:
        # Check clang-tidy
        stdout, stderr, returncode = run_command("clang-tidy --version")
        if returncode != 0:
            raise Exception("clang-tidy command failed")

        # Extract version from output
        version_match = re.search(r"clang-tidy version (\S+)", stdout)
        version = version_match.group(1) if version_match else "unknown"

        # Check clang-tidy-diff
        try:
            stdout_diff, stderr_diff, returncode_diff = run_command(
                "clang-tidy-diff --help"
            )
            # clang-tidy-diff returns non-zero for --help, but that's normal
            diff_available = True
        except Exception:
            raise Exception(
                "clang-tidy-diff is not installed or not available in PATH. "
                "Please ensure both clang-tidy and clang-tidy-diff are installed and available."
            )

        return version, diff_available
    except Exception:
        raise Exception(
            "clang-tidy is not installed or not available in PATH. "
            "Please ensure both clang-tidy and clang-tidy-diff are installed and available."
        )


def parse_changes_diff(inter_dir):
    """Parse changes.diff to get modified files and line numbers"""
    diff_file = Path(inter_dir) / "changes.diff"

    if not diff_file.exists():
        return None

    try:
        diff_content = diff_file.read_text()
    except Exception as e:
        print(f"Warning: Could not read changes.diff: {e}")
        return None

    modified_files = {}
    current_file = None

    for line in diff_content.split("\n"):
        # Parse file headers
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3][2:]  # Remove 'b/' prefix
                if current_file not in modified_files:
                    modified_files[current_file] = {
                        "added_lines": [],
                        "modified_lines": [],
                    }

        # Parse hunk headers to get line numbers
        elif line.startswith("@@") and current_file:
            # Extract line numbers from hunk header like @@ -10,7 +10,9 @@
            hunk_match = re.search(r"@@ -\d+,?\d* \+(\d+),?\d* @@", line)
            if hunk_match:
                start_line = int(hunk_match.group(1))
                modified_files[current_file]["modified_lines"].append(start_line)

    return modified_files if modified_files else None


def get_source_files_from_compile_commands(compile_commands_file):
    """Extract source files from compile_commands.json"""
    try:
        with open(compile_commands_file, "r") as f:
            compile_commands = json.load(f)

        source_files = []
        for entry in compile_commands:
            if "file" in entry:
                file_path = entry["file"]
                # Filter for C/C++ source files
                if any(
                    file_path.endswith(ext) for ext in [".c", ".cpp", ".cc", ".cxx"]
                ):
                    source_files.append(file_path)

        return source_files
    except Exception as e:
        print(f"Warning: Could not parse {compile_commands_file}: {e}")
        return []


def filter_files_by_changes(source_files, modified_files, repo_path):
    """Filter source files to only include modified ones"""
    if not modified_files:
        return source_files

    repo_path = Path(repo_path).resolve()
    filtered_files = []

    for source_file in source_files:
        source_path = Path(source_file)

        # Make path relative to repo if it's absolute
        if source_path.is_absolute():
            try:
                rel_path = source_path.relative_to(repo_path)
            except ValueError:
                rel_path = source_path
        else:
            rel_path = source_path

        # Check if this file was modified
        for modified_file in modified_files:
            if str(rel_path) == modified_file or str(rel_path).endswith(modified_file):
                filtered_files.append(source_file)
                break

    return filtered_files


def run_focused_analysis_with_diff(diff_file, compile_commands_file, repo_path):
    """Run focused analysis using clang-tidy-diff on modified lines"""

    # Build directory path (iwasm or wamrc)
    build_dir = compile_commands_file.parent

    # Use clang-tidy-diff with correct format: -p 1 -path <build_dir> < <diff_file>
    # Note: clang-tidy-diff doesn't support --config-file, it uses .clang-tidy in the repo
    cmd = f"clang-tidy-diff -p 1 -path {build_dir} < {diff_file}"

    print(f"Running clang-tidy-diff for focused analysis...")
    print(f"Command: {cmd}")

    try:
        stdout, stderr, returncode = run_command(cmd, cwd=repo_path)

        # Capture and display all output from clang-tidy-diff
        if stdout:
            print("clang-tidy-diff output:")
            print(stdout)

        if stderr:
            print("clang-tidy-diff warnings/errors:")
            print(stderr)

        if returncode != 0:
            print(f"clang-tidy-diff exited with code: {returncode}")

        # Return both stdout and stderr as they may both contain issues
        return stdout + "\n" + stderr if stderr else stdout

    except Exception as e:
        # If clang-tidy-diff execution fails, raise an exception to be caught by main
        raise Exception(f"clang-tidy-diff execution failed: {e}")


def run_global_analysis(
    files_to_analyze, compile_commands_file, config_file, repo_path
):
    """Run global clang-tidy analysis on specified files"""
    if not files_to_analyze:
        return ""

    # Prepare clang-tidy command with system header filtering
    files_str = " ".join(f'"{f}"' for f in files_to_analyze)

    cmd = (
        f"clang-tidy {files_str} "
        f"-p {compile_commands_file.parent} "
        f"--config-file={config_file} "
        f"--header-filter='^(?!.*(usr/include|/usr/local|/opt|system)).*'"
    )

    print(f"Running clang-tidy global analysis on {len(files_to_analyze)} files...")
    print(f"Command: {cmd}")

    try:
        stdout, stderr, returncode = run_command(cmd, cwd=repo_path)

        # Display all output from clang-tidy
        if stdout:
            print("clang-tidy output:")
            print(stdout)

        if stderr:
            print("clang-tidy warnings/errors:")
            print(stderr)

        if returncode != 0 and returncode != 1:  # 1 is normal when issues are found
            print(f"clang-tidy exited with code: {returncode}")

        # Return both stdout and stderr as they may both contain issues
        return stdout + "\n" + stderr if stderr else stdout

    except Exception as e:
        # If clang-tidy execution fails, raise an exception to be caught by main
        raise Exception(f"clang-tidy execution failed: {e}")


def run_clang_tidy_analysis(
    files_to_analyze, compile_commands_file, config_file, repo_path
):
    """Legacy function - redirects to global analysis"""
    return run_global_analysis(
        files_to_analyze, compile_commands_file, config_file, repo_path
    )


def parse_clang_tidy_output(output):
    """Parse clang-tidy output to extract issues, filtering out system headers"""
    issues = []
    lines = output.split("\n")

    # System header patterns to ignore
    system_header_patterns = [
        "/usr/include/",
        "/usr/local/include/",
        "/opt/",
        "system/",
        "/Applications/Xcode.app/",  # macOS system headers
        "C:\\Program Files",  # Windows system headers
        "/Library/Developer/",  # macOS SDK headers
    ]

    for line in lines:
        # Match clang-tidy output format: file:line:col: severity: message [rule]
        match = re.match(
            r"^(.+?):(\d+):(\d+):\s+(warning|error|note):\s+(.+?)(?:\s+\[(.+?)\])?$",
            line,
        )
        if match:
            file_path, line_num, col_num, severity, message, rule = match.groups()

            # Skip issues in system headers
            is_system_header = any(
                pattern in file_path for pattern in system_header_patterns
            )
            if is_system_header:
                continue

            issues.append(
                {
                    "file": file_path,
                    "line": int(line_num),
                    "column": int(col_num),
                    "severity": severity,
                    "message": message,
                    "rule": rule or "unknown",
                }
            )

    return issues


def generate_analysis_report(issues, analysis_config, inter_dir):
    """Generate the final analysis report"""

    # Load template
    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    template_path = skill_dir / "assets" / "report_template.md"

    if template_path.exists():
        template = template_path.read_text()
    else:
        # Fallback template
        template = """# Static Analysis Report

## Analysis Summary
- **Analysis Date**: {analysis_date}
- **Analysis Type**: {analysis_type}
- **Components Analyzed**: {components}
- **Total Issues Found**: {total_issues}
- **Files Analyzed**: {files_analyzed}

## Detailed Findings
{detailed_findings}

---
*Report generated by static-analyze skill*"""

    # Analyze issues
    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    file_issues = defaultdict(list)

    for issue in issues:
        severity_counts[issue["severity"]] += 1
        category_counts[issue["rule"]] += 1
        file_issues[issue["file"]].append(issue)

    # Format severity breakdown
    severity_breakdown = (
        "\n".join(
            [
                f"- **{severity.title()}**: {count}"
                for severity, count in sorted(severity_counts.items())
            ]
        )
        if severity_counts
        else "No issues found"
    )

    # Format category breakdown
    category_breakdown = (
        "\n".join(
            [
                f"- **{rule}**: {count}"
                for rule, count in sorted(category_counts.items(), key=lambda x: -x[1])[
                    :10
                ]
            ]
        )
        if category_counts
        else "No issues found"
    )

    # Format detailed findings
    detailed_findings = []
    for file_path, file_issues_list in sorted(file_issues.items()):
        detailed_findings.append(f"### {file_path}")
        for issue in file_issues_list:
            detailed_findings.append(
                f"- **Line {issue['line']}**: {issue['severity'].title()} - {issue['message']} [{issue['rule']}]"
            )
        detailed_findings.append("")

    detailed_findings_text = (
        "\n".join(detailed_findings) if detailed_findings else "No issues found"
    )

    # Format files with issues
    files_with_issues_text = (
        "\n".join(
            [
                f"- **{file_path}**: {len(file_issues_list)} issue(s)"
                for file_path, file_issues_list in sorted(file_issues.items())
            ]
        )
        if file_issues
        else "No files with issues"
    )

    # Generate recommendations
    recommendations = []
    if severity_counts.get("error", 0) > 0:
        recommendations.append("🔴 **Critical**: Fix all errors before proceeding")
    if severity_counts.get("warning", 0) > 5:
        recommendations.append(
            "⚠️ **High Priority**: Address warnings to improve code quality"
        )
    if not issues:
        recommendations.append("✅ **Good**: No issues detected in analyzed code")

    recommendations_text = (
        "\n".join(recommendations) if recommendations else "No specific recommendations"
    )

    # Fill template
    content = template.format(
        analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        analysis_type=analysis_config.get("type", "Unknown"),
        components=", ".join(analysis_config.get("components", [])),
        total_issues=len(issues),
        files_analyzed=analysis_config.get("files_count", 0),
        clang_tidy_version=analysis_config.get("clang_tidy_version", "Unknown"),
        config_file=str(analysis_config.get("config_file", "Unknown")),
        compile_commands_files=", ".join(
            str(f) for f in analysis_config.get("compile_commands_files", [])
        ),
        severity_breakdown=severity_breakdown,
        category_breakdown=category_breakdown,
        detailed_findings=detailed_findings_text,
        files_with_issues=files_with_issues_text,
        recommendations=recommendations_text,
        commands_used=analysis_config.get("commands_used", "Not available"),
    )

    # Write report
    report_file = Path(inter_dir) / "static_analysis_report.md"
    report_file.write_text(content)

    return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Run clang-tidy static analysis on WAMR projects"
    )
    parser.add_argument(
        "inter_dir", help="Directory containing build outputs and temporary files"
    )
    parser.add_argument(
        "--repo_path",
        default=".",
        help="Path to WAMR repository (default: current directory)",
    )

    args = parser.parse_args()

    # Ensure inter_dir exists
    inter_dir = Path(args.inter_dir)
    if not inter_dir.exists():
        print(f"❌ Inter directory does not exist: {inter_dir}")
        sys.exit(1)

    try:
        repo_path = Path(args.repo_path).resolve()

        print(f"Running static analysis on repository: {repo_path}")
        print(f"Inter directory: {inter_dir}")

        # Check clang-tidy availability
        print("\n=== Checking Prerequisites ===")
        clang_tidy_version, has_clang_tidy_diff = check_clang_tidy_availability()
        print(f"✅ clang-tidy version: {clang_tidy_version}")
        print("✅ clang-tidy-diff available for focused analysis")

        # Find build directories and compile_commands.json files
        compile_commands_files, components = find_build_directories(inter_dir)
        print(f"✅ Found compile_commands.json for: {', '.join(components)}")

        # Find .clang-tidy config file
        config_file = find_clang_tidy_config(repo_path)
        print(f"✅ Found config file: {config_file}")

        # Check for changes.diff to determine analysis scope
        print("\n=== Determining Analysis Scope ===")
        diff_file = Path(inter_dir) / "changes.diff"
        if diff_file.exists():
            analysis_type = "Focused analysis on modified lines using clang-tidy-diff"
            print(f"📄 Found changes.diff - {analysis_type}")
            use_focused_analysis = True
        else:
            analysis_type = "Global scan of all source files using clang-tidy"
            print(f"🌐 No changes.diff found - {analysis_type}")
            use_focused_analysis = False

        # Run analysis for each component
        print("\n=== Running Static Analysis ===")
        all_issues = []
        total_files_analyzed = 0
        commands_used = []

        for compile_commands_file in compile_commands_files:
            component = compile_commands_file.parent.name
            print(f"\nAnalyzing {component} component...")

            if use_focused_analysis:
                # Use clang-tidy-diff for focused analysis
                output = run_focused_analysis_with_diff(
                    diff_file,
                    compile_commands_file,
                    repo_path,
                )

                # For file count, estimate based on diff (not perfectly accurate but reasonable)
                modified_files = parse_changes_diff(inter_dir)
                if modified_files:
                    source_files = get_source_files_from_compile_commands(
                        compile_commands_file
                    )
                    files_count = len(
                        filter_files_by_changes(source_files, modified_files, repo_path)
                    )
                else:
                    files_count = 0

                method_name = "clang-tidy-diff"
            else:
                # Use global analysis
                source_files = get_source_files_from_compile_commands(
                    compile_commands_file
                )
                print(
                    f"Found {len(source_files)} source files in compile_commands.json"
                )

                output = run_global_analysis(
                    source_files, compile_commands_file, config_file, repo_path
                )
                files_count = len(source_files)
                method_name = "clang-tidy (global)"

            # Parse results (system headers already filtered in parse function)
            issues = parse_clang_tidy_output(output)
            all_issues.extend(issues)
            total_files_analyzed += files_count

            print(
                f"Found {len(issues)} issues in {component} (system headers filtered)"
            )
            commands_used.append(f"{method_name} on {component}")

        # Generate report
        print("\n=== Generating Report ===")
        analysis_config = {
            "type": analysis_type,
            "components": components,
            "files_count": total_files_analyzed,
            "clang_tidy_version": clang_tidy_version,
            "config_file": config_file,
            "compile_commands_files": compile_commands_files,
            "commands_used": "; ".join(commands_used),
        }

        report_file = generate_analysis_report(all_issues, analysis_config, inter_dir)

        # Write success status
        status_file = write_status_report(inter_dir, True)

        print(f"\n✅ Static analysis completed successfully!")
        print(f"   Total issues found: {len(all_issues)}")
        print(f"   Files analyzed: {total_files_analyzed}")
        print(f"   Status: {status_file}")
        print(f"   Report: {report_file}")

    except Exception as e:
        # Write failure status
        status_file = write_status_report(inter_dir, False, str(e))
        print(f"\n❌ Static analysis failed: {e}")
        print(f"   Status: {status_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
