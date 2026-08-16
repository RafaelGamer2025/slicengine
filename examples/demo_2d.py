"""
SlicEngine — Demo 2D com tile map.

Mostra um mundo 2D de tiles com entidades (player, inimigos, moedas).
As setas movem o player; colete as moedas.

Execução:
    python -m slicengine examples/demo_2d.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import Engine  # noqa: E402
from slicengine.world import World  # noqa: E402

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

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    engine = Engine("Mundo 2D", 800, 480, base_dir=base)
    engine.build_from_ascii(MAPA, "Demo 2D — Tile Map")
    engine.mode = "2d"
    engine.run()
