# test_icon.py - Run this to test icon loading
import sys
import os
from PIL import Image

def test_icon():
    base_dir = os.path.dirname(__file__)
    
    # Test PNG
    png_path = os.path.join(base_dir, "icon.png")
    if os.path.exists(png_path):
        print(f"PNG exists: {png_path}")
        try:
            img = Image.open(png_path)
            print(f"  Size: {img.size}, Mode: {img.mode}")
            print(f"  Format: {img.format}")
        except Exception as e:
            print(f"  Error loading: {e}")
    else:
        print(f"PNG not found: {png_path}")
    
    # Test ICO
    ico_path = os.path.join(base_dir, "icon.ico")
    if os.path.exists(ico_path):
        print(f"ICO exists: {ico_path}")
        try:
            img = Image.open(ico_path)
            print(f"  Size: {img.size}, Mode: {img.mode}")
            print(f"  Format: {img.format}")
            if hasattr(img, 'n_frames'):
                print(f"  Frames: {img.n_frames}")
        except Exception as e:
            print(f"  Error loading: {e}")
    else:
        print(f"ICO not found: {ico_path}")

if __name__ == "__main__":
    test_icon()