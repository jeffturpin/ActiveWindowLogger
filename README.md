# Activity Logger

This Python script logs the active window title and process information to a SQLite database. It also provides a simple GUI that allows the user to start and stop monitoring, and to log manual activities such as lunch breaks or bathroom breaks.

## Requirements

- Python 3.x
- pygetwindow
- psutil
- pywin32
- tkinter

## Installation

1. Clone this repository or download the ZIP file and extract it.
2. Install the required Python packages by running `pip install -r requirements.txt` in the project directory.

## Usage

1. Run the script by running `python TrackAndLogActiveWindow.py` in the project directory.
2. The GUI window will appear. Click the "Start Monitor" button to start monitoring the active window.
3. The current active window title and process information will be logged to the database every second.
4. To log a manual activity, click one of the buttons labeled "Sign-off", "Lunch", "Break", "Bathroom", or "Other". Enter a short description if prompted.
5. To stop monitoring, click the "Start Monitor" button again.

## Database schema

The database schema consists of a single table named `activity_log` with the following columns:

- `id`: integer primary key
- `event`: text (either "start" or "end")
- `starttimestamp`: real (Unix timestamp in seconds)
- `endtimestamp`: real (Unix timestamp in seconds)
- `duration`: real (duration in seconds)
- `window_title`: text (title of the active window)
- `username`: text (name of the user who was logged in)
- `name`: text (name of the process)
- `process_info`: text (JSON-encoded dictionary with additional process information)

## License

This code is released under the MIT License. See LICENSE.txt for details.