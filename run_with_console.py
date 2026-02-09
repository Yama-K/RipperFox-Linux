#!/usr/bin/env python3
# run_with_console.py - Run RipperFox with terminal output
import subprocess
import sys
import os

def main():
    # Check if we should run in terminal mode
    if "--terminal" in sys.argv or "-t" in sys.argv:
        # Run in terminal mode - show console window
        print("=" * 60)
        print("RipperFox - Terminal Mode")
        print("=" * 60)
        print("Logs will appear here. Close this window to exit RipperFox.")
        print()
        
        # Run the main launcher
        import ripperfox_launcher
        ripperfox_launcher.main()
    else:
        # Run normally (detached)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        launcher_path = os.path.join(script_dir, "ripperfox_launcher.py")
        
        # Run in background
        subprocess.Popen([sys.executable, launcher_path, "--detach"])
        print("RipperFox started in background. Check system tray.")

if __name__ == "__main__":
    main()