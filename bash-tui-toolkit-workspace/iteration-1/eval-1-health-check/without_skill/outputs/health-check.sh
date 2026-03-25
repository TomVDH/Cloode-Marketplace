#!/bin/bash

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print the banner
print_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║            🔍  SERVER HEALTH CHECKER v1.0  🔍               ║
║                                                               ║
║              Monitor your system's vital signs               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Function to print a horizontal line
print_line() {
    echo -e "${CYAN}─────────────────────────────────────────────────────────────${NC}"
}

# Function to print table header
print_table_header() {
    local header="$1"
    echo ""
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $header${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to check disk usage
check_disk_usage() {
    print_table_header "📊 DISK USAGE"

    echo -e "${BOLD}Filesystem${NC:45} ${BOLD}Size${NC:10} ${BOLD}Used${NC:10} ${BOLD}Available${NC:10} ${BOLD}Use%${NC}"
    print_line

    df -h | awk 'NR>1 {
        fs=$1
        size=$2
        used=$3
        avail=$4
        use=$5

        # Parse percentage
        percent=int(use)

        # Color code based on usage
        if (percent >= 90) {
            color="\033[0;31m"  # Red
        } else if (percent >= 70) {
            color="\033[1;33m"  # Yellow
        } else {
            color="\033[0;32m"  # Green
        }

        # Truncate filesystem name if too long
        if (length(fs) > 20) {
            fs=substr(fs, 1, 17) "..."
        }

        printf "%-25s %10s %10s %10s %s%3s%%\033[0m\n", fs, size, used, avail, color, percent
    }'

    echo ""
    echo -e "${YELLOW}Note: Filesystem with >90% usage is critical (red), >70% is warning (yellow)${NC}"
    print_line
}

# Function to check memory usage
check_memory_usage() {
    print_table_header "💾 MEMORY USAGE"

    # Get memory info from /proc/meminfo
    local total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local available=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    local used=$((total - available))

    # Convert to human-readable format
    local total_gb=$(echo "scale=2; $total / 1048576" | bc)
    local used_gb=$(echo "scale=2; $used / 1048576" | bc)
    local avail_gb=$(echo "scale=2; $available / 1048576" | bc)
    local percent=$((used * 100 / total))

    # Determine color
    if [ $percent -ge 90 ]; then
        color="${RED}"
    elif [ $percent -ge 70 ]; then
        color="${YELLOW}"
    else
        color="${GREEN}"
    fi

    echo -e "${BOLD}Memory Type${NC:25} ${BOLD}Amount${NC}"
    print_line
    printf "%-30s %s\n" "Total Memory:" "${total_gb} GB"
    printf "%-30s ${color}%s${NC}\n" "Used Memory:" "${used_gb} GB"
    printf "%-30s %s\n" "Available Memory:" "${avail_gb} GB"
    printf "%-30s ${color}%s%%${NC}\n" "Usage Percentage:" "${percent}"

    # Create a simple visual bar
    echo ""
    echo -e "${BOLD}Usage Bar:${NC}"
    local bar_length=$((percent / 5))
    local empty=$((20 - bar_length))
    printf "["
    printf "%${bar_length}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' '-'
    printf "] ${color}%d%%${NC}\n" "$percent"

    echo ""
    echo -e "${YELLOW}Note: >90% is critical (red), >70% is warning (yellow), <70% is healthy (green)${NC}"
    print_line
}

# Function to check network connectivity
check_network_connectivity() {
    print_table_header "🌐 NETWORK CONNECTIVITY"

    echo -e "${BOLD}Host${NC:20} ${BOLD}Status${NC:15} ${BOLD}Response Time${NC}"
    print_line

    # Array of hosts to ping
    local hosts=("google.com" "8.8.8.8" "cloudflare.com")

    for host in "${hosts[@]}"; do
        # Ping once with timeout of 2 seconds
        local response=$(ping -c 1 -W 2 "$host" 2>/dev/null | grep "time=" | awk -F'time=' '{print $2}')

        if [ -z "$response" ]; then
            printf "%-25s ${RED}%-15s${NC} N/A\n" "$host" "UNREACHABLE"
        else
            printf "%-25s ${GREEN}%-15s${NC} %s\n" "$host" "REACHABLE" "$response"
        fi
    done

    echo ""

    # Check DNS resolution
    echo -e "${BOLD}DNS Resolution:${NC}"
    if ping -c 1 -W 2 google.com &>/dev/null; then
        echo -e "  ${GREEN}✓ DNS is working${NC}"
    else
        echo -e "  ${RED}✗ DNS may not be working${NC}"
    fi

    # Check default route
    echo ""
    echo -e "${BOLD}Default Route:${NC}"
    local gateway=$(ip route | grep default | awk '{print $3}')
    if [ -n "$gateway" ]; then
        echo -e "  ${GREEN}✓ Gateway: $gateway${NC}"
    else
        echo -e "  ${RED}✗ No default gateway found${NC}"
    fi

    print_line
}

# Function to display the main menu
show_menu() {
    print_banner
    echo ""
    echo -e "${BOLD}${CYAN}Select an option:${NC}"
    echo ""
    echo -e "  ${BOLD}1)${NC} Check Disk Usage"
    echo -e "  ${BOLD}2)${NC} Check Memory Usage"
    echo -e "  ${BOLD}3)${NC} Check Network Connectivity"
    echo -e "  ${BOLD}4)${NC} Run All Checks"
    echo -e "  ${BOLD}5)${NC} Exit"
    echo ""
    print_line
    echo ""
}

# Function to display exit message
exit_message() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                  Thanks for using Health Checker!            ║
║                                                               ║
║               Keep your systems running smoothly              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    exit 0
}

# Main script loop
main() {
    while true; do
        show_menu
        read -p "$(echo -e ${BOLD}Enter your choice [1-5]:${NC} )" choice

        case $choice in
            1)
                check_disk_usage
                read -p "$(echo -e ${BOLD}Press Enter to continue...${NC})" dummy
                ;;
            2)
                check_memory_usage
                read -p "$(echo -e ${BOLD}Press Enter to continue...${NC})" dummy
                ;;
            3)
                check_network_connectivity
                read -p "$(echo -e ${BOLD}Press Enter to continue...${NC})" dummy
                ;;
            4)
                check_disk_usage
                check_memory_usage
                check_network_connectivity
                read -p "$(echo -e ${BOLD}Press Enter to continue...${NC})" dummy
                ;;
            5)
                exit_message
                ;;
            *)
                echo -e "${RED}Invalid option. Please try again.${NC}"
                sleep 1
                ;;
        esac
    done
}

# Run the main function
main
