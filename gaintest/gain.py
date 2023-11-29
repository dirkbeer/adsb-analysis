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

OUTPUT_FILE = 'data.csv'
STATS_FILE = '/run/readsb/stats.json'
AUTO_GAIN = -10
INTERVAL_NAME = 'last1min'
WAIT_TIME = 10  
original_gain = None

def get_current_gain():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with open(STATS_FILE, 'r') as file:
                stats_data = json.load(file)
                return stats_data['gain_db']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"Attempt {attempt + 1}: Could not read current gain value ({e}). Retrying...")
            time.sleep(2)

    print("Unable to read current gain after several attempts.")
    return None

def restore_original_gain():
    if original_gain is not None:
        command = f"sudo readsb-gain {original_gain}"
        try:
            result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Restored original gain to {original_gain}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to restore original gain. Error: {e.stderr}")

def install_rtl_sdr():
    if "rtl-sdr" not in subprocess.getoutput("dpkg -l"):
        print("Installing rtl-sdr package...")
        subprocess.run(["sudo", "apt-get", "update"])
        subprocess.run(["sudo", "apt-get", "install", "-y", "rtl-sdr"])

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

def setup_output_file(file_name, mode):
    header = "end_time,run,gain_set,gain_actual,signal,peak_signal,noise,snr,modes,bad,p_bad,messages_valid,max_distance"
    print(header)
    if mode == "overwrite":
        with open(file_name, "w") as file:
            file.write(header + '\n')
    elif not os.path.isfile(file_name):
        with open(file_name, "w") as file:
            file.write(header + '\n')

def get_stats_json():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with open(STATS_FILE, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Attempt {attempt + 1}: Error reading stats file ({e}).")
            if attempt < max_attempts - 1:  # Check if more attempts should be made
                time.sleep(2)  # Wait for 2 seconds before the next attempt
            else:
                return None  # Return None after all attempts failed


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
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite the output file')
    parser.add_argument('--min_gain', type=float, default=0.0, help='Minimum gain value')
    parser.add_argument('--max_gain', type=float, default=60.0, help='Maximum gain value')

    args = parser.parse_args()

    # store the current gain so it can be restored later
    original_gain = get_current_gain()
    if original_gain == None:
        print(f"Unable to read current gain setting. Check that {STATS_FILE} exists. Exiting ...")
        sys.exit(0)
    else:
        print(f"Current gain setting of {original_gain} will be restored when the program exits")

    install_rtl_sdr()
    gain_values = get_gain_values(AUTO_GAIN, args.gain_step, args.min_gain, args.max_gain)
    output_mode = "overwrite" if args.overwrite else "append"

    print("Testing gain values:", ', '.join(map(str, gain_values)))
    print("Runs at each value: ", args.runs)
    print("Expected run time:  ", round(args.runs * WAIT_TIME * len(gain_values) / 60, 1), "minutes")
    if args.overwrite:
        print("Overwriting existing data file ...")
    print("Saving data to:     ", OUTPUT_FILE)
    print("")

    setup_output_file(OUTPUT_FILE, output_mode)

    for run in range(1, args.runs + 1):
        shuffled_gain_values = random.sample(gain_values, len(gain_values))

        for gain in shuffled_gain_values:
            error_message = subprocess.getoutput(f"sudo readsb-gain {gain}")

            if "Error, invalid gain!" in error_message:
                print(f"Invalid gain value: {gain}, skipping")
                continue

            data = get_stats_json()
            if data and "now" in data:
                now_timestamp = data["now"]
                target_time = now_timestamp + WAIT_TIME
                current_time = time.time()
                sleep_time = max(0, target_time - current_time)
                time.sleep(sleep_time)
            else:
                time.sleep(WAIT_TIME + 60)

            data = get_stats_json()

            max_retries = 3  # Number of retries
            retry_delay = 5  # Seconds to wait before retrying

            for attempt in range(max_retries):
                try:
                    end_time = data[INTERVAL_NAME]['end']
                    gain_actual = data['gain_db']
                    signal = data[INTERVAL_NAME]['local']['signal']
                    peak_signal = data[INTERVAL_NAME]['local']['peak_signal']
                    noise = data[INTERVAL_NAME]['local']['noise']
                    modes = data[INTERVAL_NAME]['local']['modes']
                    bad = data[INTERVAL_NAME]['local']['bad']
                    messages_valid = data[INTERVAL_NAME]['messages_valid']
                    max_distance = data[INTERVAL_NAME]['max_distance']
                    break  # Break out of the loop if successful
                except KeyError as e:
                    if attempt < max_retries - 1:
                        print(f"Key error: {e}. Data might be incomplete or corrupted. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        data = get_stats_json()  # Re-fetch the data
                    else:
                        print(f"Key error: {e}. Maximum retries reached. Skipping this iteration.")
                        continue  # Skip this iteration after all retries


            snr = round(signal - noise, 1)
            p_bad = round(bad / modes, 3)

            data = [end_time, run, gain, gain_actual, signal, peak_signal, noise, snr, modes, bad, p_bad, messages_valid, max_distance]
            print(', '.join(map(str, data)))

            with open(OUTPUT_FILE, 'a') as file:
                writer = csv.writer(file)
                writer.writerow(data)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    restore_original_gain()

