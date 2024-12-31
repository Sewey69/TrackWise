#maybe there is some redondances, but my eyes began to hurt so i didn't bother removing them
import tkinter as tk
from tkinter.ttk import Style
import numpy as np
from customtkinter import *
import sqlite3
import time
import pygetwindow as gw
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import *
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, date, timedelta
from tkinter import ttk
import subprocess
from PIL import Image, ImageTk
import calendar
import matplotlib.dates as mdates
import re
from collections import defaultdict
import os
import sys
import socket
import threading
import winreg as reg

#shwaya variablouet
tracking_process = None
tracking = False
animate_job = None

#preparing database
db_path = os.path.join(os.path.dirname(sys.executable), 'usage_tracker.db')
subprocess.run(["attrib","+H","usage_tracker.db"],check=True)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT NOT NULL,
        usage_time INTEGER NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
print("Database and table created successfully.")

# the main utility script 
def run_script():
    global tracking_process, tracking
    if (tracking_process is None or tracking_process.poll() is not None) and tracking is False:
        def log_usage(app_name, usage_time):
            local_conn = sqlite3.connect(db_path)
            local_cursor = local_conn.cursor()

            try:
                print(f"Logging usage: {app_name}, Time: {int(usage_time)} seconds")
                local_cursor.execute(
                    '''INSERT INTO usage (app_name, usage_time, date) VALUES (?, ?, CURRENT_TIMESTAMP)''',
                    (app_name, int(usage_time)))
                local_conn.commit()
            except sqlite3.Error as e:
                print(f"Database error: {e}")
            finally:
                local_conn.close()

        def track_usage():
            global tracking
            last_app = None
            start_time = None

            while tracking:
                active_window = gw.getActiveWindow()
                if active_window:
                    app_name = active_window.title

                    if app_name != last_app:
                        if last_app and start_time:
                            end_time = time.time()
                            usage_time = end_time - start_time
                            log_usage(last_app, usage_time)

                        last_app = app_name
                        start_time = time.time()
                time.sleep(1)

            print("Tracking stopped.")
            update_status("Tracking stopped.")

        def check_for_stop():
            global tracking
            while tracking:
                try:
                    user_input = input("Type 'stop' to end tracking: ")
                    if user_input == "stop":
                        print("Stopping tracking...")
                        tracking = False
                except EOFError:
                    break

        def start_tracking_thread():
            global tracking
            tracking = True
            track_usage()

        tracking_thread = threading.Thread(target=start_tracking_thread, daemon=True)
        tracking_thread.start()

        update_status("Tracking started...")
        print("Tracking started.")
    else:
        print("Tracking is already running.")
        update_status("Tracking is already running.")
def stop_script():
    global tracking
    if tracking:
        tracking = False
        print("Tracking stopped.")
        update_status("Tracking stopped.")

        output_path = os.path.join(os.getcwd(), 'usage_data.csv')
        subprocess.run(["attrib","+H" , "usage_data.csv"], check=True)
        cone = sqlite3.connect(os.path.join(os.getcwd(), 'usage_tracker.db'))
        try:
            cone = sqlite3.connect(os.path.join(os.getcwd(), 'usage_tracker.db'))
            df = pd.read_sql_query("SELECT * FROM usage", conn)
            if not df.empty:
                df.to_csv(output_path, index=False)
                subprocess.run(["attrib", "+H", output_path], check=True)
                print(f"CSV successfully created at: {output_path}")
            else:
                print("No data to export.")
        except Exception as e:
            print(f"Error exporting data: {e}")
        finally:
            cone.close()

        update_status("Tracking stopped and data exported.")
    else:
        print("Tracking is not currently running.")
        update_status("Tracking is not currently running.")

def update_status(message):
    stop_animation()
    if message.endswith("..."):
        base_message = message[:-3]
        animate_dots(base_message)
    else:
        status_label.configure(text=message)
def animate_dots(base_message, current_step=0):
    global animate_job
    dots = '.' * (current_step % 4)
    status_label.configure(text=f"{base_message}{dots}")
    animate_job = root.after(500, animate_dots, base_message, current_step + 1)
def stop_animation():
    global animate_job
    if animate_job:
        root.after_cancel(animate_job)
        animate_job = None

def save_and_exit():
    root.quit()

