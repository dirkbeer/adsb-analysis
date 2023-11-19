***Manual install and execution***

**First-time setup**

1) Install the required packages on your Wingbits Raspberry Pi:
   ```bash
   sudo apt install git python3-pip python3-venv libopenblas-dev libopenjp2-7
   ```
2) Clone this repository
   ```bash
   git clone https://github.com/dirkbeer/adsb-analysis.git
   ```
3) Go to the adsb-analysis folder
   ```bash
   cd adsb-analysis
   ```
4) Create a Python virtual environment and start it: 
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
    You should see your prompt change to something like
    ```bash
    (venv) sdr@sdr:~/adsb-analysis $
    ```
5) Install the required Python packages (this may take a while): 
   ```bash
   pip install -r requirements.txt
   ```

**Running the analysis**
1) Go to the adsb-analysis directory. If you're not already at a (venv) prompt, run
   ```bash
   source venv/bin/activate
   ```
3) Run the script. It reads your home location from the readsb config file, processes the data, calculates detection probability and then saves a file called `receiver_performance.png`
   ```bash
    ./analyze.py
    ```
4) Copy the image to the web server directory:
    ```bash
    sudo cp ./receiver_performance.png /usr/local/share/tar1090/html
    ```
5) Go view the receiver performance plot at
    ```txt
    http://sdr.local/tar1090/receiver_performance.png
    ```
    (replace `sdr.local` with the name or ip address of your Wingbits Raspberry Pi)
