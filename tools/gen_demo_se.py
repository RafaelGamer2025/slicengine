"""Gera o pacote de demonstração demo_game.se (formato próprio .se)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine.seformat import SEFormat  # noqa: E402
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

SCRIPT_SL = """
quando iniciar:
    definir "vida" como 100
    mostrar texto "Demo .se carregada!" por 3

quando tecla "espaço" for pressionada:
    aumentar 1 no "JOGO"
    tocar som "pulo.wav"
"""

SCRIPT_LUA = """
engine.on_event("iniciar", function(api)
    engine.set_var("pontos_lua", 0)
    api.mostrar_texto("Lua dentro do .se OK", 2)
end)
"""

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(base, "examples", "demo_game.se")
    world = World.from_ascii(MAPA)
    world.flags = {
        "title": "Demo .se",
        "mode": "3d",
        "author": "SlicEngine",
        "version": "1.0",
        "scripts": ["main.sl", "extra.lua"],
    }
    fmt = SEFormat()
    fmt.save(world, out, title="Demo .se", author="SlicEngine",
             mode="3d", scripts={
                 "main.sl": SCRIPT_SL,
                 "extra.lua": SCRIPT_LUA,
                 "README.txt": "Pacote de demonstração da SlicEngine (.se)",
             })
    print("Pacote criado:", os.path.abspath(out))
