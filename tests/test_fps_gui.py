"""Teste GUI do FPS: roda alguns frames e salva screenshot com HUD."""
import math
import os
import sys
import time

import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import Engine  # noqa: E402
from slicengine.fps import FPSGame, Enemy  # noqa: E402

MAPA = """
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

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
engine = Engine("FpsGui", 800, 480, base_dir=base)
engine.build_from_ascii(MAPA, "FPS GUI Test")

engine.world.entities = [
    Enemy(e.x, e.y) if e.kind == "enemy" else e
    for e in engine.world.entities]
fps = FPSGame(engine, gun_sprite=engine.assets.sprite("assets/gun.png"),
              enemy_sprite=engine.assets.sprite("assets/enemy_fps.png"))
fps.respawn_enemies([(3.5, 1.5), (7.5, 1.5), (3.5, 3.5)])

# apontar para o inimigo à frente e atirar
fps.rc.angle = math.atan2(1.5 - 1.5, 3.5 - 1.5)
fps.shoot()

# renderizar
fps.rc.render(engine.screen,
              [{"x": e.x, "y": e.y, "surface": engine.assets.sprite(
                  "assets/enemy_fps.png")}
               for e in engine.world.entities if e.alive])
fps.render_hud(engine.screen)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots",
                   "demo_fps.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
pygame.image.save(engine.screen, out)
print("screenshot salvo:", out)
