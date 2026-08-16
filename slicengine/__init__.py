"""
SlicEngine — game engine em Python (com Lua e C).

Jogos 3D raycasting estilo Doom, jogos 2D com tile maps, editor com
pincel, mods, formato .se, scripting em português, IA assistente,
terminal embutido, perfis em banco de dados e hierarquia de cena.

Uso rápido:
    from slicengine import Engine

    e = Engine("Meu Jogo", 800, 600)
    e.build_from_ascii('''
        ##########
        #P...E...#
        #.###.##.#
        #...#..C.#
        ##########
    ''')
    e.run()
"""
from .core import Engine
from .world import World, TileMap, Entity
from .raycaster import Raycaster
from .editor import MapEditor
from .modsystem import ModSystem
from .seformat import SEFormat
from .assets import AssetManager
from .hierarchy import Hierarchy, HierarchyNode
from .local import ScriptRunner, Shell
from .profile_db import ProfileDB
from .aiscript import AIAssistant
from .ptscript import PTScript
from . import utils

VERSION = utils.VERSION
ENGINE_NAME = utils.ENGINE_NAME

__all__ = [
    "Engine", "World", "TileMap", "Entity", "Raycaster", "MapEditor",
    "ModSystem", "SEFormat", "AssetManager", "Hierarchy",
    "HierarchyNode", "ScriptRunner", "Shell", "ProfileDB",
    "AIAssistant", "PTScript", "VERSION", "ENGINE_NAME",
]
