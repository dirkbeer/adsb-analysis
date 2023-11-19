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

# Clone the repository
clone_repository() {
    echo "Cloning the adsb-analysis repository..."
    git clone https://github.com/dirkbeer/adsb-analysis.git || error "Failed to clone repository."

    cd adsb-analysis || error "Failed to enter the adsb-analysis directory."
}

# Create and activate virtual environment
setup_venv() {
    echo "Setting up Python virtual environment..."
    python3 -m venv venv || error "Failed to create a virtual environment."

    source venv/bin/activate || error "Failed to activate the virtual environment."
}

# Install Python dependencies
install_python_packages() {
    echo "Installing Python packages..."
    pip install -r requirements.txt || error "Failed to install Python packages."
}

# Print completion message
print_completion() {
    success "Setup completed successfully."
    echo "To activate the virtual environment and run the analysis, execute:"
    echo "source venv/bin/activate"
    echo "./analyze.py"
}

# Start the script
install_packages
clone_repository
setup_venv
install_python_packages
print_completion
