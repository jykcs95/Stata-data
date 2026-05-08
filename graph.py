import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import textwrap

import pandas as pd
from pathlib import Path

import numpy as np
import glob
import os

def wrap_label(text, width=20):
    return '\n'.join(textwrap.wrap(text, width))

def multiPlot(file_paths, data_name, x_col='Vf', y_col='Im'):
    # 1. SETUP THE CANVAS
    fig, ax = plt.subplots(figsize=(16, 9))
    # Leave room for buttons at bottom and legend on the right
    plt.subplots_adjust(bottom=0.25, right=0.8)
    
    all_datasets = []
    plot_lines = []

    # 2. LOAD AND CLEAN DATA
    for path in file_paths:
        df = pd.read_csv(path, skiprows=1)
        potential_cols = ['T', 'Vf', 'Im', x_col, y_col]
        actual_cols = [c for c in potential_cols if c in df.columns]
        for col in actual_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=[x_col, y_col]).reset_index(drop=True)

        file_name = os.path.basename(path)
        wrapped_name = wrap_label(file_name, width=40) 

        #Calculating how many points I want to plot depeneding on the data size
        num_points = len(df)
        step = max(1, num_points // 5000)

        all_datasets.append({
            'df_orig': df,
            'plot_x': df[x_col].values,
            'plot_y': df[y_col].values,
            'name': file_name,
            'wrapped_name': wrapped_name,
            'start_idx': 0,
            'end_idx': num_points - 1,
            'step': step,
            'extra': {col: df[col].values for col in actual_cols}
        })

        line, = ax.plot(df[x_col][::step], df[y_col][::step], alpha=0.7, label=wrapped_name)
        plot_lines.append(line)

    # 3. INTERACTIVE MARKERS
    preview_dot, = ax.plot([], [], 'ro', markersize=6, zorder=10)
    annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points", 
                        bbox=dict(boxstyle="round", fc="white", ec="red", alpha=0.9))
    annot.set_visible(False)

    fig.canvas.draw()
    orig_xlim, orig_ylim = ax.get_xlim(), ax.get_ylim()

    drag_state = {'is_panning': False, 'start_mouse_pix': (None, None), 'start_limits': (None, None), 'moved': False}

    # --- INTERNAL FUNCTIONS ---
    def zoom_fun(event):
        if event.inaxes != ax: return
        cur_xlim, cur_ylim = ax.get_xlim(), ax.get_ylim()
        dx, dy = cur_xlim[1] - cur_xlim[0], cur_ylim[1] - cur_ylim[0]
        scale_factor = 1/1.2 if event.button == 'up' else 1.2
        rel_x, rel_y = (cur_xlim[1] - event.xdata) / dx, (cur_ylim[1] - event.ydata) / dy
        ax.set_xlim([event.xdata - dx * scale_factor * (1 - rel_x), event.xdata + dx * scale_factor * rel_x])
        ax.set_ylim([event.ydata - dy * scale_factor * (1 - rel_y), event.ydata + dy * scale_factor * rel_y])
        fig.canvas.draw_idle()

    def get_closest(event):
        if event.inaxes != ax: return None, None
        xl, yl = ax.get_xlim(), ax.get_ylim()
        rx, ry = (xl[1] - xl[0]), (yl[1] - yl[0])
        best_dist, best_match = float('inf'), None
        for i, d in enumerate(all_datasets):
            if not plot_lines[i].get_visible(): continue
            file_step = d['step']
            xs, ys = d['plot_x'][::file_step], d['plot_y'][::file_step]
            dists = ((xs - event.xdata)/rx)**2 + ((ys - event.ydata)/ry)**2
            idx_sub = np.argmin(dists)
            if dists[idx_sub] < best_dist:
                best_dist, best_match = dists[idx_sub], (i, idx_sub * file_step)
        return best_match, best_dist

    def update_preview(event):
        if drag_state.get('is_panning', False): return
        match, dist = get_closest(event)
        if match and dist < 0.02:
            ds_i, pt_i = match
            d = all_datasets[ds_i]
            x_p, y_p = d['plot_x'][pt_i], d['plot_y'][pt_i]
            preview_dot.set_data([x_p], [y_p])
            annot.xy = (x_p, y_p)
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
        match, dist = get_closest(event)
        if match and dist < 0.02:
            ds_i, pt_i = match
            d = all_datasets[ds_i]
            if event.button == 1: d['end_idx'] = pt_i
            elif event.button == 3: d['start_idx'] = pt_i
            s, e, step = d['start_idx'], d['end_idx'], d['step']
            if s < e:
                plot_lines[ds_i].set_xdata(d['plot_x'][s:e:step])
                plot_lines[ds_i].set_ydata(d['plot_y'][s:e:step])
                fig.canvas.draw_idle()

    def reset(event):
        for i, d in enumerate(all_datasets):
            d['start_idx'], d['end_idx'] = 0, len(d['plot_x']) - 1
            plot_lines[i].set_xdata(d['plot_x'][::d['step']])
            plot_lines[i].set_ydata(d['plot_y'][::d['step']])
        ax.set_xlim(orig_xlim); ax.set_ylim(orig_ylim)
        fig.canvas.draw_idle()

    def reset_zoom(event):
        ax.set_xlim(orig_xlim); ax.set_ylim(orig_ylim)
        fig.canvas.draw_idle()

    def save_data(event):
        for d in all_datasets:
            s, e = d['start_idx'], d['end_idx']
            if s < e:
                file_path = Path(f"truncated_{data_name}/truncated_{d['name']}")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                d['df_orig'].iloc[s:e].to_csv(file_path, index=False)
                print(f"Saved: {d['name']}")

    def on_press(event):
        if event.inaxes != ax: return
        if event.button == 1:
            drag_state.update({'is_panning': True, 'moved': False, 'start_mouse_pix': (event.x, event.y), 'start_limits': (ax.get_xlim(), ax.get_ylim())})

    def on_drag(event):
        # 1. If we are dragging but the mouse leaves the plot area...
        if drag_state['is_panning'] and event.inaxes != ax:
            # FREEZE AND RELEASE: Stop the panning state immediately
            drag_state['is_panning'] = False
            return

        # 2. Standard hover logic if not dragging
        if not drag_state['is_panning']:
            if event.inaxes == ax:
                update_preview(event)
            return

        # 3. Standard Drag Logic (only runs if is_panning is True and inaxes == ax)
        dx_pix = event.x - drag_state['start_mouse_pix'][0]
        dy_pix = event.y - drag_state['start_mouse_pix'][1]
        
        if abs(dx_pix) > 2 or abs(dy_pix) > 2:
            drag_state['moved'] = True

        inv = ax.transData.inverted()
        p0 = inv.transform((0, 0))
        p1 = inv.transform((dx_pix, dy_pix))
        dx_data, dy_data = p1[0] - p0[0], p1[1] - p0[1]

        xlims, ylims = drag_state['start_limits']
        ax.set_xlim(xlims[0] - dx_data, xlims[1] - dx_data)
        ax.set_ylim(ylims[0] - dy_data, ylims[1] - dy_data)
        
        fig.canvas.draw_idle()

    def on_release(event):
        # If the mouse is outside when released, just kill the pan state and exit
        if event.inaxes != ax:
            drag_state['is_panning'] = False
            return

        if event.button == 1:
            # Only truncate if we stayed inside and didn't move much
            if not drag_state['moved']:
                handle_truncation(event)
            drag_state['is_panning'] = False
        elif event.button == 3:
            handle_truncation(event)

    # 9. UI BUTTONS - DEFINED HERE
    ax_zoom = plt.axes([0.15, 0.05, 0.15, 0.05])
    ax_reset = plt.axes([0.35, 0.05, 0.15, 0.05])
    ax_save = plt.axes([0.55, 0.05, 0.15, 0.05])

    btn_zoom = Button(ax_zoom, 'Reset Zoom')
    btn_zoom.on_clicked(reset_zoom)
    btn_reset = Button(ax_reset, 'Reset Data')
    btn_reset.on_clicked(reset)
    btn_save = Button(ax_save, 'Save CSVs')
    btn_save.on_clicked(save_data)

    # 10. LEGEND
    # Increase the margin on the right to accommodate long names (0.7 or lower)
    plt.subplots_adjust(bottom=0.25, right=0.65)

    # 10. LEGEND AND PICKER SETUP
    leg = ax.legend(
        fontsize='medium', 
        loc='upper left', 
        bbox_to_anchor=(1.02, 1), 
        labelspacing=1.2  # <--- Adds space so wrapped names don't overlap each other
    )
    leg.set_draggable(False) 
    plt.subplots_adjust(right=0.75, bottom=0.25)

    # Re-map the picker logic
    ax.map_legend_to_plot = {}
    for leg_line, plot_line in zip(leg.get_lines(), plot_lines):
        leg_line.set_picker(True)
        leg_line.set_pickradius(15)    # Bigger hitbox for the bigger font
        ax.map_legend_to_plot[leg_line] = plot_line

    def on_pick(event):
        if event.artist in ax.map_legend_to_plot:
            line = ax.map_legend_to_plot[event.artist]
            vis = not line.get_visible()
            line.set_visible(vis)
            event.artist.set_alpha(1.0 if vis else 0.2)
            fig.canvas.draw_idle()

    # 11. CONNECT & SHOW
    fig.canvas.mpl_connect('pick_event', on_pick)
    fig.canvas.mpl_connect("scroll_event", zoom_fun)
    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_drag)
    fig.canvas.mpl_connect("button_release_event", on_release)

    # Use the ax object specifically to keep labels pinned to the plot area
    ax.set_title(f"{data_name} Files", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel(x_col, fontsize=12, labelpad=10)
    ax.set_ylabel(y_col, fontsize=12, labelpad=10)

    # Shift the plot up slightly more to create a "safe zone" for the labels
    # Increase 'bottom' from 0.25 to 0.3 if the buttons are still too close
    plt.subplots_adjust(bottom=0.3, right=0.7) 
    ax.btn_zoom, ax.btn_reset, ax.btn_save = btn_zoom, btn_reset, btn_save

def getFiles():
    return glob.glob("*.csv")

def checkFileType(file):
    header = pd.read_csv(file, nrows=0).columns.tolist()
    match header[0]:
        case "CA":
            x,y = "Im","T"
        case "CC":
            x1, y1 = "Im", "T"
            x2, y2 = "Q", "T"
            return [[x1,y1],[x2,y2],header[0]]
        case "CV":
            x,y = "Im","Vf"
        case "LSV":
            x,y = "Im","Vf"
        case "OCP":
            x,y = "Vf","T"
        case "PEIS":
            x,y = "Zimag","Zreal"
    return x,y,header[0]


if __name__ == "__main__":
    #Get all the files in the folder
    files = getFiles()

    #Check what x and y value we are going to use
    #x at index 1, y at index 2, type at index 3
    if files:
        xy_name = checkFileType(files[0])
        #CC types need two different graphs
        if xy_name[2] == "CC":
            multiPlot(files, xy_name[2], xy_name[0][0], xy_name[0][1])
            multiPlot(files, xy_name[2], xy_name[1][0], xy_name[1][1])
        else:
            multiPlot(files, xy_name[2], xy_name[0], xy_name[1])
        plt.show()
        
