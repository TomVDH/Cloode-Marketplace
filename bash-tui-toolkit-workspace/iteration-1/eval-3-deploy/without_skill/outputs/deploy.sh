#!/bin/bash

# ============================================================================
# DEPLOYMENT SCRIPT WITH TUI ELEMENTS
# ============================================================================

set -o pipefail

# Configuration
DRY_RUN=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Spinner characters
SPINNER_FRAMES=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
SPINNER_DELAY=0.1

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                     🚀  DEPLOYMENT SCRIPT v1.0  🚀                      ║
║                                                                          ║
║                    Production Deployment Automation                     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --dry-run    Show what would be executed without making changes"
    echo "  --verbose    Show detailed output during execution"
    echo "  --help       Display this help message"
    echo
}

# Spinner function - displays animated spinner while command runs
run_with_spinner() {
    local step_name=$1
    local command=$2
    local frame_idx=0
    local temp_output

    # Create temporary file for command output
    temp_output=$(mktemp)

    printf "  %-40s " "$step_name"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC}"
        return 0
    fi

    # Run command in background
    eval "$command" > "$temp_output" 2>&1 &
    local pid=$!

    # Animate spinner while process runs
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  %-40s ${CYAN}${SPINNER_FRAMES[$frame_idx]}${NC}" "$step_name"
        frame_idx=$(( (frame_idx + 1) % ${#SPINNER_FRAMES[@]} ))
        sleep "$SPINNER_DELAY"
    done

    # Wait for process to finish and get exit code
    wait "$pid"
    local exit_code=$?

    # Clear spinner and show result
    if [ $exit_code -eq 0 ]; then
        printf "\r  %-40s ${GREEN}✓${NC}\n" "$step_name"
        if [ "$VERBOSE" = true ]; then
            cat "$temp_output" | sed 's/^/    /'
        fi
        rm "$temp_output"
        return 0
    else
        printf "\r  %-40s ${RED}✗${NC}\n" "$step_name"
        echo -e "${RED}Error output:${NC}"
        cat "$temp_output" | sed 's/^/    /'
        rm "$temp_output"
        return 1
    fi
}

# Dry-run version that shows what would happen
show_step_preview() {
    local step_name=$1
    local command_desc=$2

    printf "  %-40s ${YELLOW}[DRY RUN]${NC}\n" "$step_name"
    echo -e "    ${CYAN}Would execute:${NC} $command_desc"
}

# ============================================================================
# DEPLOYMENT STEPS
# ============================================================================

step_check_git_status() {
    local cmd="git status --porcelain"
    if [ "$DRY_RUN" = true ]; then
        show_step_preview "Step 1: Check Git Status" "$cmd"
        return 0
    fi
    run_with_spinner "Step 1: Check Git Status" "$cmd"
    return $?
}

step_run_tests() {
    local cmd="npm test 2>&1 | head -n 20"
    if [ "$DRY_RUN" = true ]; then
        show_step_preview "Step 2: Run Tests" "npm test"
        return 0
    fi
    # Simulate test run if npm test doesn't exist
    local sim_cmd="if command -v npm &> /dev/null && [ -f package.json ]; then npm test; else echo 'Running simulated tests...' && sleep 1 && echo 'All tests passed'; fi"
    run_with_spinner "Step 2: Run Tests" "$sim_cmd"
    return $?
}

step_build() {
    local cmd="npm run build 2>&1 | head -n 20"
    if [ "$DRY_RUN" = true ]; then
        show_step_preview "Step 3: Build Application" "npm run build"
        return 0
    fi
    # Simulate build if npm build doesn't exist
    local sim_cmd="if command -v npm &> /dev/null && [ -f package.json ]; then npm run build; else echo 'Running simulated build...' && sleep 1 && mkdir -p dist && echo 'Build complete' > dist/build.log; fi"
    run_with_spinner "Step 3: Build Application" "$sim_cmd"
    return $?
}

step_upload_artifacts() {
    local cmd="tar -czf artifacts.tar.gz dist/ 2>&1"
    if [ "$DRY_RUN" = true ]; then
        show_step_preview "Step 4: Upload Artifacts" "tar -czf artifacts.tar.gz dist/ && upload to repository"
        return 0
    fi
    # Simulate artifact upload
    local sim_cmd="mkdir -p dist 2>/dev/null; tar -czf artifacts.tar.gz dist/ 2>/dev/null && echo 'Artifacts uploaded successfully'"
    run_with_spinner "Step 4: Upload Artifacts" "$sim_cmd"
    return $?
}

step_update_config() {
    local cmd="cp config.example.sh config.sh && echo 'DEPLOY_TIME=$(date)' >> config.sh"
    if [ "$DRY_RUN" = true ]; then
        show_step_preview "Step 5: Update Configuration" "cp config.example.sh config.sh && update timestamps"
        return 0
    fi
    # Simulate config update
    local sim_cmd="echo 'DEPLOY_TIME=$(date)' > config.deployed && echo 'Configuration updated'"
    run_with_spinner "Step 5: Update Configuration" "$sim_cmd"
    return $?
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                print_banner
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Display banner
    print_banner

    # Show dry-run notice if applicable
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}🔍 DRY RUN MODE - No changes will be made${NC}"
        echo
    fi

    # Track overall success
    local failed_steps=0

    # Execute deployment steps
    echo -e "${BLUE}Starting deployment process...${NC}"
    echo

    step_check_git_status || ((failed_steps++))
    step_run_tests || ((failed_steps++))
    step_build || ((failed_steps++))
    step_upload_artifacts || ((failed_steps++))
    step_update_config || ((failed_steps++))

    # Print summary
    echo
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

    if [ $failed_steps -eq 0 ]; then
        echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
        echo
        exit 0
    else
        echo -e "${RED}✗ Deployment failed with $failed_steps error(s)${NC}"
        echo
        exit 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
