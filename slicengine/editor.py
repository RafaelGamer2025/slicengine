"""
SlicEngine — Editor de mapas com PINCEL.

Ferramentas:
- Pincel (desenhar/apagar tiles em qualquer camada)
- Borracha
- Seletor de camada
- Paleta de tiles (grade de miniaturas)
- Testar jogo (play rápido)
- Salvar/carregar em .se

Atalhos: B = pincel, E = borracha, L = camada, Ctrl+S = salvar, T = testar
"""
import os
import pygame
from .world import TileMap, World
from .seformat import SEFormat

# paleta de cores de tiles por id (usadas para gerar miniaturas quando
# não há sprite; sprites reais substituem via atlas)
TILE_COLORS = {
    0: (30, 30, 34), 1: (120, 90, 60), 2: (60, 130, 60),
    3: (70, 120, 180), 4: (150, 150, 150), 5: (180, 50, 50),
    6: (200, 160, 60), 7: (90, 60, 140), 8: (40, 170, 170),
}

TOOL_BRUSH, TOOL_ERASER, TOOL_FILL = "brush", "eraser", "fill"
TOOL_ENTITY = "entity"


class TilePalette:
    """Grade de tiles selecionáveis."""

    def __init__(self, tile_size=32):
        self.tile_size = tile_size
        self.selected = 1
        self.ids = list(TILE_COLORS.keys())  # 0 = vazio (borracha)

    def draw(self, surface: pygame.Surface, x0, y0):
        ts = self.tile_size
        cols = 3
        for i, tid in enumerate(self.ids):
            px = x0 + (i % cols) * (ts + 6)
            py = y0 + (i // cols) * (ts + 6)
            color = TILE_COLORS[tid]
            rect = pygame.Rect(px, py, ts, ts)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (255, 255, 255), rect, 1)
            if tid == self.selected:
                pygame.draw.rect(surface, (255, 220, 60), rect, 3)
            # número do tile
            font = pygame.font.SysFont("dejavusans", 12, bold=True)
            lbl = font.render(str(tid), True, (255, 255, 255))
            surface.blit(lbl, (px + 3, py + 2))

    def hit(self, mx, my, x0, y0) -> int:
        ts = self.tile_size
        cols = 3
        for i, tid in enumerate(self.ids):
            px = x0 + (i % cols) * (ts + 6)
            py = y0 + (i // cols) * (ts + 6)
            if pygame.Rect(px, py, ts, ts).collidepoint(mx, my):
                return tid
        return -1


class MapEditor:
    """Editor de tile maps com pincel. Roda dentro da janela da engine."""

    def __init__(self, engine):
        self.engine = engine
        assets = engine.assets
        self.world = World()
        self.tilemap = self.world.tilemap
        self.tool = TOOL_BRUSH
        self.tile_size = self.tilemap.tile_size
        self.camera = pygame.Vector2(0, 0)
        self.brushing = False
        self.last_brush = None
        self.tool_size = 1          # tamanho do pincel (1, 2, 3...)
        self.paused_ticks = 0
        self.status_msg = "Editor SlicEngine — B=pincel, E=borracha, "+ \
                          "F=balde, N=entidade, Ctrl+Z/Y, Ctrl+S=salvar, " \
                          "T=testar"
        self.status_timer = 0.0
        self.palette = TilePalette(self.tile_size)

        # undo/redo: pilha de snapshots do tilemap
        self._undo_stack = []
        self._redo_stack = []
        self._undo_max = 40
        # modo entidade (P player, E inimigo, C moeda)
        self.entity_kind = None
        self.ENTITIES = [("P", "player"), ("E", "enemy"), ("C", "coin")]

        # carregar sprites da paleta, se existirem
        self.tile_sprites = {}
        for tid in range(1, 9):
            for name in (f"tile{tid}.png", f"tile_{tid}.png",
                         f"tiles/tile{tid}.png"):
                try:
                    self.tile_sprites[tid] = assets.sprite_raw(name)
                    break
                except (pygame.error, FileNotFoundError):
                    continue

    # ------------------------------------------------------------------
    def _world_pos(self, mx, my) -> tuple:
        sx = (mx + self.camera.x) // self.tile_size
        sy = (my + self.camera.y) // self.tile_size
        return int(sx), int(sy)

    # ------------------------------------------------------------------
    # Undo/Redo
    # ------------------------------------------------------------------
    def _snapshot(self):
        import copy
        data = {"layers": [copy.deepcopy(l["tiles"]) for l in
                           self.tilemap.layers],
                "active": self.tilemap.active_layer,
                "ents": [(e.kind, e.x, e.y) for e in
                         self.engine.world.entities]}
        self._undo_stack.append(data)
        if len(self._undo_stack) > self._undo_max:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        import copy
        if not self._undo_stack:
            return
        import copy as _copy
        self._redo_stack.append(
            {"layers": [_copy.deepcopy(l["tiles"]) for l in
                        self.tilemap.layers],
             "ents": [(e.kind, e.x, e.y) for e in
                      self.engine.world.entities]})
        data = self._undo_stack.pop()
        for l, tiles in zip(self.tilemap.layers, data["layers"]):
            l["tiles"] = tiles
        self.tilemap.active_layer = data["active"]
        self.status("Desfazer OK")

    def redo(self):
        import copy as _copy
        if not self._redo_stack:
            return
        self._undo_stack.append(
            {"layers": [_copy.deepcopy(l["tiles"]) for l in
                        self.tilemap.layers],
             "ents": [(e.kind, e.x, e.y) for e in
                      self.engine.world.entities]})
        data = self._redo_stack.pop()
        for l, tiles in zip(self.tilemap.layers, data["layers"]):
            l["tiles"] = tiles
        # restaurar entidades salvas
        from .world import Entity
        self.engine.world.entities = [Entity(k, x, y) for k, x, y in
                                      data["ents"]]
        self.status("Refazer OK")

    # ------------------------------------------------------------------
    def _paint(self, x, y, key=None):
        """Pinta célula (pincel, borracha ou preenchimento)."""
        if key is not None and key != (x, y):
            return  # célula já pintada (evita redundância)
        if self.tool == TOOL_ENTITY and self.entity_kind:
            # substituir entidade do tipo selecionado na célula
            for e in self.engine.world.entities:
                if int(e.x) == x and int(e.y) == y:
                    e.alive = False
            if self.entity_kind:
                self.engine.world.entities.append(
                    Entity(self.entity_kind, x + 0.5, y + 0.5))
            return
        if self.tool == TOOL_FILL:
            old = self.tilemap.get(x, y)
            new = 0 if old else self.palette.selected
            self._flood(x, y, old, new)
        elif self.tool == TOOL_ERASER:
            self.tilemap.set(x, y, 0)
        else:
            self.tilemap.set(x, y, self.palette.selected)

    def _flood(self, x, y, old, new):
        """Flood fill iterativo."""
        if old == new:
            return
        stack = [(x, y)]
        visited = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            if self.tilemap.get(cx, cy) != old:
                continue
            self.tilemap.set(cx, cy, new)
            for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                if (nx, ny) not in visited:
                    stack.append((nx, ny))

    # ------------------------------------------------------------------
    def _begin_stroke(self):
        """Marcar snapshot antes de pintar (chamado no primeiro clique
        de um traço)."""
        if self._undo_stack and self._undo_stack[-1] is self._stroke_snap:
            return
        self._snapshot()
        self._stroke_snap = self._undo_stack[-1]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                self.tool = TOOL_BRUSH
                self.status("Pincel selecionado")
            elif event.key == pygame.K_e:
                self.tool = TOOL_ERASER
                self.status("Borracha selecionada")
            elif event.key == pygame.K_f:
                self.tool = TOOL_FILL
                self.status("Balde de preenchimento")
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.tool_size = min(5, self.tool_size + 1)
            elif event.key == pygame.K_MINUS:
                self.tool_size = max(1, self.tool_size - 1)
            elif event.key == pygame.K_l:
                n = len(self.tilemap.layers)
                self.tilemap.active_layer = (self.tilemap.active_layer + 1) % n
                name = self.tilemap.layers[self.tilemap.active_layer]["name"]
                self.status(f"Camada: {name}")
            elif event.key == pygame.K_s and (pygame.key.get_mods()
                                              & pygame.KMOD_CTRL):
                self.save_current("mapa.se")
            elif event.key == pygame.K_t:
                return "test"   # sinal para engine entrar em modo jogo
            elif event.key == pygame.K_z and (pygame.key.get_mods()
                                              & pygame.KMOD_CTRL):
                self.undo()
            elif event.key == pygame.K_y and (pygame.key.get_mods()
                                              & pygame.KMOD_CTRL):
                self.redo()
            elif event.key == pygame.K_n:
                # alternar modo entidade: sem entidade -> player
                if self.entity_kind is None:
                    self.entity_kind = "player"
                    self.status("Modo entidade: player (P)")
                elif self.entity_kind == "player":
                    self.entity_kind = "enemy"
                    self.status("Modo entidade: inimigo (E)")
                elif self.entity_kind == "enemy":
                    self.entity_kind = "coin"
                    self.status("Modo entidade: moeda (C)")
                else:
                    self.entity_kind = None
                    self.tool = TOOL_BRUSH
                    self.status("Voltou para o pincel")
            elif event.key in (pygame.K_r,):
                self.status("Ctrl+Z desfaz, Ctrl+Y refaz")
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # clique na paleta?
                if self.palette.hit(event.pos[0], event.pos[1],
                                    10, 40) >= 0:
                    tid = self.palette.hit(event.pos[0], event.pos[1],
                                           10, 40)
                    self.palette.selected = tid
                    self.tool = TOOL_BRUSH if tid > 0 else TOOL_ERASER
                    return
                self.brushing = True
                self.last_brush = None
                self._stroke_snap = None
                self._begin_stroke()
                self._brush(event.pos[0], event.pos[1])
            elif event.button == 3:
                # botão direito = borracha
                self.brushing = True
                self.tool = TOOL_ERASER
                self.last_brush = None
                self._stroke_snap = None
                self._begin_stroke()
                self._brush(event.pos[0], event.pos[1])
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (1, 3):
                self.brushing = False
                self.last_brush = None
        elif event.type == pygame.MOUSEMOTION and self.brushing:
            self._brush(event.pos[0], event.pos[1])

    def _brush(self, mx, my):
        x, y = self._world_pos(mx, my)
        r = self.tool_size // 2
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                self._paint(x + dx, y + dy, self.last_brush)
        self.last_brush = (x, y)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        ts = self.tile_size
        # fundo
        surface.fill((20, 20, 26))
        # tiles
        cam_x = int(self.camera.x) // ts * ts
        cam_y = int(self.camera.y) // ts * ts
        x0 = max(0, -cam_x // ts)
        y0 = max(0, -cam_y // ts)
        x1 = min(self.tilemap.width,
                 (surface.get_width() - cam_x) // ts + 1)
        y1 = min(self.tilemap.height,
                 (surface.get_height() - cam_y) // ts + 1)
        for y in range(y0, y1):
            for x in range(x0, x1):
                tid = self.tilemap.get(x, y)
                px = x * ts - cam_x
                py = y * ts - cam_y
                if tid == 0:
                    # grade fina
                    pygame.draw.rect(surface, (36, 36, 42),
                                     (px, py, ts, ts))
                    pygame.draw.rect(surface, (44, 44, 50), (px, py, ts, ts), 1)
                    continue
                surf = self.tile_sprites.get(tid)
                if surf is not None:
                    surface.blit(surf, (px, py))
                else:
                    pygame.draw.rect(surface, TILE_COLORS.get(
                        tid, (100, 100, 100)), (px, py, ts, ts))
                    pygame.draw.rect(surface, (0, 0, 0), (px, py, ts, ts), 1)
        # grade do cursor do pincel
        mx, my = pygame.mouse.get_pos()
        gx, gy = self._world_pos(mx, my)
        r = self.tool_size // 2
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                rect = pygame.Rect((gx + dx) * ts - cam_x,
                                   (gy + dy) * ts - cam_y, ts, ts)
                pygame.draw.rect(surface, (255, 220, 60), rect, 2)
        # HUD
        font = pygame.font.SysFont("dejavusans", 14, bold=True)
        tool_name = {"brush": "Pincel", "eraser": "Borracha",
                     "fill": "Balde",
                     "entity": f"Entidade ({self.entity_kind})"}.get(
            self.tool, self.tool)
        hud = (f"Editor | {tool_name} (tam {self.tool_size}) | camada "
               f"{self.tilemap.active_layer} | {self.tilemap.width}x"
               f"{self.tilemap.height} | Ctrl+Z/Y | Ctrl+S salvar | "
               f"T testar")
        t = font.render(hud, True, (230, 230, 230))
        surface.blit(t, (10, 8))
        self.palette.draw(surface, 10, 40)
        # indicador do modo entidade
        if self.entity_kind:
            col = {"player": (60, 150, 255), "enemy": (220, 60, 60),
                   "coin": (255, 215, 0)}[self.entity_kind]
            pygame.draw.circle(surface, col, (120, 30), 12)
            pygame.draw.circle(surface, (255, 255, 255), (120, 30), 12, 1)
        if self.status_timer > 0:
            st = font.render(self.status_msg, True, (255, 240, 150))
            surface.blit(st, (10, surface.get_height() - 24))

    def update(self, dt):
        keys = pygame.key.get_pressed()
        spd = 300 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.camera.x += spd
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.camera.x -= spd
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.camera.y += spd
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.camera.y -= spd
        # limitar câmera
        self.camera.x = max(0, min(self.camera.x,
                                   self.tilemap.pixels_w - 400))
        self.camera.y = max(0, min(self.camera.y,
                                   self.tilemap.pixels_h - 300))
        self.status_timer = max(0, self.status_timer - dt)

    def status(self, msg):
        self.status_msg = msg
        self.status_timer = 2.5

    # ------------------------------------------------------------------
    def save_current(self, path="mapa.se", title="Meu Jogo"):
        world = World()
        world.tilemap = self.tilemap.copy()
        fmt = SEFormat()
        fmt.save(world, path, title=title)
        self.status(f"Salvo em {path}")

    def load_current(self, path):
        fmt = SEFormat()
        world = fmt.load(path)
        self.tilemap = world.tilemap
        self.status(f"Carregado {path}")
