#!/bin/bash

# Define some colors for echo outputs
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to handle errors
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "The setup could not be completed. Please check the error message above."
    exit 1
}

# Function to print success message
success() {
    echo -e "${GREEN}$1${NC}"
}

# Update the package list and install required system packages
install_packages() {
    echo "Updating package list..."
    sudo apt update || error "Failed to update package list."

    echo "Installing required packages..."
    sudo apt install -y git python3-pip python3-venv libopenblas-dev libopenjp2-7 || error "Failed to install required packages."
}

# Check if the repository already exists and update it
update_repository() {
    if [ -d "adsb-analysis/.git" ]; then
        echo "Checking for local changes in the existing adsb-analysis repository..."
        cd adsb-analysis
        # Check for uncommitted changes in the git directory
        if ! git diff-index --quiet HEAD --; then
            # Prompt the user for action on local changes
            read -p "Local changes detected. Would you like to overwrite them? (y/N): " user_choice
            case $user_choice in
                [Yy]* )
                    echo "Overwriting local changes..."
                    git reset --hard HEAD
                    git clean -fd
                    ;;
                * )
                    echo "Keeping local changes. Update cancelled."
                    exit 0
                    ;;
            esac
        fi
        echo "Updating repository..."
        git pull || error "Failed to update repository."
    else
        clone_repository
    fi
}

# Clone the repository
clone_repository() {
    echo "Cloning the adsb-analysis repository..."
    git clone https://github.com/dirkbeer/adsb-analysis.git || error "Failed to clone repository."
    cd adsb-analysis || error "Failed to enter the adsb-analysis directory."
}

# Create and activate virtual environment
setup_venv() {
    echo "Setting up Python virtual environment..."
    # Check if the virtual environment already exists
    if [ ! -d "venv" ]; then
        python3 -m venv venv || error "Failed to create a virtual environment."
    fi
    source venv/bin/activate || error "Failed to activate the virtual environment."
}

# Install or update Python dependencies
install_python_packages() {
    echo "Installing or updating Python packages..."
    pip install --upgrade pip
    pip install -r requirements.txt || error "Failed to install or update Python packages."
}

# Print completion message
print_completion() {
    cd adsb-analysis || error "Failed to enter the adsb-analysis directory."
    success "Setup completed successfully."
    echo "To run the analysis, execute:"
    echo "cd adsb-analysis"
    echo "./run_analysis.sh"
}

# Start the script
install_packages
update_repository
setup_venv
install_python_packages
print_completion
