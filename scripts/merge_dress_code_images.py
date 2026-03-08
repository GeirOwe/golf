#!/usr/bin/env python3
"""
Merge dress code images into one (vertical stack).
Run from project root: python scripts/merge_dress_code_images.py
Requires: pip install Pillow
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    sys.exit(1)

# Paths relative to project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = [
    os.path.join(ROOT, "IMG_1315.jpeg"),
    os.path.join(ROOT, "IMG_1318.jpeg"),
]
OUTPUT = os.path.join(ROOT, "static", "dress_code_merged.jpeg")

def main():
    images = []
    for path in SOURCES:
        if not os.path.exists(path):
            print(f"Mangler: {path}")
            sys.exit(1)
        images.append(Image.open(path).convert("RGB"))

    # Same width = widest image; stack vertically
    width = max(im.width for im in images)
    heights = [im.height for im in images]
    total_height = sum(heights)

    merged = Image.new("RGB", (width, total_height))
    y = 0
    for im in images:
        # Center if narrower than width
        x = (width - im.width) // 2
        merged.paste(im, (x, y))
        y += im.height

    merged.save(OUTPUT, "JPEG", quality=90)
    print(f"Lagret: {OUTPUT}")

if __name__ == "__main__":
    main()
