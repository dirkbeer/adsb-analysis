#!/bin/bash

# Change to the directory of the script
cd "$(dirname "$0")"

# Activate the Python virtual environment
source venv/bin/activate

# Check if the Python virtual environment was activated successfully
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Virtual environment activated."

    # Run the analysis script
    ./analyze.py

    # Check if analyze.py ran successfully
    if [[ $? -eq 0 ]]; then
        echo "Analysis complete. The output has been saved."

        # Attempt to retrieve the local IP address of the Raspberry Pi
        IP_ADDRESS=$(hostname -I | awk '{print $1}')
        if [[ -z "$IP_ADDRESS" ]]; then
            echo "Could not determine the IP address."
            IP_ADDRESS="sdr.local" # default value if IP address cannot be determined
        fi

        # Copy the image to the web server directory
        sudo cp ./receiver_performance.png /usr/local/share/tar1090/html
        echo "The image has been copied to the web server directory."

        # Provide the user with the URL to view the image
        echo "Go view the receiver performance plot at http://$IP_ADDRESS/tar1090/receiver_performance.png"

    else
        echo "An error occurred while running the analysis."
    fi
else
    echo "Failed to activate virtual environment. Please check that you have completed the setup."
fi

# Deactivate the virtual environment
deactivate
