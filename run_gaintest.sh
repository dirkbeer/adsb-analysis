#!/bin/bash

# Change to the directory of the script
cd "$(dirname "$0")"

# Check if ../output directory exists, and create it if not
if [[ ! -d "../data" ]]; then
    mkdir -p "../data"
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

# Run the gain test script with defaults
./src/gaintest.py
#./src/gaintest.py --runs 30 --gain_step 1 --min_gain 20

# Check if gaintest.py ran successfully
if [[ $? -eq 0 ]]; then
    echo ""
    echo "Gain test complete."

    # Attempt to retrieve the local IP address of the Raspberry Pi
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    if [[ -z "$IP_ADDRESS" ]]; then
        echo "Could not determine the IP address."
        IP_ADDRESS="sdr.local" # default value if IP address cannot be determined
    fi

    echo "Gain test result copied to ~/adsb-analysis/data/gain_*.csv."
    echo ""
    echo "Run ~/adsb-analysis/run_gainplot.sh next to plot the results."
    echo ""
    echo "Then consider running gainplot.py directly to collect more detailed gain data,"
    echo "e.g. /"nohup ./src/gaintest.py --runs 30 --gain_step 1 --min_gain 20/""
    echo ""

else
    echo "An error occurred while running the gain test."
fi
