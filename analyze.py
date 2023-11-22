#!/usr/bin/env python3
import sys

def is_running_in_venv():
    return sys.prefix != sys.base_prefix

if is_running_in_venv():
    import subprocess
    import gzip
    import json
    import glob
    import math
    import datetime
    import re
    import argparse
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.stats import binom
    from scipy.optimize import curve_fit
else:
    print("Not running in the virtual environment. Run \"source venv/bin/activate\" first. ")
    sys.exit(1)

# Global variables from the first script
data_dir = '/run/tar1090'
config_file_path = '/etc/default/readsb'
device_name_path = '/etc/wingbits/device'

def get_wingbits_id():
    try:
        with open(device_name_path, 'r') as file:
            device_name = file.read().strip()
    except FileNotFoundError:
        device_name = None
    return device_name

def get_gain():
    command = "ps aux | grep readsb"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    ps_output = out.decode()
    if err:
        print("Error:", err.decode())
    else:
        gain_regex = r'--gain ([\-\d\.]+)'
        gain_match = re.search(gain_regex, ps_output)
        if gain_match:
            gain_value = gain_match.group(1)
        else:
            gain_value = None
    return gain_value


def extract_lat_lon_from_config(config_file_path):
    with open(config_file_path, 'r') as file:
        config_content = file.read()

    lat_lon_pattern = r"--lat\s+([+-]?\d+\.\d+)\s+--lon\s+([+-]?\d+\.\d+)"
    match = re.search(lat_lon_pattern, config_content)

    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon
    else:
        print("Latitude and longitude not found in the readsb config file.\n")
        print("Set your location using \"sudo readsb-set-location <lat> <lon>\" and try again.\n")
        exit(1)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of the Earth in kilometers
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000  # Distance in meters

def extract_data(file_content, latitude_home, longitude_home):
    json_data = json.loads(file_content)
    extracted_data = []
    for entry in json_data.get("files", []):
        time = entry.get("now") * 1000
        for aircraft in entry.get("aircraft", []):
            aircraft_id = aircraft[0]
            latitude, longitude = aircraft[4] if len(aircraft) > 4 else None, aircraft[5] if len(aircraft) > 5 else None
            if latitude is not None and longitude is not None:
                distance = haversine(latitude, longitude, latitude_home, longitude_home)
                extracted_data.append([aircraft_id, time, latitude, longitude, distance])
    return extracted_data

# Class definition from the first script
class Data:
    def __init__(self, row):
        self.aircraft_id, self.time, self.latitude, self.longitude, self.distance = row
        self.distance /= 1852  # Convert to nautical miles
        self.datetime = datetime.datetime.utcfromtimestamp(self.time / 1000)

def piecewise_linear(x, x0, y0, m):
    return np.piecewise(x, [x < x0, x >= x0], [lambda x: y0, lambda x: m * (x - x0) + y0])

def get_knee_point(binned_data):
    if len(binned_data) < 4:
        print("Not enough data for reliable range assessment.")
        return None
    binned_data['distance'] = binned_data['distance'].astype(float)
    piecewise_params0 = (np.mean(binned_data['distance']), np.max(binned_data['proportion']),
                         (np.min(binned_data['proportion']) - np.max(binned_data['proportion']))
                         / (np.max(binned_data['distance']) - np.mean(binned_data['distance'])))

    fitted_params, _ = curve_fit(piecewise_linear,
                                 binned_data['distance'].values,
                                 binned_data['proportion'].values,
                                 p0=piecewise_params0)
    return fitted_params

def binom_confint(successes, trials):
    if trials == 0:
        return np.nan, np.nan
    ci_low, ci_high = binom.interval(0.95, n=trials, p=successes/trials)
    return ci_low/trials, ci_high/trials

def extract_upper_bound(interval):
    interval_str = str(interval).strip('()[]')
    parts = interval_str.split(',')
    return float(parts[1].strip())

