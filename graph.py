import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import glob

if __name__ == "__main__":
    '''
    # 1. Load the CSV file
    file_path = Path("results_CA/output_dataCA.csv")

    csv_files = glob.glob('results_CA/*.csv')
    df = pd.read_csv(file_path, skiprows=1)
    # 1. Find the first index where it hits or exceeds 0.25
    condition = df['Im'] >= .25
    if condition.any():
        stop_index = condition.idxmax()
        # 2. SLICE EXCLUSIVELY: Stop at the row BEFORE the jump
        # This prevents the line from even reaching the high value
        df_final = df.iloc[:stop_index]  
        print(stop_index)
    else:
        df_final = df
    '''

    csv_files = glob.glob('results_CA/*.csv')

    for file in csv_files:
        df = pd.read_csv(file, skiprows=1)
        plt.plot(df['Vf'], df['Im'], label=file.split('/'[-1]))
    # 3. Plot
    plt.xlabel("Vf")
    plt.ylabel("Im")
    plt.title('Combined Data from Multiple CSVs')
    plt.legend()
    plt.show()