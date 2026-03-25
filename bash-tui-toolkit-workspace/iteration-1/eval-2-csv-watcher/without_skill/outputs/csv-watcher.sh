#!/bin/bash

# CSV Watcher - Monitor a directory for new CSV files and display statistics
# Shows animated loading bar while counting rows and displays a summary table

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Store processed files to avoid re-processing
declare -A processed_files

# Function to display animated loading bar
show_loading_bar() {
    local duration=${1:-3}
    local width=30
    local steps=30

    for ((i=0; i<=steps; i++)); do
        local percent=$((i * 100 / steps))
        local filled=$((i * width / steps))
        local empty=$((width - filled))

        printf "\r${BLUE}Processing:${NC} ["
        printf "%${filled}s" | tr ' ' '='
        printf "%${empty}s" | tr ' ' '-'
        printf "] %3d%%" "$percent"

        sleep "$(bc <<< "scale=3; $duration / $steps" 2>/dev/null || echo "0.01")"
    done
    printf "\n"
}

# Function to count rows in a CSV file
count_csv_rows() {
    local file=$1
    local row_count=0

    if [[ -f "$file" ]]; then
        # Count lines, subtract 1 for header (if present)
        row_count=$(wc -l < "$file" 2>/dev/null || echo "0")
        # Show as data rows (excluding header if it exists)
        if [[ $row_count -gt 0 ]]; then
            row_count=$((row_count - 1))
        fi
    fi

    echo "$row_count"
}

# Function to get human-readable file size
get_file_size() {
    local file=$1
    if [[ -f "$file" ]]; then
        du -h "$file" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# Function to display summary table
display_table_header() {
    printf "${GREEN}%-35s %-12s %-10s${NC}\n" "FILENAME" "ROW COUNT" "FILE SIZE"
    printf "%s\n" "$(printf '%0.s-' {1..57})"
}

display_table_row() {
    local filename=$1
    local row_count=$2
    local file_size=$3

    printf "%-35s %-12s %-10s\n" \
        "$(basename "$filename" | cut -c1-33)" \
        "$row_count" \
        "$file_size"
}

# Function to process a new CSV file
process_csv_file() {
    local file=$1

    if [[ ! -f "$file" ]]; then
        return
    fi

    echo ""
    echo "${YELLOW}Found new CSV file: $(basename "$file")${NC}"

    # Show animated loading bar
    show_loading_bar 2

    # Count rows
    local row_count=$(count_csv_rows "$file")
    local file_size=$(get_file_size "$file")

    # Mark as processed
    processed_files["$file"]=1

    echo ""
    display_table_header
    display_table_row "$file" "$row_count" "$file_size"
    echo ""
}

# Function to display all processed files table
display_all_files() {
    if [[ ${#processed_files[@]} -gt 0 ]]; then
        echo ""
        echo "${GREEN}=== CSV Files Summary ===${NC}"
        display_table_header

        for file in "${!processed_files[@]}"; do
            if [[ -f "$file" ]]; then
                local row_count=$(count_csv_rows "$file")
                local file_size=$(get_file_size "$file")
                display_table_row "$file" "$row_count" "$file_size"
            fi
        done
        echo ""
    fi
}

# Main monitoring loop
main() {
    local watch_dir="${1:-.}"

    if [[ ! -d "$watch_dir" ]]; then
        echo "${RED}Error: Directory '$watch_dir' does not exist${NC}" >&2
        exit 1
    fi

    echo "${GREEN}CSV Watcher Started${NC}"
    echo "${BLUE}Monitoring directory: $watch_dir${NC}"
    echo "${BLUE}Press Ctrl+C to stop${NC}"
    echo ""

    # Trap Ctrl+C to display final summary
    trap 'echo ""; echo "${YELLOW}Watcher stopped${NC}"; display_all_files; exit 0' INT

    # Main loop - monitor directory
    while true; do
        # Find all CSV files in the directory (not recursive)
        while IFS= read -r file; do
            if [[ ! " ${!processed_files[@]} " =~ " ${file} " ]]; then
                process_csv_file "$file"
            fi
        done < <(find "$watch_dir" -maxdepth 1 -type f -name "*.csv" 2>/dev/null | sort)

        # Sleep before next check
        sleep 2
    done
}

# Run main function with optional directory argument
main "$@"
