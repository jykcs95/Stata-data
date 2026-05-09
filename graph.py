import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import textwrap
import pandas as pd
from pathlib import Path
import numpy as np
import glob
import os

# Helper to split long filenames into multiple lines for the legend
def wrap_label(text, width=20):
    return '\n'.join(textwrap.wrap(text, width))

def multiPlot(file_paths, data_name, x_col='Vf', y_col='Im'):
    # 1. SETUP THE CANVAS
    fig, ax = plt.subplots(figsize=(16, 9))

    # DISABLE default key bindings so 's' doesn't trigger the save dialog
    plt.rcParams['keymap.save'] = '' 

    # Standard margins to prevent UI/Legend overlap
    plt.subplots_adjust(bottom=0.25, right=0.8)
    
    all_datasets = []
    plot_lines = []

    # 2. LOAD AND CLEAN DATA
    for path in file_paths:
        df = pd.read_csv(path, skiprows=1, comment='#')
        
        # Identify valid numeric columns for this specific plot
        potential_cols = ['T', 'Vf', 'Im', x_col, y_col]
        actual_cols = [c for c in potential_cols if c in df.columns]
        
        for col in actual_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Remove NaNs and reset index to ensure click indices match the dataframe rows
        df = df.dropna(subset=[x_col, y_col]).reset_index(drop=True)
        
        file_name = os.path.basename(path)
        wrapped_name = wrap_label(file_name, width=40)

        m, = ax.plot([], [], 'kx', markersize=10, markeredgewidth=3, zorder=11)

        # Performance: Only plot ~7000 points visually to keep UI responsive
        num_points = len(df)
        step = max(1, num_points // 7000)

        all_datasets.append({
            'df_orig': df,
            'plot_x': df[x_col].values,
            'plot_y': df[y_col].values,
            'name': file_name,
            'wrapped_name': wrapped_name,
            'start_idx': 0,
            'stored_idx': None,
            'marker': m,
            'end_idx': num_points - 1,
            'step': step, # Store decimation step for later re-plotting
            'extra': {col: df[col].values for col in actual_cols}
        })

        # Plot decimated version for speed
        line, = ax.plot(df[x_col][::step], df[y_col][::step], alpha=0.7, label=wrapped_name)
        plot_lines.append(line)

    # 3. INTERACTIVE UI ELEMENTS
    preview_dot, = ax.plot([], [], 'ro', markersize=6, zorder=20)
    annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points", 
                        bbox=dict(boxstyle="round", fc="white", ec="red", alpha=0.9),
                        zorder=20)
    annot.set_visible(False)

    # Capture original view for the Reset buttons
    fig.canvas.draw()
    orig_xlim, orig_ylim = ax.get_xlim(), ax.get_ylim()

    # Shared state for the click-and-drag logic
    drag_state = {'is_panning': False, 'start_mouse_pix': (None, None), 'start_limits': (None, None), 'moved': False}

    # --- INTERNAL INTERACTIVE FUNCTIONS ---

    def zoom_fun(event):
        if event.inaxes != ax: return
        
        # Get current limits
        cur_xlim, cur_ylim = ax.get_xlim(), ax.get_ylim()
        dx, dy = cur_xlim[1] - cur_xlim[0], cur_ylim[1] - cur_ylim[0]
        
        # Zoom speed (1.2x)
        scale_factor = 1/1.2 if event.button == 'up' else 1.2
        
        # Calculate mouse position relative to the axis (0.0 to 1.0)
        rel_x = (cur_xlim[1] - event.xdata) / dx
        rel_y = (cur_ylim[1] - event.ydata) / dy

        # Determine which axes to zoom based on keys
        # event.key is provided by Matplotlib for scroll events!
        zoom_x = True
        zoom_y = True
        
        if event.key == 'shift':      # Hold Shift to zoom ONLY X
            zoom_y = False
        elif event.key == 'control':  # Hold Ctrl to zoom ONLY Y
            zoom_x = False

        if zoom_x:
            ax.set_xlim([
                event.xdata - dx * scale_factor * (1 - rel_x), 
                event.xdata + dx * scale_factor * rel_x
            ])
        
        if zoom_y:
            ax.set_ylim([
                event.ydata - dy * scale_factor * (1 - rel_y), 
                event.ydata + dy * scale_factor * rel_y
            ])
            
        fig.canvas.draw_idle()

    def get_closest(event):
        if event.inaxes != ax: return None, None
        xl, yl = ax.get_xlim(), ax.get_ylim()
        rx, ry = (xl[1] - xl[0]), (yl[1] - yl[0])
        best_dist, best_match = float('inf'), None

        for i, d in enumerate(all_datasets):
            if not plot_lines[i].get_visible(): continue
            
            # 1. Find the neighborhood in the decimated data
            file_step = d['step']
            xs_sub, ys_sub = d['plot_x'][::file_step], d['plot_y'][::file_step]
            dists_sub = ((xs_sub - event.xdata)/rx)**2 + ((ys_sub - event.ydata)/ry)**2
            idx_sub = np.argmin(dists_sub)
            
            # 2. Refine search: Look at the FULL data around that neighborhood
            center_idx = idx_sub * file_step
            search_start = max(0, center_idx - file_step)
            search_end = min(len(d['plot_x']), center_idx + file_step)
            
            xs_refine = d['plot_x'][search_start:search_end]
            ys_refine = d['plot_y'][search_start:search_end]
            
            dists_refine = ((xs_refine - event.xdata)/rx)**2 + ((ys_refine - event.ydata)/ry)**2
            idx_refine = np.argmin(dists_refine)
            
            # Calculate the absolute index in the original dataframe
            final_idx = search_start + idx_refine
            final_dist = dists_refine[idx_refine]

            if final_dist < best_dist:
                best_dist, best_match = final_dist, (i, final_idx)
                
        return best_match, best_dist

    def update_preview(event):
        """Update the hover tooltip box"""
        if drag_state.get('is_panning', False): return
        match, dist = get_closest(event)
        if match and dist < 0.02:
            ds_i, pt_i = match
            d = all_datasets[ds_i]
            x_p, y_p = d['plot_x'][pt_i], d['plot_y'][pt_i]
            # If this file has a stored point, make the box green
            if d.get('stored_idx') is not None:
                annot.get_bbox_patch().set_edgecolor('black')
                annot.get_bbox_patch().set_facecolor('#f0f0f0') # Light grey
            else:
                annot.get_bbox_patch().set_edgecolor('red')
                annot.get_bbox_patch().set_facecolor('white')

            preview_dot.set_data([x_p], [y_p])
            annot.xy = (x_p, y_p)
            
            # Dynamically build info lines
            info = [f"File: {d['name']}", f"{x_col}: {x_p:.4f}", f"{y_col}: {y_p:.4e}"]
            for k, v in d['extra'].items():
                if k not in [x_col, y_col]: info.append(f"{k}: {v[pt_i]:.4f}")

            annot.set_text("\n".join(info))
            annot.set_visible(True)
        else:
            annot.set_visible(False)
            preview_dot.set_data([], [])
        fig.canvas.draw_idle()

    def handle_truncation(event):
        """Set new Start (Right Click) or End (Left Click) points for saving"""
        match, dist = get_closest(event)
        if match and dist < 0.02:
            ds_i, pt_i = match
            d = all_datasets[ds_i]
            if event.button == 1: 
                d['start_idx'] = pt_i
            elif event.button == 3: 
                d['end_idx'] = pt_i

            s, e, step = d['start_idx'], d['end_idx'], d['step']
            if s < e:
                plot_lines[ds_i].set_xdata(d['plot_x'][s:e+1])
                plot_lines[ds_i].set_ydata(d['plot_y'][s:e+1])
                fig.canvas.draw_idle()

    def reset(event):
        """Restore all data to full original length"""
        for i, d in enumerate(all_datasets):
            d['stored_idx'] = None # Clear stored points
            d['marker'].set_data([], [])
            d['start_idx'], d['end_idx'] = 0, len(d['plot_x']) - 1
            plot_lines[i].set_xdata(d['plot_x'][::d['step']])
            plot_lines[i].set_ydata(d['plot_y'][::d['step']])
        ax.set_xlim(orig_xlim); ax.set_ylim(orig_ylim)
        fig.canvas.draw_idle()

    def reset_zoom(event):
        """Restore zoom only, keep data truncation"""
        ax.set_xlim(orig_xlim); ax.set_ylim(orig_ylim)
        fig.canvas.draw_idle()

    def save_data(event):
        """Save the high-resolution truncated data to CSV"""
        for d in all_datasets:
            s, e = d['start_idx'], d['end_idx']
            if s < e:
                truncated_df = d['df_orig'].iloc[s:e].copy()

                truncated_df['Stored_Point_X'] = np.nan
                truncated_df['Stored_Point_Y'] = np.nan
                
                # If a point was stored, get its values and add to the CSV
                if d['stored_idx'] is not None:
                    m_idx = d['stored_idx']
                    truncated_df.iloc[0, truncated_df.columns.get_loc('Stored_Point_X')] = d['plot_x'][m_idx]
                    truncated_df.iloc[0, truncated_df.columns.get_loc('Stored_Point_Y')] = d['plot_y'][m_idx]

                file_path = Path(f"truncated_{data_name}/truncated_{d['name']}")
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Get physical values for the range
                x_start, x_end = d['plot_x'][s], d['plot_x'][e]
                y_start, y_end = d['plot_y'][s], d['plot_y'][e]

                with open(file_path, 'w', encoding='utf-8') as f:
                    # Metadata Headers
                    f.write(f"{data_name}\n")
                    f.write(f"# Original File: {d['name']}\n")
                    f.write(f"# Truncation Index Range: {s} to {e}\n")
                    f.write(f"# Truncation {x_col} Range: {x_start:.4f} to {x_end:.4f}\n")
                    f.write(f"# Truncation {y_col} Range: {y_start:.4e} to {y_end:.4e}\n")
                    
                    # Write the CSV data
                    truncated_df.to_csv(f, index=False, lineterminator='\n')

                print(f"Saved {d['name']} with range: {x_start:.2f} to {x_end:.2f}")


    def on_press(event):
        """Record starting point for panning"""
        if event.inaxes != ax: return
        if event.button == 1:
            drag_state.update({
                'is_panning': True, 
                'moved': False, 
                'start_mouse_pix': (event.x, event.y), 
                'start_limits': (ax.get_xlim(), ax.get_ylim())
            })

    def on_key(event):
        if event.key == 's' and event.inaxes == ax:
            match, dist = get_closest(event)
            
            if match:
                # UNPACK THE TUPLE: match is (ds_i, pt_i)
                ds_i, pt_i = match 
                
                # Now ds_i is an integer (e.g., 0)
                d = all_datasets[ds_i] 
                
                d['stored_idx'] = pt_i
                d['marker'].set_data([d['plot_x'][pt_i]], [d['plot_y'][pt_i]])
                
                print(f"Stored point for {d['name']}")
                fig.canvas.draw_idle()

    def on_drag(event):
        """Handle panning movement and freeze if leaving axes"""
        if drag_state['is_panning'] and event.inaxes != ax:
            drag_state['is_panning'] = False # Snap-freeze if cursor leaves plot
            return
        if not drag_state['is_panning']:
            if event.inaxes == ax: update_preview(event)
            return
        
        # Calculate pixel-based movement to avoid 'shaking'
        dx_pix = event.x - drag_state['start_mouse_pix'][0]
        dy_pix = event.y - drag_state['start_mouse_pix'][1]
        
        if abs(dx_pix) > 2 or abs(dy_pix) > 2: drag_state['moved'] = True
        
        # Convert pixels to data units for xlim/ylim shift
        inv = ax.transData.inverted()
        p0 = inv.transform((0, 0))
        p1 = inv.transform((dx_pix, dy_pix))
        dx_data, dy_data = p1[0] - p0[0], p1[1] - p0[1]
        
        xlims, ylims = drag_state['start_limits']
        ax.set_xlim(xlims[0] - dx_data, xlims[1] - dx_data)
        ax.set_ylim(ylims[0] - dy_data, ylims[1] - dy_data)
        fig.canvas.draw_idle()

    def on_release(event):
        """Release pan state or trigger truncation click"""
        if event.inaxes != ax:
            drag_state['is_panning'] = False
            return
        if event.button == 1:
            if not drag_state['moved']: 
                handle_truncation(event)
            drag_state['is_panning'] = False
        elif event.button == 3:
            handle_truncation(event)

    # 4. UI BUTTON DEFINITIONS
    ax_zoom = plt.axes([0.15, 0.05, 0.15, 0.05])
    ax_reset = plt.axes([0.35, 0.05, 0.15, 0.05])
    ax_save = plt.axes([0.55, 0.05, 0.15, 0.05])

    btn_zoom = Button(ax_zoom, 'Reset Zoom')
    btn_zoom.on_clicked(reset_zoom)
    btn_reset = Button(ax_reset, 'Reset Data')
    btn_reset.on_clicked(reset)
    btn_save = Button(ax_save, 'Save CSVs')
    btn_save.on_clicked(save_data)

    controls_text = (
        "ZOOM CONTROLS:\n"
        "• Scroll: Zoom Both\n"
        "• Shift + Scroll: X-Axis Only\n"
        "• Ctrl + Scroll: Y-Axis Only\n\n"
        "TRUNCATE & STORE:\n"
        "• Left Click: Set Start\n"
        "• Right Click: Set End\n"
        "• Press 'S': Store Reference Point'"
    )

    # Place it in the bottom-left margin (coordinates are 0-1 of the whole window)
    fig.text(0.98, 0.02, controls_text, fontsize=9, verticalalignment='bottom', horizontalalignment='right', multialignment='left',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='gray'))

    # 5. LEGEND & TOGGLE LOGIC
    leg = ax.legend(
        fontsize='medium', 
        loc='upper left', 
        bbox_to_anchor=(1.02, 1), 
        labelspacing=1.2
    )
    #legend stays behind the tool tip
    leg.set_zorder(5)

    leg.set_draggable(False) 
    plt.subplots_adjust(right=0.75, bottom=0.3)

    # Link legend colored lines to the plot lines for toggling
    ax.map_legend_to_plot = {}
    for leg_line, plot_line in zip(leg.get_lines(), plot_lines):
        leg_line.set_picker(True)
        leg_line.set_pickradius(15)
        ax.map_legend_to_plot[leg_line] = plot_line

    def on_pick(event):
        """Toggle line visibility when clicking the legend icon"""
        if event.artist in ax.map_legend_to_plot:
            plot_line = ax.map_legend_to_plot[event.artist]
            vis = not plot_line.get_visible()
            plot_line.set_visible(vis)
            
            # Find the dataset that matches this line and hide its marker too
            for d in all_datasets:
                if d['name'] in event.artist.get_label(): # matching by name
                    d['marker'].set_visible(vis)
            
            event.artist.set_alpha(1.0 if vis else 0.2)
            fig.canvas.draw_idle()


    # 6. CONNECT EVENTS
    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.mpl_connect('pick_event', on_pick)
    fig.canvas.mpl_connect("scroll_event", zoom_fun)
    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_drag)
    fig.canvas.mpl_connect("button_release_event", on_release)

    # Title and Labels
    ax.set_title(f"{data_name} Files", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel(x_col, fontsize=12, labelpad=10)
    ax.set_ylabel(y_col, fontsize=12, labelpad=10)

    # Protect button references from Python's garbage collector
    ax.btn_zoom, ax.btn_reset, ax.btn_save = btn_zoom, btn_reset, btn_save

def getFiles():
    return glob.glob("*.csv")

def checkFileType(file):
    header = pd.read_csv(file, nrows=0).columns.tolist()
    match header[0]:
        case "CA": x,y = "T","Im"
        case "CC": 
            # CC usually requires viewing both Charge (Q) and Current (Im) vs Time
            x1, y1 =  "T","Im"
            x2, y2 =  "T","Q"
            return [[x1,y1],[x2,y2],header[0]]
        case "CV": x,y = "Vf","Im"
        case "LSV": x,y = "Vf","Im"
        case "OCP": x,y = "T","Vf"
        case "PEIS": x,y = "Zreal","Zimag"
    return x,y,header[0]

if __name__ == "__main__":
    files = getFiles()
    if files:
        xy_name = checkFileType(files[0])
        # Open two windows for CC data, one for others
        if xy_name[2] == "CC":
            multiPlot(files, xy_name[2], xy_name[0][0], xy_name[0][1])
            multiPlot(files, xy_name[2], xy_name[1][0], xy_name[1][1])
        else:
            multiPlot(files, xy_name[2], xy_name[0], xy_name[1])
        plt.show()
