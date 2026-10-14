#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import argparse
import sys

def parse_repo_string(repo_string):
    """
    Parses the repository string "user/repo@branch" into (user, repo, branch).

    Args:
        repo_string: The repository string in the format 'user/repo@branch'.

    Returns:
        A tuple containing (user, repo, branch).

    Raises:
        ValueError: If the string format is invalid.
    """
    # Regex to match the 'user/repo@branch' format
    match = re.match(r"([^/]+)/([^@]+)@(.+)", repo_string)
    if match:
        user, repo, branch = match.groups()
        # Basic validation to avoid empty parts
        if user and repo and branch:
            return user, repo, branch
        else:
            raise ValueError("User, repository name, and branch cannot be empty.")
    else:
        raise ValueError("Repository string must be in the format 'user/repo@branch'.")

def replace_links_in_file(filepath, repo_user, repo_name, branch, custom_domain):
    """
    Reads a file, replaces specific GitHub/jsDelivr links, and writes back if changes were made.

    Args:
        filepath: Path to the Markdown file.
        repo_user: GitHub username.
        repo_name: GitHub repository name.
        branch: GitHub repository branch.
        custom_domain: The custom domain to use for replacement.

    Returns:
        The number of replacements made in this file.
    """
    replacements_made = 0
    try:
        # Read the file content using UTF-8 encoding
        with open(filepath, 'r', encoding='utf-8') as f_read:
            content = f_read.read()
            original_content = content # Store original content for comparison

        # --- Define Regex Patterns ---
        # Escape user-provided parts to be safe in regex
        escaped_user = re.escape(repo_user)
        escaped_repo = re.escape(repo_name)
        escaped_branch = re.escape(branch)

        # Pattern for jsDelivr links (matches http or https)
        # Captures the path after the branch name
        jsdelivr_pattern = re.compile(
            # Using rf-string for easier combination of regex and variables
            rf"https?://cdn\.jsdelivr\.net/gh/{escaped_user}/{escaped_repo}@{escaped_branch}/([^\s\"\'\)<>]+)"
        )

        # Pattern for raw GitHub links (matches http or https)
        # Captures the path after the branch name
        github_raw_pattern = re.compile(
            rf"https?://raw\.githubusercontent\.com/{escaped_user}/{escaped_repo}/{escaped_branch}/([^\s\"\'\)<>]+)"
        )

        # --- Define Replacement Logic ---
        # The base URL for replacement
        replacement_url_base = f"https://{custom_domain}"

        # Replacement function: constructs the new URL using the captured path (group 1)
        def replacer(match):
            nonlocal replacements_made # Allow modification of the outer scope variable
            path = match.group(1) # Get the captured path part
            replacements_made += 1
            # Ensure no double slashes if path starts with one (though unlikely with pattern)
            return f"{replacement_url_base}/{path.lstrip('/')}"

        # --- Perform Replacements ---
        # Apply the replacement for jsDelivr links
        content = jsdelivr_pattern.sub(replacer, content)
        # Apply the replacement for raw GitHub links
        content = github_raw_pattern.sub(replacer, content)

        # --- Write Back if Changed ---
        if content != original_content:
            # Write the modified content back to the file using UTF-8
            with open(filepath, 'w', encoding='utf-8') as f_write:
                f_write.write(content)
            # Use a positive indicator for successful replacement
            print(f"  ✅ Replaced {replacements_made} links.")
        else:
            # Indicate that no relevant links were found or needed changing
            # print(f"  - No matching links found or no changes needed.") # Can be uncommented if more verbosity is desired
            pass # Keep output clean if no changes

    except FileNotFoundError:
        print(f"  ❌ Error: File not found at {filepath}.")
    except IOError as e:
        print(f"  ❌ Error reading/writing file {filepath}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during file processing
        print(f"  ❌ An unexpected error occurred processing file {filepath}: {e}")

    return replacements_made # Return the count for this file

def main():
    """
    Main function to parse arguments and orchestrate the link replacement process.
    """
    # Setup argument parser for command-line interface
    parser = argparse.ArgumentParser(
        description="Recursively scan Markdown files and replace GitHub/jsDelivr links with a custom domain.",
        formatter_class=argparse.RawDescriptionHelpFormatter # Preserve formatting in help text
    )

    # Required arguments
    parser.add_argument(
        "repo",
        help="Target GitHub repository in the format 'user/repo@branch' (e.g., DullJZ/MyPicture@master)"
    )
    parser.add_argument(
        "domain",
        help="Custom domain name to use for replacement (e.g., ohmyimage.pp.ua)"
    )

    # Optional arguments
    parser.add_argument(
        "-d", "--directory",
        default=".", # Default to the current directory
        help="The root directory to start scanning for Markdown files (default: current directory)"
    )
    parser.add_argument(
        "-e", "--extensions",
        default=".md",
        help="Comma-separated list of file extensions to process (default: .md)"
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # --- Validate Inputs ---
    try:
        repo_user, repo_name, branch = parse_repo_string(args.repo)
    except ValueError as e:
        # Print error message and exit if repository format is invalid
        print(f"Error: Invalid repository format provided ('{args.repo}'). {e}", file=sys.stderr)
        sys.exit(1) # Exit with a non-zero status code indicates an error

    custom_domain = args.domain
    start_dir = args.directory
    # Process extensions argument into a tuple of lowercased extensions
    file_extensions = tuple(ext.strip().lower() for ext in args.extensions.split(',') if ext.strip())
    if not file_extensions:
        print(f"Error: No valid file extensions specified.", file=sys.stderr)
        sys.exit(1)


    # --- Start Processing ---
    total_files_processed = 0
    total_replacements = 0

    # Print initial information about the task
    print(f"🚀 Starting link replacement process...")
    print(f"   Repository: {args.repo}")
    print(f"   Custom Domain: {custom_domain}")
    print(f"   Scanning Directory: {os.path.abspath(start_dir)}")
    print(f"   File Extensions: {', '.join(file_extensions)}")
    print("-" * 40) # Separator for clarity

    # --- Walk Through Directory ---
    # os.walk yields (current_directory, subdirectories, files_in_current)
    for root, _, files in os.walk(start_dir):
        for filename in files:
            # Check if the file extension matches the ones specified
            if filename.lower().endswith(file_extensions):
                filepath = os.path.join(root, filename)
                # Use relative path for cleaner output if possible
                relative_path = os.path.relpath(filepath, start_dir)
                print(f"Processing: {relative_path}")
                total_files_processed += 1
                try:
                    # Process the file and add the number of replacements to the total
                    count = replace_links_in_file(filepath, repo_user, repo_name, branch, custom_domain)
                    total_replacements += count
                except Exception as e:
                    # Catch potential errors from replace_links_in_file if not handled internally
                    print(f"  ❌ Failed to process {relative_path}: {e}")


    # --- Print Summary ---
    print("-" * 40)
    print(f"🏁 Scan complete.")
    if total_files_processed == 0:
        print(f"   No files with extensions ({', '.join(file_extensions)}) found in '{start_dir}'.")
    else:
        print(f"   Processed {total_files_processed} file(s).")
        print(f"   Made a total of {total_replacements} replacement(s).")

# --- Script Entry Point ---
if __name__ == "__main__":
    # Ensure the script runs the main function when executed directly
    main()
