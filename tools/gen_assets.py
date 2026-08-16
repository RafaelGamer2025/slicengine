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

# ---------------- arma (sprite do FPS) ----------------
gun = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
d = ImageDraw.Draw(gun)
# corpo da pistola
for y in range(96, 128):
    for x in range(30, 98):
        shade = 70 + (y - 96) * 2
        gun.putpixel((x, y), (shade, shade - 8, shade - 16, 255))
d.rectangle([26, 92, 102, 102], fill=(55, 50, 45, 255))
d.rectangle([34, 40, 94, 96], fill=(85, 80, 75, 255))
d.rectangle([40, 30, 88, 44], fill=(110, 105, 100, 255))
d.rectangle([48, 18, 80, 32], fill=(140, 135, 130, 255))
d.ellipse([44, 12, 84, 28], fill=(170, 165, 160, 255))  # cano
gun.save(os.path.join(OUT, "gun.png"))

# ---------------- inimigo do FPS (maior, sprite 64x64) ----------------
fps_enemy = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(fps_enemy)
d.ellipse([6, 6, 58, 58], fill=(160, 40, 40, 255))
d.ellipse([14, 14, 28, 28], fill=(255, 240, 60, 255))   # olho esq
d.ellipse([36, 14, 50, 28], fill=(255, 240, 60, 255))   # olho dir
d.ellipse([17, 17, 25, 25], fill=(20, 0, 0, 255))
d.ellipse([39, 17, 47, 25], fill=(20, 0, 0, 255))
# boca
d.polygon([(20, 42), (44, 42), (40, 52), (24, 52)], fill=(10, 0, 0, 255))
fps_enemy.save(os.path.join(OUT, "enemy_fps.png"))

# ---------------- inimigos variados do FPS ----------------
# ranged (vermelho com mira/arma) — 64x64
e_fps_ranged = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(e_fps_ranged)
d.ellipse([6, 6, 58, 58], fill=(190, 70, 200, 255))
d.ellipse([14, 14, 28, 28], fill=(255, 240, 60, 255))
d.ellipse([36, 14, 50, 28], fill=(255, 240, 60, 255))
d.ellipse([17, 17, 25, 25], fill=(20, 0, 0, 255))
d.ellipse([39, 17, 47, 25], fill=(20, 0, 0, 255))
d.ellipse([24, 38, 40, 54], fill=(60, 20, 80, 255))  # focinho/arma
d.rectangle([28, 40, 36, 48], fill=(10, 10, 10, 255))  # cano
e_fps_ranged.save(os.path.join(OUT, "enemy_ranged.png"))

# fast (verde, esguio) — 64x64
e_fps_fast = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(e_fps_fast)
d.ellipse([10, 8, 54, 56], fill=(60, 180, 60, 255))
d.ellipse([16, 14, 28, 26], fill=(255, 255, 100, 255))
d.ellipse([36, 14, 48, 26], fill=(255, 255, 100, 255))
d.ellipse([18, 16, 24, 22], fill=(0, 0, 0, 255))
d.ellipse([38, 16, 44, 22], fill=(0, 0, 0, 255))
# sorriso malvado
d.arc([20, 40, 44, 56], 180, 360, fill=(0, 0, 0, 255), width=3)
e_fps_fast.save(os.path.join(OUT, "enemy_fast.png"))

# tank (cinza, enorme) — 64x64
e_fps_tank = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(e_fps_tank)
d.ellipse([2, 2, 62, 62], fill=(90, 90, 100, 255))
d.ellipse([10, 10, 26, 26], fill=(255, 80, 80, 255))
d.ellipse([38, 10, 54, 26], fill=(255, 80, 80, 255))
d.ellipse([14, 14, 22, 22], fill=(0, 0, 0, 255))
d.ellipse([42, 14, 50, 22], fill=(0, 0, 0, 255))
d.rectangle([18, 40, 46, 50], fill=(30, 30, 40, 255))  # maxila
e_fps_tank.save(os.path.join(OUT, "enemy_tank.png"))

# ---------------- coletáveis do FPS ----------------
# medkit (kit médico branco/vermelho)
medkit = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
d = ImageDraw.Draw(medkit)
d.rounded_rectangle([4, 10, 44, 40], radius=4, fill=(235, 235, 240, 255))
d.rounded_rectangle([4, 10, 44, 40], radius=4, outline=(120, 120, 130, 255),
                    width=2)
# cruz vermelha
d.rectangle([20, 18, 28, 32], fill=(220, 40, 40, 255))
d.rectangle([15, 22, 33, 28], fill=(220, 40, 40, 255))
medkit.save(os.path.join(OUT, "medkit.png"))

# power-up munição (caixa lourada com bala)
ammo = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
d = ImageDraw.Draw(ammo)
d.rounded_rectangle([6, 12, 42, 40], radius=3, fill=(180, 130, 50, 255))
d.rounded_rectangle([6, 12, 42, 40], radius=3, outline=(90, 60, 20, 255),
                    width=2)
