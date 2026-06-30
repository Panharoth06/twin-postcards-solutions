"""Step 6 — Render the recovered raw RGB bytes into a viewable image.
Needs postcard.bin (produced by final.py).
Run:  ./venv/bin/python3 render.py
"""
from PIL import Image

W, H = 640, 480
data = open('postcard.bin', 'rb').read()
assert len(data) == W * H * 3, f"unexpected size {len(data)}"
img = Image.frombytes('RGB', (W, H), data)
img.save('postcard.png')
print("Saved postcard.png", img.size)
