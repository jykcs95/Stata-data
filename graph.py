import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from pathlib import Path
import numpy as np
import os

def multiPlot(file_paths, x_col='Vf', y_col='Im'):
    # 1. SETUP THE CANVAS
    fig, ax = plt.subplots(figsize=(10, 8))
    # Leave room at the bottom for the Reset and Save buttons
    plt.subplots_adjust(bottom=0.25) 

    all_datasets = []
    plot_lines = []

    # 2. LOAD AND CLEAN DATA
    for path in file_paths:
        df = pd.read_csv(path, skiprows =1)
        # Ensure T, Vf, and Im are numeric. errors='coerce' turns text into NaN.
        for col in ['T', 'Vf', 'Im']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # Drop rows that have NaN values to prevent "black box" text errors on axes
        df = df.dropna(subset=['T', 'Vf', 'Im'])

        # Store data, labels, and original dataframe for each file independently
        all_datasets.append({
            'df_orig': df,
            't': df['T'].values,
            'vf': df['Vf'].values,
            'im': df['Im'].values,
            'plot_x': df[x_col].values,
            'plot_y': df[y_col].values,
            'name': os.path.basename(path),
            'start_idx': 0,           # Tracking beginning cut-off
            'end_idx': len(df) - 1    # Tracking ending cut-off
        })
        
        # Initial plot for this file
        line, = ax.plot(df[x_col], df[y_col], alpha=0.7, label=os.path.basename(path))
        plot_lines.append(line)

    # 3. INTERACTIVE MARKERS
    # Red dot that follows the mouse
    preview_dot, = ax.plot([], [], 'ro', markersize=6, zorder=10)
    # The text box (annotation) for T, Vf, and Im values
    annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="white", ec="red", alpha=0.9))
    annot.set_visible(False)

    # Save original zoom limits for the Reset button
    fig.canvas.draw()
    orig_xlim, orig_ylim = ax.get_xlim(), ax.get_ylim()

    # 4. DISTANCE LOGIC (Find the nearest data point)
    def get_closest(event):
        if event.inaxes != ax: return None, None
        xl, yl = ax.get_xlim(), ax.get_ylim()
        # Calculate axis range to handle different scales (e.g. Time 0-8 vs Current 1e-6)
        dx, dy = (xl[1] - xl[0]), (yl[1] - yl[0]) 
        
        best_dist, best_match = float('inf'), None
        for i, d in enumerate(all_datasets):
            # Normalized Euclidean distance
            dists = ((d['plot_x'] - event.xdata)/dx)**2 + ((d['plot_y'] - event.ydata)/dy)**2
            idx = np.argmin(dists)
            if dists[idx] < best_dist:
                best_dist, best_match = dists[idx], (i, idx)
        return best_match, best_dist

    # 5. HOVER EVENT (Update Tooltip)
    def update_preview(event):
        match, dist = get_closest(event)
        if match and dist < 0.02: # Only show if mouse is close to a line
            ds_i, pt_i = match
            d = all_datasets[ds_i]
            x_p, y_p = d['plot_x'][pt_i], d['plot_y'][pt_i]
            
            preview_dot.set_data([x_p], [y_p])
            annot.xy = (x_p, y_p)
            # Display all three variables in the tooltip
            annot.set_text(f"File: {d['name']}\nTime (T): {d['t'][pt_i]:.4f}\n"
                        f"Voltage (Vf): {d['vf'][pt_i]:.4f}\n"
                        f"Current (Im): {d['im'][pt_i]:.4e}\n"
                        f"Left: Set End | Right: Set Start")
            annot.set_visible(True)
        else:
            annot.set_visible(False)
            preview_dot.set_data([], [])
        fig.canvas.draw_idle()

    # 6. CLICK EVENT (Truncate Start/End)
    def on_click(event):
        # Ignore clicks if the toolbar zoom/pan tools are active
        if event.inaxes != ax or fig.canvas.manager.toolbar.mode != '': return
        
        match, dist = get_closest(event)
        if match and dist < 0.02:
            ds_i, pt_i = match
            d = all_datasets[ds_i]
            
            if event.button == 1:   # Left Click: Sets the END of the data
                d['end_idx'] = pt_i
            elif event.button == 3: # Right Click: Sets the START of the data
                d['start_idx'] = pt_i
            
            # Re-slice the line data using the new start/end indices
            s, e = d['start_idx'], d['end_idx']
            if s < e:
                plot_lines[ds_i].set_xdata(d['plot_x'][s:e])
                plot_lines[ds_i].set_ydata(d['plot_y'][s:e])
            fig.canvas.draw_idle()

    # 7. RESET FUNCTION
    def reset(event):
        for i, d in enumerate(all_datasets):
            # Restore indices and data to original full length
            d['start_idx'], d['end_idx'] = 0, len(d['t']) - 1
            plot_lines[i].set_xdata(d['plot_x'])
            plot_lines[i].set_ydata(d['plot_y'])
        # Hard-reset zoom to original boundaries
        ax.set_xlim(orig_xlim)
        ax.set_ylim(orig_ylim)
        preview_dot.set_data([], [])
        annot.set_visible(False)
        fig.canvas.draw_idle()

    csv_files = glob.glob('results_CA/*.csv')

    def save_data(event):
        for d in all_datasets:
            s, e = d['start_idx'], d['end_idx']
            if s < e:
                truncated_df = d['df_orig'].iloc[s:e]
                new_name = f"truncated_{d['name']}"

                #storing the output into a new folder in the directory
                file_path = Path(f"truncated/truncated_{d['name']}")
                #create parent directories if they don't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)

                truncated_df.to_csv(file_path, index=False)
                print(f"Successfully saved: {new_name}")
            else:
                print(f"Error: {d['name']} has an invalid range (Start index is after End index).")

    # 9. UI BUTTONS
    ax_reset = plt.axes([0.3, 0.05, 0.15, 0.05])
    btn_reset = Button(ax_reset, 'Reset All', color='lightgray')
    btn_reset.on_clicked(reset)

    ax_save = plt.axes([0.55, 0.05, 0.15, 0.05])
    btn_save = Button(ax_save, 'Save CSVs', color='lightblue')
    btn_save.on_clicked(save_data)

    # 10. CONNECT EVENTS AND FINALIZE
    fig.canvas.mpl_connect("motion_notify_event", update_preview)
    fig.canvas.mpl_connect("button_press_event", on_click)
    
    plt.sca(ax)
    plt.xlabel(f"X-Axis: {x_col}")
    plt.ylabel(f"Y-Axis: {y_col}")
    plt.grid(True, linestyle='--', alpha=0.3)
    ax.legend(fontsize='x-small')
    plt.show()


if __name__ == "__main__":
    # 1. Load the CSV file
    file_path1 = Path("results_CV/output_dataCV.csv")
    file_path2 = Path("results_CA/output_dataCA.csv")

    files = [file_path1]

    multiPlot(files, x_col='Vf',y_col='Im')
