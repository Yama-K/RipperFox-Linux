import sys
import os
import threading
from PIL import Image
import pystray


def create_tray_icon():
    """Load icon from icon.ico/icon.png file."""
    base_dir = os.path.dirname(__file__)
    
    # Try PNG first (better compatibility on Linux)
    icon_png_path = os.path.join(base_dir, "icon.png")
    if os.path.exists(icon_png_path):
        try:
            image = Image.open(icon_png_path)
            print(f"[SYSTEM] Loaded icon: {icon_png_path}")
            return image
        except Exception as e:
            print(f"[WARNING] Could not load PNG icon: {e}")
    
    # Fallback to ICO
    icon_ico_path = os.path.join(base_dir, "icon.ico")
    if os.path.exists(icon_ico_path):
        try:
            image = Image.open(icon_ico_path)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Save PNG version for faster loading next time
            try:
                image.save(icon_png_path, 'PNG')
                print(f"[SYSTEM] Cached icon as PNG: {icon_png_path}")
            except Exception:
                pass
            
            print(f"[SYSTEM] Loaded icon: {icon_ico_path}")
            return image
        except Exception as e:
            print(f"[WARNING] Could not load ICO icon: {e}")
    
    # Fallback: generate a simple icon
    print("[WARNING] No icon files found, using generated fallback icon")
    image = Image.new('RGBA', (64, 64), color=(31, 111, 235, 255))  # GitHub blue
    return image

def exit_app(icon, item):
    """Exit the application"""
    icon.stop()
    os._exit(0)

def update_yt_dlp(icon, item):
    """Trigger backend update and stream status to console"""
    try:
        import requests
    except Exception as e:
        print(f"[UPDATE] Requests not available: {e}. Falling back to local updater.")
        try:
            from ytdlp_updater import download_latest_ytdlp
            if download_latest_ytdlp():
                print("[UPDATE] yt-dlp updated successfully (local)")
            else:
                print("[UPDATE] Local update failed")
        except Exception as ee:
            print(f"[UPDATE] Local update failed: {ee}")
        return

    def _worker():
        try:
            resp = requests.post("http://127.0.0.1:5100/api/update-yt-dlp", timeout=5)
            if resp.ok:
                print("[UPDATE] Update requested")
                import time
                while True:
                    time.sleep(1)
                    s = requests.get("http://127.0.0.1:5100/api/update-status", timeout=5).json()
                    status = s.get("status")
                    msg = s.get("message")
                    print(f"[UPDATE] {status}: {msg}")
                    if status in ("succeeded", "failed", "idle"):
                        break
            else:
                print(f"[UPDATE] Update request failed: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[UPDATE] Could not contact backend: {e}. Falling back to local updater.")
            try:
                from ytdlp_updater import download_latest_ytdlp
                if download_latest_ytdlp():
                    print("[UPDATE] yt-dlp updated successfully (local)")
                else:
                    print("[UPDATE] Local update failed")
            except Exception as ee:
                print(f"[UPDATE] Local update failed: {ee}")

    import threading
    threading.Thread(target=_worker, daemon=True).start()


def setup_tray_icon():
    """Setup the system tray icon with context menu."""
    image = create_tray_icon()
    
    menu = pystray.Menu(
        pystray.MenuItem('Update yt-dlp', update_yt_dlp),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Exit', exit_app)
    )
    
    icon = pystray.Icon("RipperFox", image, "RipperFox Backend", menu)
    return icon

def start_backend():
    """Start the Flask backend"""
    try:
        # Change working directory to appdata when running as frozen so relative paths are writable
        try:
            if getattr(sys, 'frozen', False):
                import appdirs
                data_dir = appdirs.user_data_dir("RipperFox", "RipperFox")
                os.makedirs(data_dir, exist_ok=True)
                try:
                    os.chdir(data_dir)
                    print(f"[SYSTEM] Changed working dir to: {data_dir}")
                except Exception as e:
                    print(f"[WARNING] Could not change working directory to {data_dir}: {e}")
        except Exception:
            pass

        from yt_backend import app
        print("[SYSTEM] Starting Flask backend on port 5100...")
        # Run in a separate thread to avoid blocking
        threading.Thread(target=lambda: app.run(port=5100, debug=False, use_reloader=False), daemon=True).start()

        # Quick health check to ensure backend is responding
        try:
            import urllib.request, time
            for _ in range(10):
                try:
                    with urllib.request.urlopen("http://127.0.0.1:5100/api/status", timeout=1) as resp:
                        if resp.status == 200:
                            print("[SYSTEM] Backend started and responding on port 5100")
                            break
                except Exception:
                    time.sleep(0.5)
            else:
                print("[WARNING] Backend did not respond after startup. It may still be initializing or failed to start.")
        except Exception:
            pass
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")

if __name__ == "__main__":
    # Start the backend first
    start_backend()
    
    # Then start the tray icon
    icon = setup_tray_icon()
    
    print("[SYSTEM] RipperFox is running in system tray. Right-click the icon for options.")
    icon.run()