# the show_graphs interface
def show_graph_window():
    if os.path.exists('usage_data.csv'):
        graph_window = Toplevel()
        graph_window.title("TrackWise")
        graph_window.geometry("1010x960")
        style = Style(graph_window)
        style.theme_use('clam')
        graph_window.resizable(False, False)
        graph_window.iconbitmap("clock.ico")


        app_label = Label(graph_window, text="Select App", font=('Segoe UI', 14))
        app_label.grid(row=0, column=0, padx=(120,0), pady=(15,0), sticky=W)

        def extract_substrings(name):
            name = re.sub(r'[^a-zA-Z0-9/\-_\s.]', '', name.lower())
            name = re.sub(r'^[^a-zA-Z]+', '', name)
            substrings = set()
            for i in range(len(name)):
                for j in range(i + 6, len(name) + 1):
                    substrings.add(name[i:j])
            return substrings

        def find_best_match(name1, name2):
            substrings1 = extract_substrings(name1)
            substrings2 = extract_substrings(name2)
            common = substrings1.intersection(substrings2)
            if common:
                return max(common, key=len)
            return None

        df = pd.read_csv("usage_data.csv")

        names = df['app_name'].tolist()
        grouped_names = defaultdict(list)

        for i, name1 in enumerate(names):
            for j, name2 in enumerate(names):
                if i != j:
                    best_match = find_best_match(name1, name2)
                    if best_match:
                        grouped_names[best_match].append(i)
                        grouped_names[best_match].append(j)

        for common, indices in grouped_names.items():
            indices = set(indices)
            for index in indices:
                df.at[index, 'app_name'] = common

        df['app_name'] = df['app_name'].apply(lambda x: re.sub(r'^[^a-zA-Z]+', '', x).capitalize())

        df.to_csv("updated_usage_data.csv", index=False)

        print(df)

        app_options = list(df['app_name'].unique()) + ["All Apps", "Top 5"]
        app_dropdown = ttk.Combobox(graph_window, values=app_options, font=('Segoe UI', 10))
        app_dropdown.set("All Apps")
        app_dropdown.grid(row=0, column=1, padx=10, pady=(15,0))

        time_label = Label(graph_window, text="Select Time Span", font=('Segoe UI', 14))
        time_label.grid(row=1, column=0, padx=(120,0), pady=5, sticky=W)

        time_options = ["Day", "Month", "All Time"]
        time_dropdown = ttk.Combobox(graph_window, values=time_options, font=('Segoe UI', 10))
        time_dropdown.set("All Time")
        time_dropdown.grid(row=1, column=1, padx=10, pady=5)

        graph_type_label = Label(graph_window, text="Select Graph Type", font=('Segoe UI', 14))
        graph_type_label.grid(row=2, column=0, padx=(120,0), pady=5, sticky=W)

        graph_type_options = ["Bar Chart", "Pie Chart"]
        graph_type_dropdown = ttk.Combobox(graph_window, values=graph_type_options, font=('Segoe UI', 10))
        graph_type_dropdown.set("Bar Chart")
        graph_type_dropdown.grid(row=2, column=1, padx=10, pady=5)

        graph_frame = Frame(graph_window)
        graph_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky=N+S+E+W)

        button_frame = Frame(graph_window)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)

        submit_button = Button(button_frame,
                               text="Generate Graph",
                               command=lambda: generate_graph(df, app_dropdown.get(), time_dropdown.get(),
                                                              graph_type_dropdown.get(), graph_frame),
                               font=('Segoe UI', 16),
                               fg="white",
                               bg="#3498db",
                               relief="flat",
                               bd=0,
                               highlightthickness=0,
                               padx=20, pady=10,
                               width=18, height=1)

        def on_enter(e):
            submit_button['bg'] = "#2980b9"
            submit_button['cursor'] = "hand2"

        def on_leave(e):
            submit_button['bg'] = "#3498db"
            submit_button['cursor'] = "arrow"

        def on_click(e):
            submit_button['bg'] = "#2980b9"

        def on_release(e):
            submit_button['bg'] = "#2980b9"

        submit_button.bind("<Enter>", on_enter)
        submit_button.bind("<Leave>", on_leave)
        submit_button.bind("<ButtonPress-1>", on_click)
        submit_button.bind("<ButtonRelease-1>", on_release)

        submit_button.pack(pady=10, padx=10)

        graph_window.grid_rowconfigure(3, weight=1)
        graph_window.grid_columnconfigure(1, weight=1)
    else:
        messagebox.showerror("Error", "No data available. Please track first.\n If tracking is running, stop it and try again.")

