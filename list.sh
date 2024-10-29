#!/bin/bash

# Directory to scan, default to current if not provided
dir="${1:-.}"

# Function to process each directory
process_directory() {
    local current_dir="$1"
    # Markdown friendly prompt at the top of the output
    echo "The following is an application. After you have reviewed it, do not respond except to acknowledge receipt of the information, after which I will provide instructions"
    echo ""
    find "$current_dir" -type f \( \
        -name '*.py' -o -name '*.html' -o -name '*.js' -o -name '*.css' -o \
        -name '*.yaml' -o -name '*.md' -o -name '*.txt' -o -name '*.sql' \) \
        -exec echo "" \; \
        -exec echo "" \; \
        -exec echo "### File: {}" \; \
        -exec echo '```' \; \
        -exec cat "{}" \; \
        -exec echo "" \; \
        -exec echo '```' \; \
        -exec echo "" \; \
        -exec echo "" \;
}

# Export results to clipboard
process_directory "$dir" | pbcopy

echo "File listings have been copied to the clipboard."
