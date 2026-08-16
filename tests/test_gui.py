"""Teste GUI automatizado: renderiza demos e salva screenshots."""
import os
import sys
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import Engine, ScriptRunner

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUT, exist_ok=True)

# ---------- demo 3D ----------
MAP3D = """
####################
#P..#....#.....#...#
#...#....#..E..#...#
#...####.#####.C...#
#.............#....#
#.E.......#...######
#.........#........#
####.#####.####.#.##
#....#...#........##
#....#...#.E.......#
####################
"""
e = Engine("Shot3D", 640, 400)
e.build_from_ascii(MAP3D, "Demo 3D")
e.state = "game"
import time
for i in range(3):
    e._last = time.perf_counter()
    for ev in pygame.event.get():
        pass
    keys = {pygame.K_w: True, pygame.K_d: True}
    if e.raycaster:
        e.raycaster.angle += 0.25
        e.raycaster.move(keys, 0.016)
    e._update_2d_entities(keys, 0.016)
# render 3D real
if e.raycaster:
    sprites = [
        {"x": ent.x, "y": ent.y, "surface": __import__("pygame").Surface((16, 16))}
        for ent in e.world.entities if ent.alive]
    e.raycaster.render(e.screen, sprites)
pygame.display.flip()
pygame.image.save(e.screen, os.path.join(OUT, "demo_3d.png"))
print("shot 3d ok")

# ---------- demo 2D ----------
MAP2D = """
################
#P.C...........#
#...########...#
#...#......#...#
#...#.C.E..#...#
################
"""
os.makedirs(OUT + "/d2d", exist_ok=True)
e2 = Engine("Shot2D", 640, 400, base_dir=OUT + "/d2d")
e2.build_from_ascii(MAP2D, "Demo 2D")
e2.state = "game"
e2._last = __import__("time").perf_counter()
for ev in pygame.event.get():
    pass
keys = pygame.key.get_pressed()
e2._update_2d_entities(keys, 0.016)
e2._draw_2d()
pygame.display.flip()
pygame.image.save(e2.screen, os.path.join(OUT, "demo_2d.png"))
print("shot 2d ok")

# ---------- menu com GIF ----------
# gerar GIF de teste
from PIL import Image, ImageDraw
frames = []
for k in range(6):
    im = Image.new("RGBA", (320, 200), (30 + k * 20, 20, 60 - k * 8, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([100 + k * 10, 40, 220 + k * 10, 160], fill=(255, 220, 60, 255))
    frames.append(im)
gif_path = os.path.join(OUT, "menu_bg.gif")
frames[0].save(gif_path, save_all=True, append_images=frames[1:],
               duration=100, loop=0)

os.makedirs(OUT + "/dm", exist_ok=True)
e3 = Engine("ShotMenu", 640, 400, base_dir=OUT + "/dm")
e3.set_menu(gif=e3.assets.gif(gif_path), title="TESTE GIF",
            subtitle="ENTER para jogar",
            start_action=lambda: None)
e3.state = "menu"
e3.elapsed = 0.3
e3._draw_menu()
pygame.display.flip()
pygame.image.save(e3.screen, os.path.join(OUT, "menu_gif.png"))
print("shot menu ok")

pygame.quit()
print("GUI TESTS OK")