#create the graphs based on the choices of the user
def generate_graph(df, selected_app, time_span, graph_type, graph_frame):
    for widget in graph_frame.winfo_children():
        widget.destroy()

    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    if selected_app != "All Apps" and selected_app != "Top 5":
        df_others = df[df['app_name'] != selected_app]
        df_app = df[df['app_name'] == selected_app]
        if time_span == "Day":
            today = datetime.now()
            df_app = df_app[df_app['date'].dt.date == today.date()]

            if not df_app.empty:
                if graph_type == "Bar Chart":
                    print("single app, bar one day")
                    plot_bar_chart_single(df_app, selected_app, graph_frame)

                elif graph_type == "Pie Chart":
                    total_usage_time = df_app['usage_time'].sum()
                    others_usage_time = df['usage_time'].sum() - total_usage_time
                    pie_data = pd.DataFrame({
                        'app_name': [selected_app, 'Others'],
                        'usage_time': [total_usage_time, others_usage_time]
                    })
                    plot_pie_chart(pie_data, graph_frame, f'{selected_app} usage Today, {today.strftime("%d/%m/%Y")}')

                else:
                    Label(graph_frame, text=f"No data available for the selected {time_span.lower()} period.",
                          fg="red").grid(
                        row=0, column=0, columnspan=3, sticky="nsew", padx=20, pady=10)
                    print("No data available for the selected app today.")

        elif time_span == "Month":
            current_month = datetime.now().month
            df_app = df[df['date'].dt.month == current_month]
            total_usage_time = df_app['usage_time'].sum()

            others_usage_time = df_others["usage_time"].sum()

            pie_data = pd.DataFrame({
                'app_name': [selected_app, 'Others'],
                'usage_time': [total_usage_time, others_usage_time]
            })

            if graph_type == "Bar Chart":
                plot_bar_chart_current_month(df_app, selected_app, graph_frame)
            elif graph_type == "Pie Chart":
                plot_pie_chart(pie_data, graph_frame)

        else:
            total_usage_time = df_app['usage_time'].sum()

            others_usage_time = df['usage_time'].sum() - total_usage_time

            pie_data = pd.DataFrame({
                'app_name': [selected_app, 'Others'],
                'usage_time': [total_usage_time, others_usage_time]
            })
            if graph_type == "Pie Chart":
                plot_pie_chart(pie_data, graph_frame)
            elif graph_type == "Bar Chart":
                plot_bar_chart_last_40_days(df_app, selected_app, graph_frame)
            else:
                print("No data available for the selected app.")
                Label(graph_frame, text=f"No data available for the selected {time_span.lower()} period.",
                      fg="red").grid(
                    row=0, column=0, columnspan=3, sticky="nsew", padx=20, pady=10)

    elif selected_app == "Top 5":
        if time_span == "Month":
            current_month = datetime.now().month
            df_this_month = df[df['date'].dt.month == current_month]
            df_top5 = df_this_month.groupby('app_name')['usage_time'].sum().nlargest(5).reset_index()

            if df_top5.empty:
                for widget in graph_frame.winfo_children():
                    widget.destroy()
                Label(graph_frame, text=f"No data available for the selected {time_span.lower()} period.",
                      fg="red").grid(
                    row=0, column=0, columnspan=3, sticky="nsew", padx=20, pady=10)
                return

            if graph_type.lower() == "pie chart":
                plot_pie_chart(df_top5, graph_frame)
            else:
                plot_bar_chart(df_top5, graph_frame)

        elif time_span == "Day":
            current_date = datetime.now().date()
            df_today = df[df['date'].dt.date == current_date]
            df_top5 = df_today.groupby('app_name')['usage_time'].sum().nlargest(5).reset_index()

            if df_top5.empty:
                for widget in graph_frame.winfo_children():
                    widget.destroy()
                Label(graph_frame, text=f"No data available for the selected {time_span.lower()} period.",
                      fg="red").grid(
                    row=0, column=0, columnspan=3, sticky="nsew", padx=20, pady=10)
                return

            if graph_type.lower() == "pie chart":
                plot_pie_chart(df_top5, graph_frame)
            else:
                plot_bar_chart(df_top5, graph_frame, " in " + str(current_date))

        else:
            top_apps = df.groupby('app_name')['usage_time'].sum().nlargest(5).reset_index()

            if top_apps.empty:
                for widget in graph_frame.winfo_children():
                    widget.destroy()
                Label(graph_frame, text="No data available for all time.", fg="red").grid(row=0, column=0)
                return

            if graph_type.lower() == "pie chart":
                plot_pie_chart(top_apps, graph_frame)
            else:
                plot_bar_chart(top_apps, graph_frame)

    # ALL APPS
    else:
        if time_span == "Month":
            current_month = datetime.now().month
            filtered_data = df[df['date'].dt.month == current_month].groupby('app_name')[
                'usage_time'].sum().reset_index()
        elif time_span == "Day":
            current_date = datetime.now().date()
            filtered_data = df[df['date'].dt.date == current_date].groupby('app_name')['usage_time'].sum().reset_index()
        else:
            filtered_data = df.groupby('app_name')['usage_time'].sum().reset_index()

        if filtered_data.empty:
            for widget in graph_frame.winfo_children():
                widget.destroy()
            Label(graph_frame, text=f"No data available for the selected {time_span.lower()} period.", fg="red").grid(
                row=0, column=0, columnspan=3, sticky="nsew", padx=20, pady=10)
            return

        if graph_type.lower() == "pie chart":
            plot_pie_chart(filtered_data, graph_frame)
        else:
            plot_bar_chart(filtered_data, graph_frame)

        if graph_type.lower() == "pie chart":
            plot_pie_chart(filtered_data, graph_frame)
        else:
            plot_bar_chart(filtered_data, graph_frame,)

