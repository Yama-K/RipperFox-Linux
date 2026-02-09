#!/usr/bin/env python3
import sys
import os
import json
import threading
import time
import urllib.request
import logging
from datetime import datetime
import appdirs

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction,
    QMessageBox, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QMainWindow, QPlainTextEdit,
    QLabel, QComboBox
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QPainter, QFont, QColor, QPen, QBrush,
    QTextCursor
)
from PyQt5.QtCore import QTimer, Qt, QSize, pyqtSignal, QObject

# Custom stream to capture stdout/stderr
class LogStream(QObject):
    new_log = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def write(self, text):
        # Emit signal with new text
        self.new_log.emit(text)
        # Also write to original stdout if needed
        sys.__stdout__.write(text)

    def flush(self):
        sys.__stdout__.flush()

class LogWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RipperFox Logs")
        self.setGeometry(100, 100, 800, 500)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create toolbar
        toolbar_layout = QHBoxLayout()

        # Clear button
        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)
        toolbar_layout.addWidget(self.clear_button)

        # Log level selector
        toolbar_layout.addWidget(QLabel("Log Level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.currentTextChanged.connect(self.change_log_level)
        toolbar_layout.addWidget(self.log_level_combo)

        # Save logs button
        self.save_button = QPushButton("Save Logs")
        self.save_button.clicked.connect(self.save_logs)
        toolbar_layout.addWidget(self.save_button)

        # Auto-scroll toggle
        self.autoscroll_check = QPushButton("Auto-scroll: ON")
        self.autoscroll_check.setCheckable(True)
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.clicked.connect(self.toggle_autoscroll)
        toolbar_layout.addWidget(self.autoscroll_check)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # Create log text area
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Monospace", 9))
        self.log_text.setLineWrapMode(QPlainTextEdit.NoWrap)

        # Set dark theme for logs
        palette = self.log_text.palette()
        palette.setColor(palette.Base, QColor(40, 40, 40))
        palette.setColor(palette.Text, QColor(220, 220, 220))
        self.log_text.setPalette(palette)

        layout.addWidget(self.log_text)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Variables
        self.log_count = 0
        self.max_logs = 10000

    def append_log(self, text):
        """Append text to the log window."""
        if not text.strip():
            return

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {text}"

        # Append to text area
        self.log_text.appendPlainText(log_line.rstrip())

        # Auto-scroll if enabled
        if self.autoscroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        # Update status
        self.log_count += 1
        if self.log_count % 100 == 0:
            self.status_bar.showMessage(f"Logs: {self.log_count}")

        # Trim old logs if needed
        if self.log_count > self.max_logs:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 100)
            cursor.removeSelectedText()
            self.log_count -= 100

    def clear_logs(self):
        """Clear all logs."""
        self.log_text.clear()
        self.log_count = 0
        self.status_bar.showMessage("Logs cleared")

    def save_logs(self):
        """Save logs to file."""
        from PyQt5.QtWidgets import QFileDialog
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "ripperfox_logs.txt", "Text Files (*.txt);;All Files (*)"
        )

        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.status_bar.showMessage(f"Logs saved to {file_name}")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Failed to save logs: {str(e)}")

    def change_log_level(self, level):
        """Change log level."""
        self.status_bar.showMessage(f"Log level changed to: {level}")

    def toggle_autoscroll(self, checked):
        """Toggle auto-scroll."""
        self.autoscroll_check.setText(f"Auto-scroll: {'ON' if checked else 'OFF'}")

    def closeEvent(self, event):
        """Handle window close event - hide instead of close."""
        event.ignore()
        self.hide()

    def show_and_focus(self):
        """Show window and bring to front."""
        self.show()
        self.raise_()
        self.activateWindow()

