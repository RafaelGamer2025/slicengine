"""
SlicEngine — Mundo, mapas (2D tile e grade do raycaster) e entidades.
"""
import json
import copy


class TileMap:
    """Mapa de tiles 2D com camadas, usado pelo jogo 2D e pelo editor."""

    def __init__(self, width=32, height=18, tile_size=32):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.layers = [{"name": "terreno", "tiles": [[0] * width for _ in range(height)]},
                       {"name": "decoração", "tiles": [[0] * width for _ in range(height)]}]
        self.active_layer = 0
        self.meta = {"name": "mapa sem título", "tile_size": tile_size}

    @property
    def pixels_w(self):
        return self.width * self.tile_size

    @property
    def pixels_h(self):
        return self.height * self.tile_size

    def get(self, x, y, layer=None) -> int:
        if layer is None:
            layer = self.active_layer
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.layers[layer]["tiles"][y][x]
        return 0

    def set(self, x, y, tile_id, layer=None):
        if layer is None:
            layer = self.active_layer
        if 0 <= x < self.width and 0 <= y < self.height:
            self.layers[layer]["tiles"][y][x] = tile_id

    def resize(self, width, height, fill=0):
        for layer in self.layers:
            tiles = layer["tiles"]
            new = [[fill] * width for _ in range(height)]
            for y in range(min(height, len(tiles))):
                row = tiles[y]
                for x in range(min(width, len(row))):
                    new[y][x] = row[x]
            layer["tiles"] = new
        self.width, self.height = width, height

    def to_dict(self) -> dict:
        return {
            "meta": self.meta,
            "size": [self.width, self.height, self.tile_size],
            "layers": [
                {"name": l["name"], "tiles": l["tiles"]}
                for l in self.layers
            ],
            "active_layer": self.active_layer,
        }

    @classmethod
    def from_dict(cls, data: dict):
        m = cls.__new__(cls)
        w, h, ts = data["size"]
        m.width, m.height, m.tile_size = w, h, ts
        m.meta = data.get("meta", {})
        m.layers = [
            {"name": l["name"], "tiles": [row[:] for row in l["tiles"]]}
            for l in data["layers"]
        ]
        m.active_layer = data.get("active_layer", 0)
        return m

    def copy(self):
        return TileMap.from_dict(self.to_dict())


class Entity:
    """Entidade genérica (jogador, inimigo, item)."""

    def __init__(self, kind: str, x=0.0, y=0.0, data=None):
        self.kind = kind
        self.x, self.y = x, y
        self.data = data or {}
        self.alive = True

    def to_dict(self):
        return {"kind": self.kind, "x": self.x, "y": self.y,
                "data": self.data}

    @classmethod
    def from_dict(cls, d):
        return cls(d["kind"], d["x"], d["y"], d.get("data"))


class World:
    """Mundo do jogo: combina tile map e (opcionalmente) mapa do raycaster,
    além de entidades e variáveis globais do jogo."""

    def __init__(self):
        self.tilemap = TileMap()
        self.raycast_map = None          # list[list[int]] p/ modo 3D
        self.entities: list[Entity] = []
        self.variables: dict = {}
        self.flags: dict = {}

    # ------------------------------------------------------------------
    # Construção a partir de texto ASCII (rápido para demos)
    # ------------------------------------------------------------------
    @staticmethod
    def from_ascii(ascii_map: str, tile_size=32):
        """'#' = parede, '.' = chão, 'P' = jogador, 'E' = inimigo.
        Retorna World."""
        rows = [line.rstrip() for line in ascii_map.strip().splitlines()
                if line.strip()]
        h = len(rows)
        w = max(len(r) for r in rows)
        tm = TileMap(w, h, tile_size)
        world = World()
        world.tilemap = tm
        grid = []
        for y, row in enumerate(rows):
            grid_row = []
            for x, ch in enumerate(row.ljust(w)):
                if ch == '#':
                    tm.set(x, y, 1)
                    grid_row.append(1)
                elif ch == 'P':
                    world.entities.append(Entity("player", x + 0.5, y + 0.5))
                    grid_row.append(0)
                elif ch == 'E':
                    world.entities.append(Entity("enemy", x + 0.5, y + 0.5))
                    grid_row.append(0)
                elif ch == 'C':
                    world.entities.append(Entity("coin", x + 0.5, y + 0.5))
                    grid_row.append(0)
                else:
                    grid_row.append(0)
            grid.append(grid_row)
        world.raycast_map = grid
        world.flags["mode"] = "2d"
        return world

    def add_entity(self, kind: str, x: float, y: float):
        """Cria e adiciona uma entidade ao mundo (usada pelo editor
        em drag & drop)."""
        if kind in ("player", "enemy", "coin"):
            self.entities.append(Entity(kind, float(x), float(y)))
        else:
            self.entities.append(Entity(kind, float(x), float(y)))
        return self.entities[-1]

    def to_dict(self) -> dict:
        return {
            "tilemap": self.tilemap.to_dict(),
            "raycast_map": self.raycast_map,
            "entities": [e.to_dict() for e in self.entities],
            "variables": self.variables,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, data: dict):
        w = cls()
        w.tilemap = TileMap.from_dict(data["tilemap"])
        w.raycast_map = data.get("raycast_map")
        w.entities = [Entity.from_dict(e) for e in data.get("entities", [])]
        w.variables = data.get("variables", {})
        w.flags = data.get("flags", {})
        return w

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=1)

    @classmethod
    def from_json(cls, text: str):
        return cls.from_dict(json.loads(text))
