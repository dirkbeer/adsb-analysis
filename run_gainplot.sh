#!/bin/bash

# Change to the directory of the script
cd "$(dirname "$0")"

# Check if ../output directory exists, and create it if not
if [[ ! -d "../output" ]]; then
    mkdir -p "../output"
fi

# Fetch updates from the remote repository
git fetch > /dev/null 2>&1

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})
BASE=$(git merge-base @ @{u})

if [ $LOCAL = $REMOTE ]; then
    echo "Your copy of adsb-analysis is up to date."
elif [ $LOCAL = $BASE ]; then
    echo "Updates available, run 'curl -sSL https://raw.githubusercontent.com/dirkbeer/adsb-analysis/main/setup.sh | bash' to get the latest (this will overwrite any local changes)."
fi

# Activate the Python virtual environment
source venv/bin/activate

# Check if the Python virtual environment was activated successfully
if [[ "$VIRTUAL_ENV" != "" ]]; then

    # Run the analysis script (only uncomment one of these)
    ./src/gainplot.py

    # Check if analyze.py ran successfully
    if [[ $? -eq 0 ]]; then
        echo ""
        echo "Gain plots complete."

        # Attempt to retrieve the local IP address of the Raspberry Pi
        IP_ADDRESS=$(hostname -I | awk '{print $1}')
        if [[ -z "$IP_ADDRESS" ]]; then
            echo "Could not determine the IP address."
            IP_ADDRESS="sdr.local" # default value if IP address cannot be determined
        fi

        # Copy the image to the web server directory
        sudo cp ../output/gain_messages.png /usr/local/share/tar1090/html
        sudo cp ../output/gain_distance.png /usr/local/share/tar1090/html
        sudo cp ../output/adsb-analysis.html /usr/local/share/tar1090/html
        echo "Gain test plots copied to the tar1090 web directory."

        # Provide the user with the URL to view the image
        echo "Ctrl-click the links to view in your browser:"
        echo ""
        echo "    http://$IP_ADDRESS/tar1090/gain_messages.png"
        echo "    http://$IP_ADDRESS/tar1090/gain_distance.png"
        echo ""
        echo "... or see all the adsb-analysis plots you've made at:"
        echo ""
        echo "    http://$IP_ADDRESS/tar1090/adsb-analysis.html"
        echo ""

    else
        echo "An error occurred while running the analysis."
    fi
else
    echo "Failed to activate virtual environment. Please check that you have completed the setup."
fi

# Deactivate the virtual environment
deactivate