def plot_pie_chart(df, graph_frame, message = "App Usage Percentage"):
    figure, ax = plt.subplots(figsize=(10, 7))

    df['app_name'] = df['app_name'].apply(lambda x: x[:20] + '...' if len(x) > 15 else x)

    colors = [
        "#3498db", "#5dade2", "#85c1e9", "#aed6f1",
        "#2e86c1", "#2874a6", "#21618c", "#1b4f72",
        "#73c6b6", "#5499c7"
    ]

    def autopct_more_than_10(pct):
        return f'{pct:.1f}%' if pct > 10 else ''

    ax.pie(df['usage_time'], labels=df['app_name'], autopct=autopct_more_than_10, startangle=90, textprops={'fontsize': 10, 'font' : 'Segoe UI'}, colors=colors)
    ax.set_title(message, fontsize=17, fontdict={'fontsize': 14, 'font' : 'Segoe UI'})

    canvas = FigureCanvasTkAgg(figure, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0, sticky=N+S+E+W)
def plot_bar_chart(df, graph_frame, message=""):
    figure, ax = plt.subplots(figsize=(10, 7))

    df['app_name'] = df['app_name'].apply(lambda x: x[:15] + '...' if len(x) > 15 else x)

    colors = plt.cm.Blues(np.linspace(0.3, 1, len(df)))

    ax.bar(df['app_name'], df['usage_time'], color=colors)

    ax.bar(df['app_name'], df['usage_time'], color=colors)

    ax.set_ylabel('Usage Time (seconds)' + message, fontsize=12)
    ax.set_title('Apps Usage Time', fontsize=14)

    ax.tick_params(axis='x', labelsize=10)
    plt.tight_layout()
    ax.grid(axis='y', linestyle='None', alpha=0.7)

    canvas = FigureCanvasTkAgg(figure, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0, sticky=N+S+E+W)
