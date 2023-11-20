#!/bin/bash

# Check if the script is running in non-interactive mode
NON_INTERACTIVE=${NON_INTERACTIVE:-false}

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
    # Change to the directory where this script is located
    SCRIPT_DIR=$(dirname "$0")
    cd "$SCRIPT_DIR"

    # Check for .git directory to confirm it's a git repository
    if [ -d ".git" ]; then
        echo ""
        echo "Checking for local changes in the existing repository..."

        # Fetch updates from the remote repository silently
        git fetch > /dev/null 2>&1

        # Check for differences between the local and remote repositories
        LOCAL=$(git rev-parse @)
        REMOTE=$(git rev-parse @{u})

	if [ $LOCAL != $REMOTE ]; then
	    if [ "$NON_INTERACTIVE" = "false" ]; then
	        echo "Updates are available. This will overwrite any local changes."
	        read -p "Do you want to proceed? (y/n): " user_input
	        if [[ $user_input == "y" || $user_input == "Y" ]]; then
	            git reset --hard @{u}
	            git pull
	            echo "Updates applied successfully."
	        else
	            echo "Update aborted by user."
	            exit 0
	        fi
	    else
	        # Default action in non-interactive mode
	        git reset --hard @{u}
	        git pull
	        echo "Updates applied automatically in non-interactive mode."
	    fi
	else
	    echo "Your copy of the repository is up to date."
	fi
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
    if [ ! -d "venv" ]; then
        python3 -m venv venv || error "Failed to create a virtual environment."
    fi
    source venv/bin/activate || error "Failed to activate the virtual environment."
}

# Install or update Python dependencies
install_python_packages() {
    echo "Uninstalling the kneed package if it exists..."
    pip uninstall -y kneed 2>/dev/null || echo "kneed package not found."

    echo "Installing or updating Python packages..."
    pip install --upgrade pip
    pip install -r requirements.txt || error "Failed to install or update Python packages."
}

# Print completion message
print_completion() {
    echo ""
    success "Setup completed successfully."
    echo ""
    echo "To run the analysis, execute:"
    echo ""
    echo "    ~/adsb-analysis/run_analysis.sh"
    echo ""
}

# Start the script
update_repository
install_packages
setup_venv
install_python_packages
print_completion
