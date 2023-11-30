#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import subprocess
import os

DATA_DIR = './data'

def human_readable_size(size, decimal_places=2):
    """Convert bytes to human-readable file sizes."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0

def get_file_names(data_dir, file_extension):
    """Retrieve all files with file_extension in the data directory and sort them by file age."""
    files = [f for f in os.listdir(data_dir) if f.endswith(file_extension)]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
    return files

def display_files(files):
    """Display files with their sizes."""
    for idx, file in enumerate(files, 1):
        file_path = os.path.join(DATA_DIR, file)
        file_size = human_readable_size(os.path.getsize(file_path))
        print(f"{idx}. {file} ({file_size})")

def get_user_choice(files, data_dir):
    """Prompt the user to choose a file."""
    choice = int(input("\nEnter the number of the file you want to choose: "))
    if 1 <= choice <= len(files):
        return os.path.join(data_dir, files[choice - 1])
    raise ValueError("Invalid choice.")

def read_data(file_path):
    """Reads data from a CSV file."""
    return pd.read_csv(file_path)

def fit_polynomial(df, x_column, y_column, order=2):
    """Fits a polynomial of specified order to the data."""
    coeffs = np.polyfit(df[x_column], df[y_column], order)
    return np.poly1d(coeffs)

def plot_data_with_fit(df, x, y, poly_function, plot_file):
    """Plots data points with polynomial fit and saves the plot."""
    plt.figure()
    plt.scatter(df[x], df[y], label='Data Points')
    x_range = np.linspace(df[x].min(), df[x].max(), 500)
    plt.plot(x_range, poly_function(x_range), color='red', label='Polynomial Fit')
    plt.xlabel(x.replace('_', ' ').title())
    plt.ylabel(y.replace('_', ' ').title())
    plt.title(f'{y.replace("_", " ").title()} by {x.replace("_", " ").title()} with Polynomial Fit')
    plt.legend()
    plt.savefig(plot_file)

def plot_data(df, x, y, plot_file):
    """Plots data points and saves the plot."""
    plt.figure()
    plt.scatter(df[x], df[y], label='Data Points')
    plt.xlabel(x.replace('_', ' ').title())
    plt.ylabel(y.replace('_', ' ').title())
    plt.title(f'{y.replace("_", " ").title()} by {x.replace("_", " ").title()} with Polynomial Fit')
    plt.legend()
    plt.savefig(plot_file)

def copy_file(source, destination):
    """Copies a file from source to destination using subprocess."""
    command = ['sudo', 'cp', source, destination]
    try:
        subprocess.run(command, check=True)
        print("File copied successfully.")
    except subprocess.CalledProcessError:
        print("Error occurred while copying the file.")

def calculate_adjusted_values(df, column, poly_function):
    """Calculates adjusted values based on polynomial function."""
    df[f'{column}_adjusted'] = df[column] / poly_function(df['end_time'])

def calculate_median_adjusted_values(df, group_column, value_column):
    """Calculates adjusted values based on run medians."""
    grouped = df.groupby(group_column)[value_column]
    medians = grouped.median()
    df[f'{column}_adjusted'] = df[value_column] / medians

def calculate_median_adjusted_values(df, group_column, value_column):
    """Calculates adjusted values based on group medians."""
    medians = df.groupby(group_column)[value_column].transform('median')
    df[f'{value_column}_adjusted'] = df[value_column] / medians
    return df


def plot_confidence_intervals(df, group_column, value_column, plot_file):
    """Plots means with confidence intervals and adds labeled, rotated grid lines at unique gain values."""
    grouped = df.groupby(group_column)[value_column]
    means = grouped.mean()
    std_err = grouped.sem()
    ci = std_err * stats.t.ppf((1 + 0.95) / 2., grouped.count() - 1)

    plt.figure()
    plt.errorbar(means.index, means, yerr=ci, fmt='o', ecolor='r', capsize=5)
    #plt.ylim([0, max(means + ci)])
    
    # Adding grid lines and labels at unique gain values
    unique_gains = df[group_column].unique()
    for gain in unique_gains:
        plt.axvline(x=gain, color='grey', linestyle='--', linewidth=0.5)
        plt.text(gain, plt.gca().get_ylim()[0]+plt.gca().get_ylim()[1]*0.01, f'{gain}', fontsize=8, rotation=90, verticalalignment='bottom')

    plt.xlabel(group_column.replace('_', ' ').title())
    plt.ylabel(f'Mean of {value_column.replace("_", " ").title()}')
    plt.title(f'Mean and Confidence Intervals of {value_column.replace("_", " ").title()} by {group_column.replace("_", " ").title()}')
    plt.grid(True, axis='y')  # Adding horizontal grid lines for better readability
    plt.savefig(plot_file)


def main():

    files = get_file_names(DATA_DIR, '.csv')
    if not files:
        raise ValueError("No .csv files found in the data directory.")
    display_files(files)
    chosen_file = get_user_choice(files, DATA_DIR)

    df = read_data(chosen_file)

    calculate_median_adjusted_values(df, 'run', 'messages_valid')

    plot_confidence_intervals(df, 'gain_actual', 'messages_valid_adjusted', 'gain_messages.png')
    copy_file('./gain_messages.png', '/usr/local/share/tar1090/html')

    plot_confidence_intervals(df, 'gain_actual', 'max_distance', 'gain_distance.png')
    copy_file('./gain_distance.png', '/usr/local/share/tar1090/html')

if __name__ == "__main__":
    main()
