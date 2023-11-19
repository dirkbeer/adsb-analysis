#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
from kneed import KneeLocator
import matplotlib.pyplot as plt
from scipy.stats import binom

def binom_confint(successes, trials):
    if trials == 0:
        return np.nan, np.nan
    ci_low, ci_high = binom.interval(0.95, n=trials, p=successes/trials)
    return ci_low/trials, ci_high/trials

def extract_upper_bound(interval):
    interval_str = str(interval).strip('()[]')
    parts = interval_str.split(',')
    return float(parts[1].strip())

def main(dynamic_limits, figure_filename, use_all):
    # Read the CSV file
    dat = pd.read_csv('output.csv', header=None)
    dat.columns = ["aircraft_id", "distance", "present"]

    # Bin the distances into intervals and calculate the proportion of presence
    dat['distance_bin'] = pd.cut(dat['distance'], bins=np.arange(0, dat['distance'].max() + 10, 10), include_lowest=True, right=False)

    # Calculate the proportion of presence in each bin
    binned_data = dat.groupby('distance_bin', observed=True).agg(
        present_count=('present', 'sum'),
        total_count=('present', 'count')
    ).reset_index()
    binned_data['proportion'] = binned_data['present_count'] / binned_data['total_count']

    # Filter the data to include only rows where total_count > 30 to ensure valid statistics
    if not use_all:
        pre_filter_bin_count = len(binned_data)
        binned_data = binned_data[binned_data['total_count'] >= 30]
        post_filter_bin_count = len(binned_data)
        filtered_bins = pre_filter_bin_count - post_filter_bin_count 
        if filtered_bins > 1:        # It's normal for the last bin to have too few messages, don't bother the user if there is only one bin filtered
            print(f"Filtering {filtered_bins} range bins because they had to few messages for valid statistics. Collect more data, or set --use-all on the command line to override.")

    # Calculate the confidence intervals
    binned_data[['conf_low', 'conf_high']] = binned_data.apply(
        lambda row: binom_confint(row['present_count'], row['total_count']),
        axis=1, result_type='expand'
    )
    
    # Extract the far ranges from the bin name
    binned_data['distance'] = binned_data['distance_bin'].apply(extract_upper_bound)

    # Find the knee in the curve using filtered data
    kn = KneeLocator(binned_data['distance'], binned_data['proportion'], 
                     curve='concave', direction='decreasing',
                     S=1.0, interp_method='polynomial', online=True)
    knee_point = (kn.knee, binned_data.loc[binned_data['distance'] == kn.knee, 'proportion'].values[0] if kn.knee is not None else None)

    # Plot with confidence intervals using filtered data
    plt.figure(figsize=(10, 8))
    plt.errorbar(binned_data['distance'], binned_data['proportion'], 
                 yerr=[binned_data['proportion'] - binned_data['conf_low'], 
                       binned_data['conf_high'] - binned_data['proportion']], fmt='o')

    if knee_point[1] is not None:
        plt.scatter(*knee_point, color='red')
        plt.annotate(f"Knee at {knee_point[0]} nautical miles", (knee_point[0], knee_point[1]))

    plt.title("ADS-B Receiver Performance / Message Reliability")
    plt.xlabel("Distance (nautical miles)")
    plt.ylabel("Probability of Detection")
    if not dynamic_limits:
        plt.ylim(0.7, 1.0)
        plt.xlim(0.0, 300.0)
    plt.grid(True)
    plt.show()
    plt.text(0.95, 0.01, "https://github.com/dirkbeer/adsb-analysis", fontsize=8, ha='right', transform=plt.gcf().transFigure)

    # Save the plot
    plt.savefig(figure_filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to analyze ADS-B Receiver Performance")
    parser.add_argument('--dynamic-limits', '-dl', action='store_true', help='Use dynamic limits to ensure all data is visible')
    parser.add_argument('--use-all', '-a', action='store_true', help='Calculate statistics on range bins even if there is insufficient data for valid statistics')
    parser.add_argument('--figure-filename', '-ffn', type=str, default='receiver_performance.png', help='Filename for the saved plot')
    args = parser.parse_args()

    main(args.dynamic_limits, args.figure_filename, args.use_all)