def plot_bar_chart_single(df, selected_app, graph_frame):
    print("you got to the single func")
    today = date.today()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    df_app = df[(df['app_name'] == selected_app) & (df['date'].dt.date == today)].copy()
    print(df_app.head())
    if df_app.empty:
        for widget in graph_frame.winfo_children():
            widget.destroy()
        Label(graph_frame, text="No data available for the selected app today.", fg="red").grid(row=0, column=0)
        return


    df_app['hour'] = df_app['date'].dt.hour
    hourly_usage = df_app.groupby('hour')['usage_time'].sum().reset_index()
    print(hourly_usage.head())

    if hourly_usage.empty:
        for widget in graph_frame.winfo_children():
            widget.destroy()
        Label(graph_frame, text="No hourly data available for the selected app today.", fg="red").grid(row=0, column=0)
        return

    for widget in graph_frame.winfo_children():
        widget.destroy()
    plt.close('all')

    colors = plt.cm.Blues(np.linspace(0.3, 1, len(df)))

    figure, ax = plt.subplots(figsize=(10, 7))
    ax.bar(hourly_usage['hour'], hourly_usage['usage_time'], color=colors)
    ax.set_title(f'Houtly usage of {selected_app} on {today.strftime("%m/%d/%Y")}', fontsize=14)
    ax.set_ylabel('Usage Time (seconds)', fontsize=12)
    ax.set_xticks(range(24))
    ax.set_xticklabels(range(24))
    ax.grid(axis='y', linestyle='None', alpha=0.7)

    canvas = FigureCanvasTkAgg(figure, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
def plot_bar_chart_current_month(df, selected_app, graph_frame):
    today = date.today()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    current_month_start = today.replace(day=1)
    _, days_in_month = calendar.monthrange(today.year, today.month)
    current_month_end = today.replace(day=days_in_month)

    df_app = df[(df['app_name'] == selected_app) &
                (df['date'].dt.date >= current_month_start) &
                (df['date'].dt.date <= current_month_end)].copy()

    print(df_app.head())
    if df_app.empty:
        for widget in graph_frame.winfo_children():
            widget.destroy()
        Label(graph_frame, text="No data available for the selected app this month.", fg="red").grid(row=0, column=0)
        return

    df_app['day'] = df_app['date'].dt.day
    daily_usage = df_app.groupby('day')['usage_time'].sum().reset_index()
    print(daily_usage.head())

    if daily_usage.empty:
        for widget in graph_frame.winfo_children():
            widget.destroy()
        Label(graph_frame, text="No daily data available for the selected app this month.", fg="red").grid(row=0, column=0)
        return

    for widget in graph_frame.winfo_children():
        widget.destroy()
    plt.close('all')

    colors = plt.cm.Blues(np.linspace(0.3, 1, len(df)))

    figure, ax = plt.subplots(figsize=(10, 7))
    ax.bar(daily_usage['day'], daily_usage['usage_time'], color=colors)
    ax.set_title(f'Daily Usage of {selected_app} for {today.strftime("%B %Y")}', fontsize=14)
    ax.set_ylabel('Usage Time (seconds)', fontsize=12)
    ax.set_xticks(range(1, days_in_month + 1))
    ax.set_xticklabels(range(1, days_in_month + 1))
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    canvas = FigureCanvasTkAgg(figure, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
def plot_bar_chart_last_40_days(df, selected_app, graph_frame):
    today = datetime.now().date()
    start_date = today - timedelta(days=40)
    df.loc[:, 'date'] = pd.to_datetime(df['date'], errors='coerce')
    df_app = df[(df['app_name'] == selected_app) &
                (df['date'].dt.date >= start_date) &
                (df['date'].dt.date <= today)].copy()

    if df_app.empty:
        for widget in graph_frame.winfo_children():
            widget.destroy()
        Label(graph_frame, text="No data available for the selected app in the last 40 days.", fg="red").grid(row=0, column=0)
        return

    df_app['day'] = df_app['date'].dt.date
    daily_usage = df_app.groupby('day')['usage_time'].sum().reset_index()
    daily_usage['day'] = pd.to_datetime(daily_usage['day'], errors='coerce')

    if daily_usage.empty:
        for widget in graph_frame.winfo_children():
            widget.destroy()
        Label(graph_frame, text="No daily data available for the selected app in the last 40 days.", fg="red").grid(row=0, column=0)
        return

    earliest_date = max(daily_usage['day'].min().date(), today - timedelta(days=20))
    filtered_start_date = min(earliest_date, start_date)
    filtered_date_range = pd.date_range(start=filtered_start_date, end=today)

    all_dates_df = pd.DataFrame({'day': filtered_date_range})
    daily_usage = pd.merge(all_dates_df, daily_usage, on='day', how='left').fillna(0)

    for widget in graph_frame.winfo_children():
        widget.destroy()
    plt.close('all')

    colors = plt.cm.Blues(np.linspace(0.3, 1, len(filtered_date_range)))

    figure, ax = plt.subplots(figsize=(10, 7))
    ax.bar(daily_usage['day'], daily_usage['usage_time'], color=colors)
    ax.set_title(f'Daily Usage of {selected_app} (Last {len(filtered_date_range)} Days)', fontsize=14)
    ax.set_ylabel('Usage Time (seconds)', fontsize=12)

    ax.xaxis.set_major_locator(mdates.DayLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    plt.tight_layout()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    canvas = FigureCanvasTkAgg(figure, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

# mena l main CTk
root = CTk()
root.title("TrackWise")
root.geometry("330x530")
set_appearance_mode("dark")
root.resizable(False, False)

# start tracking on launch
if "--autostart" in sys.argv:
    print("Autostart functionality triggered.")
    run_script()

# make only one instance of the app possible in the same moment
HOST = 'localhost'
PORT = 65432

def restore_window():
    """Restore the application window."""
    root.deiconify()
def handle_incoming_connections():
    """Handle incoming connections from subsequent instances."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print("Listening for incoming connections...")
        while True:
            conn, addr = server.accept()
            with conn:
                print(f"Connection from {addr}")
                restore_window()
def is_instance_running():
    """Check if another instance of the application is already running."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((HOST, PORT))
            client.sendall(b"Restore")  # Send a restore command
        return True
    except ConnectionRefusedError:
        return False
if is_instance_running():
    print("Application is already running. Opening...")
    sys.exit(0)

server_thread = threading.Thread(target=handle_incoming_connections, daemon=True)
server_thread.start()

#add to startup apps (only for windows)
def add_to_startup(app_name):
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(__file__)
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)

        reg.SetValueEx(key, app_name, 0, reg.REG_SZ, exe_path)
        reg.CloseKey(key)
        print(f"{app_name} added to startup successfully!")
    except Exception as e:
        print(f"Failed to add to startup: {e}")
app_name = "TrackWise"
add_to_startup(app_name)


# hetha mta3 l icons
if getattr(sys, 'frozen', False):
    icon_path = os.path.join(sys._MEIPASS, 'clock.ico')
else:
    icon_path = os.path.join(os.path.dirname(__file__), 'clock.ico')
if os.path.exists(icon_path):
    root.iconbitmap(icon_path)

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

play_image_path = get_resource_path('images/play.png')
stop_image_path = get_resource_path('images/stop.png')
graphs_image_path = get_resource_path('images/graphs.png')

try:
    tracking_image = CTkImage(Image.open(play_image_path))
    stop_tracking_image = CTkImage(Image.open(stop_image_path), size=(15, 15))
    graphs_frame = CTkImage(Image.open(graphs_image_path), size=(15, 15))
except FileNotFoundError as e:
    print(f"Image file not found: {e}")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(padx=(0,10), pady=10)

#buttons
tracking_label1 = CTkLabel(root, text="TrackWise", font=('Segoe UI', 28, 'bold'), bg_color="transparent")
tracking_label2 = CTkLabel(root, text="Your Screen Usage, Documented", font=('Segoe UI', 17), bg_color="transparent")
tracking_label1.pack(pady=(6,0))
tracking_label2.pack(pady=(5,20))

def on_close():
    root.withdraw()
root.protocol("WM_DELETE_WINDOW", on_close)

run_button = CTkButton(master=root,
                       height=40,
                       width=160,
                       border_width=2,
                       font = ('Segoe UI', 14),
                       border_color="#3498db",
                       hover_color="#3498db",
                       fg_color="transparent",
                       text="Start Tracking",
                       command=run_script,
                       image=tracking_image,
                       corner_radius=26,)
run_button.pack(pady=10, padx=10)

stop_button = CTkButton(master=root,
                        height=40,
                        width=160,
                        border_width=2,
                        font = ('Segoe UI', 14),
                        border_color="#3498db",
                        hover_color="#3498db",
                        fg_color="transparent",
                        text="Stop Tracking",
                        command=stop_script,
                        image=stop_tracking_image,
                        corner_radius=26)
stop_button.pack(pady=10, padx=10)

graph_button = CTkButton(master=root,
                         height=40,
                         width=160,
                         border_width=2,
                         font=('Segoe UI', 14),
                         border_color="#3498db",
                         hover_color="#3498db",
                         fg_color="transparent",
                         text="Show Graphs",
                         command=show_graph_window,
                         image=graphs_frame,
                         corner_radius=26)
graph_button.pack(pady=10, padx=10)

status_label = CTkLabel(root, text="Status will appear here.", height=12, font=('Segoe UI', 14))
status_label.pack(pady=18, fill='x')

hide_button = CTkButton(
    master=root,
    text="Hide",
    command=on_close,
    height=40,
    width=160,
    border_width=2,
    font=('Segoe UI', 14),
    border_color="#3498db",
    hover_color="#3498db",
    fg_color="transparent",
    corner_radius=26
)
hide_button.pack(pady=10)

save_exit_button = CTkButton(
    master=root,
    height=40,
    width=160,
    border_width=2,
    font = ('Segoe UI', 14),
    border_color="red",
    hover_color="red",
    fg_color="transparent",
    text="Save and Exit",
    command=save_and_exit,
    corner_radius=26
)
save_exit_button.pack(pady=10, padx=10)


credit = CTkLabel(root, text="2024©GoldenDragon", font=('Segoe UI', 10), bg_color="transparent")
credit.pack(pady=(10,0))

root.mainloop()
