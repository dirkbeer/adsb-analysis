#!/bin/bash

# Exit on any error
set -e

# Define the installation of required system packages
install_packages() {
    echo "Installing required packages..."
    sudo apt update
    sudo apt install -y git python3-pip python3-venv libopenblas-dev libopenjp2-7
}

# Clone the repository
clone_repository() {
    echo "Cloning the adsb-analysis repository..."
    git clone https://github.com/dirkbeer/adsb-analysis.git
    cd adsb-analysis
}

# Create and activate virtual environment
setup_venv() {
    echo "Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
}

# Install Python dependencies
install_python_packages() {
    echo "Installing Python packages..."
    pip install -r requirements.txt
}

# Print completion message
print_completion() {
    echo "Setup completed successfully."
    echo "To activate the virtual environment and run the analysis, execute:"
    echo "source venv/bin/activate"
    echo "./analyze.py"
}

# Run the functions
install_packages
clone_repository
setup_venv
install_python_packages
print_completion
