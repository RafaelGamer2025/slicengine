"""
SlicEngine — Demo 3D raycasting estilo Doom.

Use o teclado para andar e olhar ao redor. Este arquivo mostra como usar a
engine como biblioteca Python (import slicengine) em vez do modo editor.

Execução:
    python -m slicengine examples/demo_3d.py
    ou
    python examples/demo_3d.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import Engine  # noqa: E402

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
    engine = Engine("Dungeon Slic", 800, 480, base_dir=base)
    engine.build_from_ascii(MAPA, "Demo 3D — Dungeon")
    engine.run()
