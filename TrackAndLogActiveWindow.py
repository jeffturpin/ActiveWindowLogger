import json
import sqlite3
import threading
import time

import psutil
import pygetwindow as gw
import win32api
import win32gui
import win32process
import tkinter as tk
from tkinter import simpledialog, ttk


# This code creates a database file if it doesn't already exist, and creates a table inside the database file.

def create_database():
    conn = sqlite3.connect('activity_log.db')  # This will create the database file if it doesn't exist
    cursor = conn.cursor()

    # Create table
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_log
                      (id INTEGER PRIMARY KEY, event TEXT, starttimestamp REAL, endtimestamp REAL, duration REAL, window_title TEXT, username TEXT, name TEXT, process_info TEXT)''')

    conn.commit()
    conn.close()

def get_window_title_and_process(hwnd):
    process_info = {
        'window_title': None,
        'pid': None,
        'name': None,
        'parent_pid': None,
        'parent_name': None,
        'status': None,
        'username': None,
        'create_time': None,
        'cwd': None,
        'cmdline': None,
        'exe': None
    }

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_info['pid'] = pid
    except Exception:
        pass

    try:
        process = win32api.OpenProcess(0x0410, False, pid)
        exe = win32process.GetModuleFileNameEx(process, 0)
        process_info['name'] = exe.split('\\')[-1]
    except Exception:
        pass

    try:
        window_title = win32gui.GetWindowText(hwnd)
        process_info['window_title'] = window_title
    except Exception:
        pass

    try:
        parent_pid = psutil.Process(pid).ppid()
        process_info['parent_pid'] = parent_pid
        process_info['parent_name'] = psutil.Process(parent_pid).name() if parent_pid else None
    except Exception:
        pass

    try:
        process_info['status'] = psutil.Process(pid).status() if pid else None
    except Exception:
        pass

    try:
        process_info['username'] = psutil.Process(pid).username() if pid else None
    except Exception:
        pass

    try:
        process_info['create_time'] = psutil.Process(pid).create_time() if pid else None
    except Exception:
        pass

    try:
        process_info['cwd'] = psutil.Process(pid).cwd() if pid else None
    except Exception:
        pass

    try:
        process_info['cmdline'] = psutil.Process(pid).cmdline() if pid else None
    except Exception:
        pass

    try:
        process_info['exe'] = psutil.Process(pid).exe() if pid else None
    except Exception:
        pass

    return process_info


def log_activity_start(process_info):
    start_time = time.time()
    conn = sqlite3.connect('activity_log.db')
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO activity_log (event, starttimestamp, window_title, name, username, process_info) VALUES (?, ?, ?, ?, ?, ?)",
                   ('start', start_time, process_info['window_title'], process_info['name'], process_info['username'], json.dumps(process_info)))
    
    conn.commit()
    activity_id = cursor.lastrowid  # Fetches the ID of the last inserted row
    conn.close()
    return activity_id
    

def log_activity_end(activity_id, stop_time, duration, process_info):
    conn = sqlite3.connect('activity_log.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE activity_log SET event = ?, endtimestamp = ?, duration = ?, window_title = ?, process_info = ? WHERE id = ?",
                   ('end', stop_time, duration, process_info['window_title'], json.dumps(process_info), activity_id))
    
    conn.commit()
    conn.close()
    

class ActivityLogger:
    def __init__(self, root):
        self.root = root
        self.active = False
        self.active_window = None
        self.start_time = None
        self.pause_start_time = None
        self.log_file = 'activity_log.txt'
        self.thread = None
        
        
        self.root.attributes('-topmost', True)
        root.configure(bg="#F0F0F0")
        style = ttk.Style()
        style.configure("TButton", padding=5, relief="flat", background="#F0F0F0")

        self.current_window_label = ttk.Label(root, text="Current window: None", background="#F0F0F0")
        self.current_window_label.pack(pady=10)

        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10)
        
        self.start_resume_button = ttk.Button(button_frame, text="Start Monitor", command=self.start_or_resume_monitor)
        self.start_resume_button.pack(side=tk.LEFT, padx=5)

        self.sign_off_button = ttk.Button(button_frame, text="Sign-off", command=lambda: self.pause_activity_monitor("Sign-off"))
        self.sign_off_button.pack(side=tk.LEFT, padx=5)

        self.lunch_button = ttk.Button(button_frame, text="Lunch", command=lambda: self.pause_activity_monitor("Lunch"))
        self.lunch_button.pack(side=tk.LEFT, padx=5)

        self.break_button = ttk.Button(button_frame, text="Break", command=lambda: self.pause_activity_monitor("Break"))
        self.break_button.pack(side=tk.LEFT, padx=5)

        self.bathroom_button = ttk.Button(button_frame, text="Bathroom", command=lambda: self.pause_activity_monitor("Bathroom"))
        self.bathroom_button.pack(side=tk.LEFT, padx=5)
    
        self.other_button = ttk.Button(button_frame, text="Other", command=self.log_other_activity)
        self.other_button.pack(side=tk.LEFT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
        self.active_button = None
        self.button_state = {}
        self.current_activity = None
        
    def log_other_activity(self):
        # Prompt the user for a description
        description = simpledialog.askstring("Other Activity", "Enter a short description:", parent=self.root)

        # Proceed only if the description is not empty
        if description:
            self.pause_activity_monitor(f"Other - {description}")    

    def update_current_window_label(self, title):
        self.current_window_label.config(text=f"Current window: {title}")

    def log_activity_start(self, process_info):
        start_time = time.time()
        self.current_activity = {
            'start_time': start_time,
            'process_info': process_info
        }
        self.current_activity['database_id'] = log_activity_start(process_info)


        

    def log_activity_end(self):
        if self.current_activity:
            stop_time = time.time()
            duration = stop_time - self.current_activity['start_time']
            log_activity_end(activity_id= self.current_activity['database_id'], stop_time=stop_time, duration=duration, process_info=self.current_activity['process_info'])
            self.current_activity = None
            
            
    def pause_activity_monitor(self, reason):
        was_active = self.active  # Keep track of whether the monitor was previously active

        # If we are already in a paused state, log the end of the previous manual activity
        if self.pause_start_time:
            self.log_activity_end()
            self.pause_start_time = None

        # If the monitor was active, perform the usual pause operations
        if was_active:
            self.active = False
            self.log_activity_end()
            if self.thread and self.thread.is_alive():
                self.thread.join()

        # Log the start of the new manual activity (e.g., "Lunch", "Break")
        self.log_activity_start({'window_title': reason, 'username': None, 'process_info': None, 'name': reason})
        self.set_button_state(reason, True)
        self.update_current_window_label(reason)
        self.pause_start_time = time.time()

    def start_or_resume_monitor(self):
        if not self.active:
            # Log the end of the manual activity if there was one
            if self.pause_start_time:
                self.log_activity_end()
                pause_duration = time.time() - self.pause_start_time
                self.pause_start_time = None

            self.set_button_state("Start Monitor", True)
            self.active = True
            self.thread = threading.Thread(target=self.activity_monitor)
            self.thread.start()
            self.update_current_window_label("Monitoring...")
            
    def set_button_state(self, button_text, is_active):
        if self.active_button:
            self.active_button.state(['!pressed'])
        if is_active:
            button_dict = {"Start Monitor": self.start_resume_button, "Sign-off": self.sign_off_button,
                           "Lunch": self.lunch_button, "Break": self.break_button, "Bathroom": self.bathroom_button}
            self.active_button = button_dict.get(button_text)
            if self.active_button:
                self.active_button.state(['pressed'])

    def activity_monitor(self):
        while self.active:
            hwnd = gw.getActiveWindow()._hWnd
            current_process_info = get_window_title_and_process(hwnd)

            # Check if the window handle or the window title has changed
            if (not self.active_window or self.active_window._hWnd != hwnd) or \
            (self.active_window and self.active_window.title != current_process_info['window_title']):
                
                # Log the end of the previous activity
                self.log_activity_end()

                # Update the active window and log the start of the new activity
                self.active_window = gw.getActiveWindow()
                self.log_activity_start(current_process_info)

                # Update the UI with the new active window
                self.update_current_window_label(current_process_info['window_title'] if current_process_info else "None")

            time.sleep(1)
            
    def on_exit(self):
        if self.active or self.pause_start_time:
            # If an activity is active or paused, log its end
            self.log_activity_end()

        # Perform any other necessary cleanup here
        if self.thread and self.thread.is_alive():
            self.active = False
            self.thread.join()

        self.root.destroy()

if __name__ == "__main__":
    create_database()
    root = tk.Tk()
    root.title("Activity Logger")
    app = ActivityLogger(root)
    root.mainloop()
