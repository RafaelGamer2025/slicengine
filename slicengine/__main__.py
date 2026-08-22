"""
SlicEngine — Interface de linha de comando.

Uso:
    python -m slicengine                  → menu da engine
    python -m slicengine --editor         → editor com pincel
    python -m slicengine --run jogo.se    → rodar um pacote .se
    python -m slicengine --run-dir .      → rodar projeto da pasta
    python -m slicengine --ai "pergunta"  → perguntar à IA assistente
    python -m slicengine --shell          → shell interativo (pip etc.)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import Engine, utils  # noqa: E402
from slicengine.world import World  # noqa: E402


DEMO_MAP_3D = """
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

DEMO_MAP_2D = """
################
#P.C...........#
#...########...#
#...#......#...#
#...#.C.E..#...#
#...#......#..C#
#...########...#
#......C.......#
################
"""


def main():
    args = sys.argv[1:]
    base = os.getcwd()

    if not args or args[0] == "--menu":
        engine = Engine("SlicEngine", 800, 600, base_dir=base)
        if args and args[0] == "--menu":
            # menu clássico com GIF (compatibilidade)
            engine.set_menu(
                gif=_try_load_gif(base),
                title="SlicEngine",
                subtitle="ENTER = demo 3D  |  E = editor  |  "
                         "D = demo 2D  |  ESC = sair",
                start_action=lambda: _run_demo(engine, "3d"))
            # atalhos no menu
            engine.adicionar_evento("tecla:e", lambda api, p: (
                setattr(engine, "state", "editor"), engine.state))
            engine.adicionar_evento("tecla:d", lambda api, p: (
                _run_demo(engine, "2d"),))
        else:
            # experiência de entrada completa: menu / jogo / perfil
            engine.run_entry()
        engine.run()

    elif args[0] == "--editor":
        engine = Engine("SlicEngine Editor", 900, 640, base_dir=base)
        engine.state = "editor"
        engine.run()

    elif args[0] == "--run":
        if len(args) < 2:
            print("Uso: python -m slicengine --run jogo.se")
            sys.exit(1)
        engine = Engine("SlicEngine", 800, 600, base_dir=base)
        engine.load_package(args[1])
        engine.run()

    elif args[0] == "--run-dir":
        base_run = args[1] if len(args) > 1 else "."
        engine = Engine("SlicEngine", 800, 600, base_dir=base_run)
        # procurar world.json na pasta do projeto
        import json
        wpath = os.path.join(engine.base_dir, "world.json")
        if os.path.exists(wpath):
            with open(wpath) as f:
                engine.world = World.from_json(f.read())
        engine._setup_scene()
        engine.run()

    elif args[0] == "--ai":
        prompt = " ".join(args[1:]) if len(args) > 1 else "ajuda"
        ai = utils  # placeholder
        from slicengine.aiscript import AIAssistant
        print(AIAssistant().ask_online(prompt))

    elif args[0] == "--shell":
        from slicengine.local import Shell
        shell = Shell(workdir=base)
        print("Shell SlicEngine (digite 'sair' para sair)")
        while True:
            try:
                cmd = input("slic> ")
            except (EOFError, KeyboardInterrupt):
                break
            if cmd.strip().lower() in ("sair", "exit", "quit"):
                break
            print(shell.run(cmd))

    elif args[0] in ("--help", "-h"):
        print(__doc__)
    else:
        print(f"Opção desconhecida: {args[0]}\n{__doc__}")
        sys.exit(1)


def _run_demo(engine, mode):
    if mode == "3d":
        engine.build_from_ascii(DEMO_MAP_3D, "Demo 3D — Estilo Doom")
    else:
        engine.build_from_ascii(DEMO_MAP_2D, "Demo 2D — Tile Map")
    engine.state = "game"


def _try_load_gif(base: str):
    for cand in ("assets/menu_bg.gif", "menu_bg.gif",
                 "assets/menu.gif", "menu.gif"):
        if os.path.exists(os.path.join(base, cand)):
            try:
                from slicengine.assets import AssetManager
                am = AssetManager(base)
                return am.gif(cand)
            except Exception:
                return None
    return None


if __name__ == "__main__":
    main()
