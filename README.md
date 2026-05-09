# Graph.py PROGRAM
# Interactive Data Truncator & Reference Tool 

A high-performance interactive plot utility built with Python. This tool allows users to visualize large CSV datasets, truncate them to specific ranges, and store critical reference points with pixel-perfect precision.

## ✨ Features

- **High-Performance Visualization:** Uses data decimation to keep the UI responsive while handling millions of points.
- **Precision Snapping:** Two-stage search algorithm ensures your clicks snap to the nearest actual data point, not just the visual approximation.
- **Smart Metadata:** Saves truncated data with custom `#` headers, making them easy to read back into Pandas or Excel while preserving experimental context.
- **Interactive Tooltips:** Real-time hover information with dynamic color coding for stored points.

## 🖱️ Controls


| Action | Control |
| :--- | :--- |
| **Zoom Both Axes** | Scroll Wheel |
| **Zoom X-Axis Only** | `Shift` + Scroll |
| **Zoom Y-Axis Only** | `Ctrl` + Scroll |
| **Pan / Move** | `Left Click` + Drag |
| **Set Start Point** | `Left Click` |
| **Set End Point** | `Right Click` |
| **Store Reference Point** | Hover + Press `S` |
| **Toggle Series** | Click Legend Icon |

## 📂 Exporting Data

When you click **Save CSVs**, the program creates a directory named `truncated_[Project_Name]/`. 

Each exported file includes a metadata header:
```csv
# Data Set Name: Project_Alpha
# Original File: measurement_01.csv
# Truncation Index Range: 150 to 850
# Truncation Vf Range: 0.1234 to 0.8543
# Truncation Im Range: 1.2000e-05 to 4.5000e-03
Column1, Column2, Stored_Point_X, Stored_Point_Y
...
```

## 🛠️ Installation & Requirements

If running from source, you will need:
- Python 3.x
- `pandas`
- `matplotlib`
- `numpy`

### Building the Executable
To create a standalone `.exe` for Windows:
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=icon.ico your_script.py
```

## ⚠️ Known Issues / Notes
- **File Locking:** The "Save" function will trigger an error if the target CSV is currently open in another program (like Microsoft Excel).
- **Permissions:** Ensure the program is run from a directory where it has "Write" permissions (e.g., Desktop or Documents).
