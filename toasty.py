#!/usr/bin/env python3

## python3 tosty.py -t 85 -p XXXX
## echo "tosty" | nc <ip_addr> <port> #remote trigger
## CRON # DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/$(id -u) /usr/bin/python3 /path/to/your_script.py &


import sys
import os
import threading
import time
import argparse
import socket
import psutil  # To check CPU temperature, install with `pip install psutil`
from playsound import playsound
from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QPoint
from PyQt5.QtGui import QPixmap

class TransparentWindow(QLabel):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Set up the window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Load image
        pixmap = QPixmap('/home/pi/system/Toasty/toasty.png')
        self.setPixmap(pixmap)

        # Get specific screen (display :0)
        screens = QApplication.screens()
        target_screen = screens[0]  # Use first screen (display :0)
        screen = target_screen.geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        # Set initial position (off screen to the right)
        self.setGeometry(
            self.screen_width,
            self.screen_height - pixmap.height(),
            pixmap.width(),
            pixmap.height()
        )

        # Move window to specific screen
        self.moveToScreen(target_screen)

        # Create animation
        self.anim = QPropertyAnimation(self, b'pos')
        self.anim.setDuration(200)  # 200ms for the slide
        final_x = self.screen_width - pixmap.width()
        start_pos = QPoint(self.screen_width, self.screen_height - pixmap.height())
        end_pos = QPoint(final_x, self.screen_height - pixmap.height())
        self.anim.setStartValue(start_pos)
        self.anim.setEndValue(end_pos)

        # Show window and start animation
        self.show()
        self.anim.start()

        # Set timer to close window
        QTimer.singleShot(2000, self.close)  # Close after 2 seconds

    def moveToScreen(self, screen):
        # Get the geometry of the target screen
        screen_geometry = screen.geometry()
        # Adjust window position to be relative to the target screen
        self.move(screen_geometry.left() + self.x(), screen_geometry.top() + self.y())

def play_audio():
    playsound('/home/pi/system/Toasty/TOASTY.mp3')

def check_cpu_temperature(threshold, trigger_event):
    """Monitors CPU temperature and triggers the event if threshold is reached."""
    while True:
        try:
            temps = psutil.sensors_temperatures().get('coretemp', [])
            package_temp = next((t.current for t in temps if t.label == 'Package id 0'), None)
            if package_temp is not None and package_temp >= threshold:
                trigger_event.set()
        except (KeyError, IndexError, StopIteration):
            print("Unable to read CPU temperature.")
        time.sleep(60)  # Check every 60 seconds

def remote_trigger(port, trigger_event):
    """Sets up a simple socket server to listen for remote triggers on the specified port."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    print(f"Listening for remote triggers on port {port}...")

    while True:
        conn, _ = server_socket.accept()
        data = conn.recv(1024).decode('utf-8').strip()  # Receive data and strip whitespace

        if data == "toasty":  # Check for the specific trigger word
            trigger_event.set()  # Trigger if the word matches

        conn.close()

def display_animation(trigger_event):
    """Displays the animation with audio on each trigger."""
    while True:
        trigger_event.wait()  # Wait until triggered
        trigger_event.clear()  # Reset event

        # Start audio immediately
        audio_thread = threading.Thread(target=play_audio)
        audio_thread.start()

        # Small delay to ensure audio starts first
        time.sleep(0.01)

        # Initialize a new QApplication instance each time to avoid errors
        app = QApplication.instance()  # Check if QApplication already exists
        if app is None:  # Create a QApplication if it does not exist
            app = QApplication(sys.argv)
        
        window = TransparentWindow()
        QTimer.singleShot(3000, app.quit)  # Exit after 2.5 seconds
        app.exec_()

if __name__ == '__main__':
    # Argument parsing
    parser = argparse.ArgumentParser(description="Run animated notification with remote and CPU temp triggers.")
    parser.add_argument("-t", type=int, default=80, help="Set CPU temp threshold, e.g., -t 80 for 80C.")
    parser.add_argument("-p", type=int, default=None, help="Set port for remote triggering, e.g., -p 2322.")
    args = parser.parse_args()

    os.environ['DISPLAY'] = ':0'  # Set the X display

    # Initialize threading events
    trigger_event = threading.Event()

    # Start temperature monitor thread if threshold is set
    if args.t:
        threading.Thread(target=check_cpu_temperature, args=(args.t, trigger_event), daemon=True).start()

    # Start remote trigger server if port is specified
    if args.p:
        threading.Thread(target=remote_trigger, args=(args.p, trigger_event), daemon=True).start()

    # Start the main animation loop
    display_animation(trigger_event)
