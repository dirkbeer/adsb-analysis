#!/usr/bin/env python3

import argparse
import subprocess
import csv
import time
import random
import json
import os
import signal
import sys
import time
from datetime import datetime

OUTPUT_FILE_PATH = '../data' # assumes script will be run from the src directory
STATS_FILE = '/run/readsb/stats.json'
AUTO_GAIN = -10
INTERVAL_NAME = 'last1min'
INTERVAL = 60
SLACK = 5
original_gain = None

def read_json_with_retries(file_path, expected_keys, max_attempts=10, wait_seconds=5):
    """
    Attempts to read a JSON file with specified expected keys.

    :param file_path: Path to the JSON file.
    :param expected_keys: Set of keys expected to be present in the JSON file.
    :param max_attempts: Maximum number of attempts to read the file.
    :param wait_seconds: Seconds to wait between attempts.
    :return: Parsed JSON content if successful, None otherwise.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

                # Check if all expected keys are present
                if all(key in data for key in expected_keys):
                    return data
        except:
            pass    
        # Wait before retrying
        time.sleep(wait_seconds)
        attempt += 1

    print("Failed to read the JSON file after multiple attempts.")
    return None


def restore_original_gain():
    global original_gain
    if original_gain is not None:
        command = f"sudo readsb-gain {original_gain}"
        try:
            result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Restored original gain to {original_gain}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to restore original gain. Error: {e.stderr}")

def get_gain_values(autogain, interval, min_gain, max_gain):
    subprocess.run(["sudo", "systemctl", "stop", "readsb"])
    output = subprocess.getoutput("rtl_test -t")
    gain_line = next((line for line in output.split('\n') if 'gain' in line.lower()), "")
    all_gain_values = gain_line.split(": ")[-1].split() if gain_line else []
    initial_gain_values = [float(gain) for gain in all_gain_values if min_gain <= float(gain) <= max_gain]
    gain_values = initial_gain_values[::interval]
    gain_values.append(str(autogain))
    subprocess.run(["sudo", "systemctl", "start", "readsb"])
    return gain_values

def signal_handler(signum, frame):
    print(f"Signal {signum} received, cleaning up...")
    try:
        restore_original_gain()
    except Exception as e:
        print(f"Error restoring original gain: {e}")
    sys.exit(1)

# Signal handling registration
for sig in [signal.SIGINT, signal.SIGTERM]:
    signal.signal(sig, signal_handler)

# Main code block
try:
    parser = argparse.ArgumentParser(description='Collect signal and message data for a range of gain values')
    parser.add_argument('-r', '--runs', type=int, default=3, help='Number of runs')
    parser.add_argument('-i', '--gain-step', type=int, default=3, help='Gain step interval')
    parser.add_argument('--min_gain', '-min', type=float, default=0.0, help='Minimum gain value')
    parser.add_argument('--max_gain', '-max', type=float, default=60.0, help='Maximum gain value')

    args = parser.parse_args()

    # store the current gain so it can be restored later
    original_gain = read_json_with_retries(STATS_FILE, {'gain_db'})['gain_db']
    if original_gain == None:
        print(f"Unable to read current gain setting. Check that {STATS_FILE} exists. Exiting ...")
        sys.exit(0)
    else:
        print(f"Current gain setting of {original_gain} will be restored when the program exits")

    gain_values = get_gain_values(AUTO_GAIN, args.gain_step, args.min_gain, args.max_gain)

    print("Testing gain values:", ', '.join(map(str, gain_values)))
    print("Runs at each value: ", args.runs)
    print("Expected run time:  ~", round(args.runs * 1.5 * INTERVAL * len(gain_values) / 60, 1), "minutes")
    print("")

    now = datetime.now()
    formatted_date_time = now.strftime("%Y_%m_%d_%H%M")
    filename = f"{OUTPUT_FILE_PATH}/gain_{formatted_date_time}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    header = "end_time,run,gain_set,gain_actual,signal,peak_signal,noise,snr,modes,bad,p_bad,messages_valid,max_distance"
    print(header)
    with open(filename, "w") as file:
        file.write(header + '\n')

    for run in range(1, args.runs + 1):
        shuffled_gain_values = random.sample(gain_values, len(gain_values))

        for gain in shuffled_gain_values:
            # set the new gain
            error_message = subprocess.getoutput(f"sudo readsb-gain {gain}")
            if "Error, invalid gain!" in error_message:
                print(f"Invalid gain value: {gain}, skipping")
                continue
            # find out when the the stats file was last written
            data = read_json_with_retries(STATS_FILE,{'now', 'gain_db', INTERVAL_NAME})
            last_write = data['now']
            # figure out how long to wait to record a full period at this gain setting
            next_write = last_write + INTERVAL
            current_time = time.time()
            time_until_next_write = next_write - current_time
            sleep_time = time_until_next_write + INTERVAL + SLACK
            time.sleep(sleep_time)
            # get the data
            data = read_json_with_retries(STATS_FILE,{'gain_db', INTERVAL_NAME})
            end_time = data[INTERVAL_NAME]['end']
            gain_actual = data['gain_db']
            signal = data[INTERVAL_NAME]['local']['signal']
            peak_signal = data[INTERVAL_NAME]['local']['peak_signal']
            noise = data[INTERVAL_NAME]['local']['noise']
            modes = data[INTERVAL_NAME]['local']['modes']
            bad = data[INTERVAL_NAME]['local']['bad']
            messages_valid = data[INTERVAL_NAME]['messages_valid']
            max_distance = data[INTERVAL_NAME]['max_distance']

            snr = round(signal - noise, 1)
            p_bad = round(bad / modes, 3)

            data = [end_time, run, gain, gain_actual, signal, peak_signal, noise, snr, modes, bad, p_bad, messages_valid, max_distance]
            print(', '.join(map(str, data)))

            with open(filename, 'a') as file:
                writer = csv.writer(file)
                writer.writerow(data)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    restore_original_gain()

