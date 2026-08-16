"""Gera assets de demonstração da SlicEngine (procedural, sem internet).

Gera PNGs: wall1-4.png, tile1-8.png, player.png, enemy.png, coin.png
e o GIF animado menu_bg.gif em assets/.
"""
import os
import math
import random
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets")
os.makedirs(OUT, exist_ok=True)

random.seed(42)


def noise_texture(w, h, base, variation, pattern="bricks", seed=0):
    random.seed(seed)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = random.uniform(-variation, variation)
            r = max(0, min(255, base[0] + v))
            g = max(0, min(255, base[1] + v))
            b = max(0, min(255, base[2] + v * 0.7))
            if pattern == "bricks":
                # linhas de argamassa
                bh = h // 4
                if y % bh < 3 or (y // bh) % 2 == 0 and (x + bh // 2) % (w // 2) < 3:
                    r, g, b = base[0] * 0.35, base[1] * 0.35, base[2] * 0.35
            elif pattern == "stone":
                if (x * 7 + y * 13) % 97 < 4:
                    r *= 0.6; g *= 0.6; b *= 0.6
            elif pattern == "metal":
                if x % 32 < 2 or y % 32 < 2:
                    r *= 0.55; g *= 0.55; b *= 0.65
            px[x, y] = (int(r), int(g), int(b))
    return img


def sprite_circle(w, h, color, eye, body_fn=None):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, w - 4, h - 4], fill=color + (255,))
    # olhos
    d.ellipse([w//2 - 14, h//2 - 10, w//2 - 4, h//2], fill=(255, 255, 255, 255))
    d.ellipse([w//2 + 4, h//2 - 10, w//2 + 14, h//2], fill=(255, 255, 255, 255))
    d.ellipse([w//2 - 11, h//2 - 7, w//2 - 5, h//2 - 1], fill=eye + (255,))
    d.ellipse([w//2 + 7, h//2 - 7, w//2 + 13, h//2 - 1], fill=eye + (255,))
    if body_fn:
        body_fn(d, w, h)
    return img


# ---------------- paredes ----------------
wall1 = noise_texture(64, 64, (150, 110, 70), 25, "bricks", 1)
wall1.save(os.path.join(OUT, "wall1.png"))
wall2 = noise_texture(64, 64, (100, 100, 110), 20, "stone", 2)
wall2.save(os.path.join(OUT, "wall2.png"))
wall3 = noise_texture(64, 64, (70, 120, 70), 30, "bricks", 3)
wall3.save(os.path.join(OUT, "wall3.png"))
wall4 = noise_texture(64, 64, (90, 85, 100), 18, "metal", 4)
wall4.save(os.path.join(OUT, "wall4.png"))

# ---------------- tiles (modo 2D) ----------------
for tid, (base, pattern, seed) in {
        1: ((150, 110, 70), "bricks", 5),
        2: ((60, 130, 60), "stone", 6),
        3: ((70, 120, 180), "metal", 7),
        4: ((150, 150, 150), "stone", 8),
        5: ((180, 50, 50), "bricks", 9),
        6: ((200, 160, 60), "bricks", 10),
        7: ((90, 60, 140), "stone", 11),
        8: ((40, 170, 170), "metal", 12),
}.items():
    t = noise_texture(32, 32, base, 20, pattern, seed)
    t.save(os.path.join(OUT, f"tile{tid}.png"))

# ---------------- entidades ----------------
player = sprite_circle(48, 48, (60, 150, 255), (20, 40, 80))
player.save(os.path.join(OUT, "player.png"))
enemy = sprite_circle(48, 48, (200, 60, 60), (0, 0, 0))
enemy.save(os.path.join(OUT, "enemy.png"))

coin_img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
d = ImageDraw.Draw(coin_img)
d.ellipse([2, 2, 30, 30], fill=(255, 215, 0, 255))
d.ellipse([8, 8, 24, 24], fill=(255, 235, 100, 255))
coin_img.save(os.path.join(OUT, "coin.png"))

# ---------------- GIF de menu ----------------
frames = []
W, H = 640, 360
for k in range(20):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    # céu noturno animado
    for y in range(H):
        r = 10 + int(18 * math.sin(k * 0.5 + y * 0.02))
        g = 8
        b = 30 + int(25 * math.cos(k * 0.3 + y * 0.03))
        d.line([(0, y), (W, y)], fill=(r, g, b, 255))
    # estrelas piscando
    random.seed(7 + k)
    for _ in range(60):
        x = random.randint(0, W)
        y = random.randint(0, H // 2)
        a = 120 + int(135 * abs(math.sin(k + x)))
        d.point((x, y), fill=(255, 255, 255, a))
    # montanhas
    d.polygon([(0, H), (0, H - 60), (160, H - 110), (320, H - 70),
               (480, H - 120), (W, H - 80), (W, H)],
              fill=(25, 20, 45, 255))
    # sol/lua
    cx = 120 + k * 26
    d.ellipse([cx - 30, 140 - 30, cx + 30, 140 + 30],
              fill=(255, 200, 80, 255))
    frames.append(img)
frames[0].save(os.path.join(OUT, "menu_bg.gif"), save_all=True,
               append_images=frames[1:], duration=120, loop=0)

print("assets gerados em", OUT)
for f in sorted(os.listdir(OUT)):
    print(" -", f)