class RipperFoxTray(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.backend_thread = None
        self.appdata_dir = self.get_appdata_dir()
        self.log_window = None

        # Set up logging
        self.setup_logging()

        # Set up the tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.setup_tray_icon()

        # Start the backend
        self.start_backend()

        # Check backend health
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self.check_backend_health)
        self.health_check_timer.start(5000)

        self.log("[SYSTEM] RipperFox tray icon initialized. Right-click for menu.")

    def setup_logging(self):
        """Set up logging to capture stdout/stderr."""
        # Create custom stream
        self.log_stream = LogStream()
        self.log_stream.new_log.connect(self.handle_log)

        # Redirect stdout and stderr
        sys.stdout = self.log_stream
        sys.stderr = self.log_stream

        # Set up Python logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    def handle_log(self, text):
        """Handle log messages from the stream."""
        if self.log_window:
            self.log_window.append_log(text)

    def log(self, message):
        """Log a message."""
        print(message)

    def get_appdata_dir(self):
        """Return the application data directory."""
        if getattr(sys, 'frozen', False):
            data_dir = appdirs.user_data_dir("RipperFox", "RipperFox")
        else:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def get_settings_path(self):
        return os.path.join(self.appdata_dir, "settings.json")

    def load_settings(self):
        path = self.get_settings_path()
        default = {"autostart": False, "show_log_window": False}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    default.update(data)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(default, f, indent=2)
        except Exception as e:
            self.log(f"[WARNING] Failed to read settings.json: {e}")
        return default

    def save_settings(self, data):
        path = self.get_settings_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.log(f"[WARNING] Failed to save settings.json: {e}")

    def setup_tray_icon(self):
        """Create and setup the tray icon with menu."""
        # Create icon from file or generate one
        icon = self.create_icon()
        self.tray_icon.setIcon(icon)

        # Create context menu
        menu = QMenu()

        # Status action
        self.status_action = QAction("Backend: Starting...", self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        menu.addSeparator()

        # Show Logs action
        logs_action = QAction("Show Logs", self)
        logs_action.triggered.connect(self.show_logs_window)
        menu.addAction(logs_action)

        # Autostart action
        self.autostart_action = QAction("Autostart", self)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(self.is_autostart_enabled())
        self.autostart_action.triggered.connect(self.toggle_autostart)
        menu.addAction(self.autostart_action)

        # Update yt-dlp action
        update_action = QAction("Update yt-dlp", self)
        update_action.triggered.connect(self.update_yt_dlp)
        menu.addAction(update_action)
        menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

        # Connect tray icon activation
        self.tray_icon.activated.connect(self.on_tray_activated)

        # Show startup notification
        self.tray_icon.showMessage("RipperFox", "Started in system tray",
                                 QSystemTrayIcon.Information, 2000)

    def create_icon(self):
        """Create icon from file or generate one."""
        base_dir = os.path.dirname(__file__)

        # Try PNG first
        icon_paths = [
            os.path.join(base_dir, "icon.png"),
            os.path.join(base_dir, "icon.ico"),
            os.path.join(base_dir, "icon.svg"),
            os.path.join(base_dir, "icon.xpm"),
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    self.log(f"[DEBUG] Loading icon from: {icon_path}")
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        return icon
                except Exception as e:
                    self.log(f"[WARNING] Failed to load icon {icon_path}: {e}")

        # Generate a fallback icon
        self.log("[DEBUG] Generating fallback icon")
        return self.generate_fallback_icon()

    def generate_fallback_icon(self):
        """Generate a fallback icon programmatically."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw blue circle
        painter.setBrush(QBrush(QColor(31, 111, 235)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, size-8, size-8)

        # Draw 'R' text
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 24, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "R")

        painter.end()

        return QIcon(pixmap)

    def show_logs_window(self):
        """Show the log window."""
        if not self.log_window:
            self.log_window = LogWindow()
            # Restore window state from settings
            settings = self.load_settings()
            if settings.get("show_log_window", False):
                self.log_window.show()
        else:
            self.log_window.show_and_focus()

    def on_tray_activated(self, reason):
        """Handle tray icon clicks."""
        if reason == QSystemTrayIcon.Trigger:  # Left click
            self.show_backend_status()

    def show_backend_status(self):
        """Show backend status."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:5100/api/status", timeout=2) as resp:
                if resp.status == 200:
                    self.tray_icon.showMessage("Status", "Backend is running ✓",
                                             QSystemTrayIcon.Information, 2000)
                else:
                    self.tray_icon.showMessage("Status", f"Backend error: {resp.status}",
                                             QSystemTrayIcon.Warning, 2000)
        except Exception as e:
            self.tray_icon.showMessage("Status", f"Backend not responding: {str(e)}",
                                     QSystemTrayIcon.Critical, 2000)

    def check_backend_health(self):
        """Check if backend is still running and update status."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:5100/api/status", timeout=2) as resp:
                if resp.status == 200:
                    self.status_action.setText("Backend: Running ✓")
                else:
                    self.status_action.setText("Backend: Error ✗")
        except Exception:
            self.status_action.setText("Backend: Not Responding ✗")

    def start_backend(self):
        """Start the Flask backend in a separate thread."""
        def backend_worker():
            try:
                # Add local site-packages to path
                base_dir = os.path.dirname(__file__)
                local_site = os.path.join(base_dir, "python", "Lib", "site-packages")
                if os.path.isdir(local_site) and local_site not in sys.path:
                    sys.path.insert(0, local_site)

                # Change to appdata dir
                try:
                    os.chdir(self.appdata_dir)
                    self.log(f"[SYSTEM] Changed working dir to: {self.appdata_dir}")
                except Exception as e:
                    self.log(f"[WARNING] Could not change working directory: {e}")

                from yt_backend import app
                self.log("[SYSTEM] Starting Flask backend on port 5100...")
                app.run(port=5100, debug=False, use_reloader=False)
            except Exception as e:
                self.log(f"[ERROR] Backend failed: {e}")
                # Show error in GUI thread
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self, "Backend Error",
                    f"Failed to start backend: {str(e)}\n\nCheck console for details."
                ))

        self.backend_thread = threading.Thread(target=backend_worker, daemon=True)
        self.backend_thread.start()

        # Start auto-update check if available
        try:
            from ytdlp_updater import auto_update_check
            threading.Thread(target=auto_update_check, daemon=True).start()
        except Exception as e:
            self.log(f"[INFO] Auto-update not available: {e}")

    def update_yt_dlp(self):
        """Trigger yt-dlp update."""
        self.log("[UPDATE] Starting yt-dlp update...")
        try:
            import requests
        except ImportError:
            self.log("[UPDATE] ERROR: Requests module not available")
            QMessageBox.warning(self, "Update Error",
                              "Requests module not available. Cannot update.")
            return

        def do_update():
            try:
                self.log("[UPDATE] Sending update request to backend...")
                resp = requests.post("http://127.0.0.1:5100/api/update-yt-dlp", timeout=5)

                if resp.ok:
                    self.log("[UPDATE] Update request accepted")
                    self.show_notification("Update Started", "yt-dlp update has begun")

                    # Poll for status
                    while True:
                        time.sleep(1)
                        s = requests.get("http://127.0.0.1:5100/api/update-status", timeout=5).json()
                        status = s.get("status")
                        msg = s.get("message")

                        self.log(f"[UPDATE] Status: {status} - {msg}")

                        if status in ("succeeded", "failed", "idle"):
                            title = "Update Succeeded" if status == "succeeded" else "Update Failed"
                            self.log(f"[UPDATE] {title}: {msg}")
                            self.show_notification(title, msg)
                            break
                else:
                    self.log(f"[UPDATE] Request failed: {resp.status_code} {resp.text}")
                    self.show_notification("Update Failed",
                                         f"Request failed: {resp.status_code}")

                    # Try local updater as fallback
                    self.try_local_update()

            except Exception as e:
                self.log(f"[UPDATE] Error: {e}")
                self.try_local_update()

        # Run update in background thread
        threading.Thread(target=do_update, daemon=True).start()

    def try_local_update(self):
        """Try local update as fallback."""
        try:
            from ytdlp_updater import download_latest_ytdlp
            self.log("[UPDATE] Trying local update...")
            if download_latest_ytdlp():
                self.log("[UPDATE] Local update successful")
                self.show_notification("Update Succeeded",
                                     "yt-dlp updated locally")
            else:
                self.log("[UPDATE] Local update failed")
                self.show_notification("Update Failed",
                                     "Local update failed")
        except Exception as e:
            self.log(f"[UPDATE] Local update error: {e}")
            self.show_notification("Update Error",
                                 f"Could not update: {str(e)}")

    def show_notification(self, title, message):
        """Show a system notification."""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)
        self.log(f"[NOTIFY] {title}: {message}")

    def get_autostart_entry_path(self):
        """Return the path for the desktop autostart entry on Linux."""
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        return os.path.join(autostart_dir, "ripperfox.desktop")

    def is_autostart_enabled(self):
        """Check if autostart is enabled."""
        settings = self.load_settings()
        entry = self.get_autostart_entry_path()
        if settings.get("autostart", False) and os.path.exists(entry):
            return True
        return False

    def toggle_autostart(self, checked):
        """Enable or disable autostart."""
        if checked:
            self.enable_autostart()
        else:
            self.disable_autostart()

    def enable_autostart(self):
        """Enable autostart."""
        entry = self.get_autostart_entry_path()
        try:
            if getattr(sys, 'frozen', False):
                exec_cmd = sys.executable
            else:
                exec_cmd = f'{sys.executable} "{os.path.abspath(__file__)}"'

            desktop = (
                '[Desktop Entry]\n'
                'Type=Application\n'
                'Version=1.0\n'
                'Name=RipperFox\n'
                f'Exec={exec_cmd}\n'
                'Hidden=false\n'
                'NoDisplay=false\n'
                'X-GNOME-Autostart-enabled=true\n'
                'Terminal=false\n'
                'Icon=ripperfox\n'
            )

            with open(entry, 'w', encoding='utf-8') as f:
                f.write(desktop)

            try:
                os.chmod(entry, 0o755)
            except Exception:
                pass

            # Save to settings
            settings = self.load_settings()
            settings["autostart"] = True
            self.save_settings(settings)

            self.show_notification("Autostart Enabled",
                                 "RipperFox will start automatically on login")
            self.log("[SYSTEM] Autostart enabled")

        except Exception as e:
            self.log(f"[ERROR] Failed to enable autostart: {e}")
            self.autostart_action.setChecked(False)
            QMessageBox.warning(self, "Autostart Error",
                              f"Failed to enable autostart: {str(e)}")

    def disable_autostart(self):
        """Disable autostart."""
        entry = self.get_autostart_entry_path()
        try:
            if os.path.exists(entry):
                os.remove(entry)

            # Save to settings
            settings = self.load_settings()
            settings["autostart"] = False
            self.save_settings(settings)

            self.log("[SYSTEM] Autostart disabled")

        except Exception as e:
            self.log(f"[ERROR] Failed to disable autostart: {e}")
            self.autostart_action.setChecked(True)
            QMessageBox.warning(self, "Autostart Error",
                              f"Failed to disable autostart: {str(e)}")

    def exit_app(self):
        """Exit the application."""
        # Show confirmation
        reply = QMessageBox.question(
            self, 'Exit RipperFox',
            'Are you sure you want to exit? The backend will stop.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.log("[SYSTEM] Shutting down RipperFox...")

            # Save log window state
            if self.log_window:
                settings = self.load_settings()
                settings["show_log_window"] = self.log_window.isVisible()
                self.save_settings(settings)

                if self.log_window.isVisible():
                    self.log_window.close()

            # Stop health check timer
            self.health_check_timer.stop()

            self.app.quit()

def main():
    # Set up environment for KDE
    os.environ.setdefault('XDG_CURRENT_DESKTOP', 'KDE')

    # Remove --detach flag if present (Qt can't handle daemonization)
    if '--detach' in sys.argv:
        print("[INFO] Removing --detach flag for Qt compatibility")
        sys.argv.remove('--detach')

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("RipperFox")
    app.setApplicationDisplayName("RipperFox")
    app.setQuitOnLastWindowClosed(False)

    # Set application style for better KDE integration
    app.setStyle('Fusion')

    # Create and show tray icon
    tray = RipperFoxTray(app)

    # Show log window if it was open before
    settings = tray.load_settings()
    if settings.get("show_log_window", False):
        tray.show_logs_window()
        tray.log_window.show()

    # Start the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Check if PyQt5 is available
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import pyqtSignal
    except ImportError:
        print("=" * 60)
        print("ERROR: PyQt5 is not installed!")
        print("Please install it using one of these methods:")
        print()
        print("On Ubuntu/Debian:")
        print("  sudo apt-get install python3-pyqt5")
        print()
        print("On Arch Linux:")
        print("  sudo pacman -S python-pyqt5")
        print()
        print("On Fedora:")
        print("  sudo dnf install python3-qt5")
        print()
        print("Or using pip (if available):")
        print("  pip install PyQt5")
        print("=" * 60)
        sys.exit(1)

    main()