d.rectangle([12, 16, 36, 20], fill=(255, 220, 120, 255))
d.rectangle([21, 24, 27, 36], fill=(60, 50, 40, 255))  # bala
ammo.save(os.path.join(OUT, "power_ammo.png"))

# power-up velocidade (raio azul)
spd = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
d = ImageDraw.Draw(spd)
d.ellipse([4, 4, 44, 44], fill=(40, 120, 255, 255))
d.ellipse([8, 8, 40, 40], fill=(90, 170, 255, 255))
d.polygon([(26, 8), (16, 26), (24, 26), (22, 40), (34, 20), (26, 20)],
          fill=(255, 255, 100, 255))
spd.save(os.path.join(OUT, "power_speed.png"))

# power-up dano (fogo vermelho)
dmg = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
d = ImageDraw.Draw(dmg)
d.ellipse([4, 4, 44, 44], fill=(220, 40, 40, 255))
d.ellipse([8, 8, 40, 40], fill=(255, 120, 40, 255))
d.ellipse([16, 16, 32, 32], fill=(255, 230, 80, 255))
d.polygon([(24, 10), (18, 24), (30, 24)], fill=(255, 255, 200, 255))
dmg.save(os.path.join(OUT, "power_damage.png"))

# power-up saúde (coração verde)
heal = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
d = ImageDraw.Draw(heal)
d.ellipse([4, 4, 44, 44], fill=(40, 200, 80, 255))
d.ellipse([8, 8, 40, 40], fill=(90, 240, 130, 255))
d.polygon([(24, 12), (14, 28), (34, 28)], fill=(255, 255, 255, 255))
d.rectangle([18, 28, 30, 36], fill=(255, 255, 255, 255))
heal.save(os.path.join(OUT, "power_health.png"))

# ---------------- sons procedurais ----------------
try:
    import wave
    import struct

    SOUNDS = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "sounds")
    os.makedirs(SOUNDS, exist_ok=True)

    SR = 22050  # sample rate

    def write_wav(path, samples):
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(b"".join(
                struct.pack("<h", int(max(-32768, min(32767, s))))
                for s in samples))

    def env(i, n, a=0.005, r=0.25):
        """Envelope ADSR simples."""
        if i < a * SR:
            return i / (a * SR)
        return max(0.0, 1 - (i - a * SR) / (r * SR))

    # tiro.wav — click + ruído curto
    n = int(0.18 * SR)
    random.seed(111)
    samples = [(-1 + 2 * random.random()) * env(i, n, r=0.06) * 9000
               + math.sin(2 * math.pi * 120 * i / SR) * env(i, n, r=0.12)
               * 4000 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "tiro.wav"), samples)

    # dano.wav — tom grave descendente
    n = int(0.3 * SR)
    samples = [math.sin(2 * math.pi * (300 - 180 * i / n) * i / SR)
               * env(i, n, r=0.2) * 7000 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "dano.wav"), samples)

    # moeda.wav — bip agudo
    n = int(0.25 * SR)
    samples = [math.sin(2 * math.pi * 880 * i / SR) * env(i, n, r=0.15)
               * 5000 + math.sin(2 * math.pi * 1320 * i / SR)
               * env(i, n, r=0.15) * 2500 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "moeda.wav"), samples)

    # pulo.wav — whoosh
    n = int(0.2 * SR)
    random.seed(222)
    samples = [math.sin(2 * math.pi * (200 + 300 * i / n) * i / SR)
               * env(i, n, r=0.12) * 4500 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "pulo.wav"), samples)

    # inicio.wav — acorde curto
    n = int(0.5 * SR)
    samples = [sum(math.sin(2 * math.pi * f * i / SR)
                   for f in (262, 330, 392)) * env(i, n, r=0.35)
               * 2200 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "inicio.wav"), samples)

    # powerup.wav — jingle ascendente
    n = int(0.35 * SR)
    samples = [math.sin(2 * math.pi * (440 + 440 * i / n) * i / SR)
               * env(i, n, r=0.25) * 4500 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "powerup.wav"), samples)

    # heal.wav — tom suave ascendente em duas notas
    n = int(0.45 * SR)
    samples = [math.sin(2 * math.pi * (523 + 261 * (i / n > 0.5)) * i / SR)
               * env(i, n, r=0.3) * 4000 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "heal.wav"), samples)

    # morte.wav — gemido descendente
    n = int(0.5 * SR)
    samples = [math.sin(2 * math.pi * (400 - 280 * i / n) * i / SR)
               * env(i, n, r=0.35) * 6000 for i in range(n)]
    write_wav(os.path.join(SOUNDS, "morte.wav"), samples)
    print("sons gerados em", SOUNDS)
except Exception as e:
    print("aviso: sons não gerados:", e)

print("assets gerados em", OUT)
for f in sorted(os.listdir(OUT)):
    print(" -", f)
try:
    for f in sorted(os.listdir(SOUNDS)):
        print(" -", f)
except Exception:
    pass