# Integrated main function
def main():

    # Process command line arguments
    parser = argparse.ArgumentParser(description="Script to analyze ADS-B Receiver Performance")
    parser.add_argument('--dynamic-limits', '-dl', action='store_true', help='Use dynamic limits to ensure all data is visible')
    parser.add_argument('--use-all', '-a', action='store_true', help='Calculate statistics on range bins even if there is insufficient data for valid statistics')
    parser.add_argument('--figure-filename', '-ffn', type=str, default='receiver_performance.png', help='Filename for the saved plot')
    args = parser.parse_args()

    print("Loading data ...")

    # Extract latitude and longitude from config
    latitude_home, longitude_home = extract_lat_lon_from_config(config_file_path)

    # Load and extract data
    file_pattern = f"{data_dir}/chunk_*.gz"
    filenames = glob.glob(file_pattern)
    all_data = []

    for filename in filenames:
        try:
            with gzip.open(filename, 'rt') as f:
                file_content = f.read()
                extracted_data = extract_data(file_content, latitude_home, longitude_home)
                all_data.extend([Data(row) for row in extracted_data])
        except FileNotFoundError:
            print(f"File not found: {filename}")
            continue
        except OSError as e:
            print(f"OS error occurred with file {filename}: {e}")
            continue

    # After processing all data, calculate the earliest and latest dates
    if all_data:
        earliest_date = min(d.datetime for d in all_data)
        latest_date = max(d.datetime for d in all_data)
        # Calculate the time difference
        time_difference = latest_date - earliest_date
        total_seconds = time_difference.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        # Format the date range string with hours and minutes
        date_range_str = (f"{earliest_date.strftime('%Y-%m-%d %H:%M')} to "
                          f"{latest_date.strftime('%Y-%m-%d %H:%M')} "
                          f"({hours} hours, {minutes} minutes)")
    else:
        date_range_str = "No data available"

    print("Analyzing reliability ...")
    times = {d.time for d in all_data}
    data_per_time_and_aircraft = {}
    for d in all_data:
        if d.time not in data_per_time_and_aircraft:
            data_per_time_and_aircraft[d.time] = {}
        data_per_time_and_aircraft[d.time][d.aircraft_id] = d

    output_data = []
    sorted_times = sorted(times)
    for i, current_time in enumerate(sorted_times):
        next_time = sorted_times[i + 1] if i + 1 < len(sorted_times) else None
        for aircraft_id, d in data_per_time_and_aircraft[current_time].items():
            present_in_next = next_time is not None and aircraft_id in data_per_time_and_aircraft[next_time]
            output_data.append((aircraft_id, d.distance, int(present_in_next)))

    dat = pd.DataFrame(output_data, columns=["aircraft_id", "distance", "present"])

    # Bin the distances into intervals and calculate the proportion of presence
    dat['distance_bin'] = pd.cut(dat['distance'], bins=np.arange(0, dat['distance'].max() + 10, 10), include_lowest=True, right=False)

    # Calculate the proportion of presence in each bin
    binned_data = dat.groupby('distance_bin', observed=True).agg(
        present_count=('present', 'sum'),
        total_count=('present', 'count')
    ).reset_index()
    binned_data['proportion'] = binned_data['present_count'] / binned_data['total_count']

    print(binned_data[['distance_bin', 'proportion', 'total_count']].to_string(index=False))

    print("Calculating statistics ...")
    # Filter the data to include only rows where total_count > 30 to ensure valid statistics
    if not args.use_all:
        pre_filter_bin_count = len(binned_data)
        binned_data = binned_data[binned_data['total_count'] >= 30]
        post_filter_bin_count = len(binned_data)
        filtered_bins = pre_filter_bin_count - post_filter_bin_count
        if filtered_bins > 1:        # It's normal for the last bin to have too few messages, don't bother the user if there is only one bin filtered
            print(f"Filtering {filtered_bins} range bins because they had too few messages for valid statistics. Uncomment \"./analyze.py --use-all\" in run_analysis.sh to override")

    # Calculate the confidence intervals
    binned_data[['conf_low', 'conf_high']] = binned_data.apply(
        lambda row: binom_confint(row['present_count'], row['total_count']),
        axis=1, result_type='expand'
    )

    # Extract the far ranges from the bin name
    binned_data['distance'] = binned_data['distance_bin'].apply(extract_upper_bound)

    device_name = get_wingbits_id()
    gain_value = get_gain()

    print("")
    print(f"Wingbits ID: {device_name}")
    print(f"Gain:        {gain_value}")
    print(f"Data Range:  {date_range_str}")
    print("")

    # Find the knee point
    fitted_params = get_knee_point(binned_data)
    if fitted_params is not None:
        (x, y, m) = fitted_params
        print(f"Estimated ...")
        print(f"   Near range reliability:          {round(100*y,1)}%")
        print(f"   Maximum reliable range:          {round(x,1)} nautical miles")
        print(f"   Far range reliability loss:      {round(1000*m,2)}% each 10 nautical miles")

    print("")
    print("Plotting results ...")
    plt.figure(figsize=(10, 8))

    # Plot with confidence intervals using filtered data
    plt.errorbar(binned_data['distance'], binned_data['proportion'],
                 yerr=[binned_data['proportion'] - binned_data['conf_low'],
                       binned_data['conf_high'] - binned_data['proportion']], fmt='o')

    if fitted_params is not None:
        # Plot the piecewise linear fit
        plt.plot([0, x], [y, y], color='lightgray', linewidth=3)
        delta = max(binned_data['distance']) - x
        x1 = x + delta
        y1 = y + m * delta
        plt.plot([x, x1], [y, y1], color='lightgray', linewidth=3)
        plt.text(20, 0.83, f"Wingbits ID:              {device_name}", fontsize=12)
        plt.text(20, 0.82, f"Current gain setting:   {gain_value}", fontsize=12)
        plt.text(20, 0.81, f"Near range reliability:  {int(round(100*fitted_params[1], 0))}%", fontsize=12)
        plt.text(20, 0.80, f"Max reliable range:     {int(round(fitted_params[0], 0))} nautical miles", fontsize=12)

    plt.title(f"ADS-B Receiver Performance / Maximum Reliable Range")
    plt.xlabel("Distance (nautical miles)")
    plt.ylabel("Reliability (probability of detection)")
    if not args.dynamic_limits:
        plt.ylim(0.7, 1.0)
        plt.xlim(0.0, 300.0)
    plt.grid(True)

    plt.text(0.05, 0.01, f"Data Range: {date_range_str}", fontsize=8, ha='left', transform=plt.gcf().transFigure)
    plt.text(0.95, 0.01, "https://github.com/dirkbeer/adsb-analysis", fontsize=8, ha='right', transform=plt.gcf().transFigure)

    # Save the plot
    plt.savefig(args.figure_filename)

if __name__ == "__main__":
    main()
