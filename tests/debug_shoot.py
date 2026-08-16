"""Debug: por que shoot() não acerta quando a mira aponta para o inimigo?"""
import math
import os
import sys

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

engine = Engine("Dbg", 640, 400,
                base_dir=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
engine.build_from_ascii(MAPA, "dbg")
engine.world.entities = [
    Enemy(e.x, e.y) if e.kind == "enemy" else e
    for e in engine.world.entities]
fps = FPSGame(engine)
fps.respawn_enemies([(3.5, 1.5), (7.5, 1.5)])

rc = fps.rc
print("player:", rc.x, rc.y)
for e in fps.enemies():
    d = math.hypot(e.x - rc.x, e.y - rc.y)
    ang = math.atan2(e.y - rc.y, e.x - rc.x)
    print(f"inimigo em ({e.x:.1f},{e.y:.1f}) dist={d:.2f} ang={math.degrees(ang):.0f}")
    rc.angle = ang
    wall = fps._wall_between(d)
    print(f"  mira={math.degrees(rc.angle):.0f} wall_between={wall}")
    # debug: traçar o raio manualmente em grid para achar a parede
    rx, ry = math.cos(rc.angle), math.sin(rc.angle)
    px, py = rc.x, rc.y
    print("  trilha do raio:", end="")
    for _ in range(40):
        px += rx * 0.1
        py += ry * 0.1
        gx, gy = int(px), int(py)
        if 0 <= gy < len(rc.map) and 0 <= gx < len(rc.map[0]) \
                and rc.map[gy][gx]:
            print(f" PAREDE em ({gx},{gy})")
            break
    else:
        print(" nenhum tile atingido")
    # debug do cone manualmente
    diff = math.atan2(math.sin(ang - rc.angle), math.cos(ang - rc.angle))
    half = math.atan2(0.45, d)
    print(f"  diff={math.degrees(diff):.2f} half={math.degrees(half):.2f}")
    print(f"  hit={fps.shoot()} hp={e.hp}")
