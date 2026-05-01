import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

if __name__ == "__main__":
    # 1. Load the CSV file
    file_path = Path("results_CV/output_dataCV.csv")

    df = pd.read_csv(file_path, skiprows=1)


    # 2. Select columns for X and Y axes
    # df.plot(x='ColumnName1', y='ColumnName2') # Quick Pandas plot
    plt.plot(df['Vf'], df['Im'], marker='o', linestyle='-', color='b')

    # 3. Add labels and title
    plt.title('output_dataCA')
    plt.xlabel('Time')
    plt.ylabel('Vf')

    # 4. Show the graph
    plt.show()