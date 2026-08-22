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

TOOL_BRUSH, TOOL_ERASER, TOOL_FILL, TOOL_ENTITY = \
    "brush", "eraser", "fill", "entity"

# tipos de entidades arrastáveis no editor
ENTITY_TYPES = {
    "player": (60, 150, 255),   # P
    "enemy": (200, 60, 60),     # E
    "coin": (255, 215, 0),      # C
}


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
        # dica de drag & drop
        hint = font.render("arraste um tile para o mapa", True,
                           (180, 180, 200))
        surface.blit(hint, (x0, y0 + ((len(self.ids) + cols - 1) // cols)
                            * (ts + 6) + 8))

    @property
    def area_rect(self):
        """Área da paleta (usada para detectar drag & drop)."""
        ts = self.tile_size
        cols = 3
        rows = (len(self.ids) + cols - 1) // cols
        return pygame.Rect(10, 40, cols * (ts + 6) - 6,
                           rows * (ts + 6))

    def tile_at(self, mx, my, x0, y0) -> int:
        """Qual tile está sob o cursor (para drag)."""
        return self.hit(mx, my, x0, y0)

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
    """Editor de tile maps com PINCEL e DRAG & DROP.

    Drag & drop: arraste um tile da paleta (ou uma entidade do painel)
    até o mapa para pintá-lo/criá-lo. Segure o botão e mova para
    desenhar um traço. Botão direito arrasta = borracha.
    Undo/redo: Ctrl+Z / Ctrl+Y.
    """

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

        # --- drag & drop ---
        self.drag_active = False
        self.drag_source = None     # ("tile", tid) ou ("entity", kind)
        self.drag_ghost_pos = None  # posição do fantasma na tela

        # --- undo / redo (pilha de snapshots) ---
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 30
        self.status_msg = "Editor SlicEngine — B=pincel, E=borracha, "+ \
                          "+/-=tamanho, L=camada, Ctrl+S=salvar, T=testar"
        self.status_timer = 0.0
        self.palette = TilePalette(self.tile_size)

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

        # miniaturas dos tiles da paleta (para o fantasma de drag)
        self._thumb_cache = {}

        # painel de entidades (drag & drop de player/inimigo/moeda)
        self.entity_panel_open = True
        self._entity_thumbs = {}

    # ------------------------------------------------------------------
    def _world_pos(self, mx, my) -> tuple:
        sx = (mx + self.camera.x) // self.tile_size
        sy = (my + self.camera.y) // self.tile_size
        return int(sx), int(sy)

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def _snapshot(self):
        return self.tilemap.copy()

    def snapshot(self):
        """Registra estado atual para undo (chamado antes de cada edição)."""
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            self.status("Nada para desfazer")
            return
        self._redo_stack.append(self._snapshot())
        self.tilemap = self._undo_stack.pop()
        self.status("Desfeito")

    def redo(self):
        if not self._redo_stack:
            self.status("Nada para refazer")
            return
        self._undo_stack.append(self._snapshot())
        self.tilemap = self._redo_stack.pop()
        self.status("Refeito")

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------
    def _drag_thumb(self, tid):
        if tid in self._thumb_cache:
            return self._thumb_cache[tid]
        ts = self.tile_size
        th = pygame.Surface((ts, ts))
        if self.tile_sprites.get(tid) is not None:
            th.blit(self.tile_sprites[tid], (0, 0))
        else:
            th.fill(TILE_COLORS.get(tid, (128, 128, 128)))
        pygame.draw.rect(th, (255, 220, 60), (0, 0, ts, ts), 2)
        self._thumb_cache[tid] = th
        return th

    def _start_drag(self, mx, my):
        """Inicia drag a partir da paleta (tile) ou painel de entidades."""
        ts = self.tile_size
        cols = 3
        # paleta de tiles
        for i, tid in enumerate(self.palette.ids):
            px = 10 + (i % cols) * (ts + 6)
            py = 40 + (i // cols) * (ts + 6)
            if pygame.Rect(px, py, ts, ts).collidepoint(mx, my):
                self.drag_active = True
                self.drag_source = ("tile", tid)
                self.drag_ghost_pos = (mx, my)
                self.status(f"Arrastando tile {tid}")
                return True
        # painel de entidades
        if self.entity_panel_open:
            ey0 = self.engine.screen.get_height() - 56
            for i, kind in enumerate(ENTITY_TYPES):
                ex = 10 + i * 40
                if pygame.Rect(ex, ey0, 34, 34).collidepoint(mx, my):
                    self.drag_active = True
                    self.drag_source = ("entity", kind)
                    self.drag_ghost_pos = (mx, my)
                    self.status(f"Arrastando entidade {kind}")
                    return True
        return False

    def _end_drag(self, mx, my):
        """Solta o drag no mapa (ou descarta fora dele)."""
        self.drag_active = False
        gx, gy = self._world_pos(mx, my)
        tw = self.tilemap.width
        th_ = self.tilemap.height
        on_map = (0 <= gx < tw and 0 <= gy < th_
                  and mx > 140)  # longe da paleta
        if on_map and self.drag_source:
            self.snapshot()
            kind, what = self.drag_source
            if kind == "tile":
                if what == 0:
                    self.tool = TOOL_ERASER
                else:
                    self.tool = TOOL_BRUSH
                    self.palette.selected = what
                self.tool_size = 1
                self._paint(gx, gy)
                self.status(f"Tile {what} pintado via drag & drop")
            elif kind == "entity":
                self.world.add_entity(what, gx + 0.5, gy + 0.5)
                self.status(f"Entidade {what} criada via drag & drop")
        self.drag_source = None
        self.drag_ghost_pos = None

    def _paint(self, x, y, key=None):
        """Pinta célula (pincel, borracha ou preenchimento)."""
        if key is not None and key != (x, y):
            return  # célula já pintada (evita redundância)
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
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self.redo()
                else:
                    self.undo()
            elif event.key == pygame.K_y and (pygame.key.get_mods()
                                              & pygame.KMOD_CTRL):
                self.redo()
            elif event.key in (pygame.K_r,):
                self.status("Desfazer: Ctrl+Z / Refazer: Ctrl+Shift+Z ou "
                            "Ctrl+Y")
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # arrastar tile da paleta ou entidade do painel?
                if self._start_drag(event.pos[0], event.pos[1]):
                    return
                # clique simples na paleta = selecionar tile
                tid = self.palette.tile_at(event.pos[0], event.pos[1],
                                           10, 40)
                if tid >= 0:
                    self.palette.selected = tid
                    self.tool = TOOL_BRUSH if tid > 0 else TOOL_ERASER
                    return
                self.brushing = True
                self.last_brush = None
                self._brush(event.pos[0], event.pos[1])
            elif event.button == 3:
                # botão direito = borracha
                self.brushing = True
                self.tool = TOOL_ERASER
                self.last_brush = None
                self._brush(event.pos[0], event.pos[1])
        elif event.type == pygame.MOUSEMOTION and self.drag_active:
            self.drag_ghost_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (1, 3):
                if self.drag_active:
                    self._end_drag(event.pos[0], event.pos[1])
                else:
                    self.brushing = False
                    self.last_brush = None
        elif event.type == pygame.MOUSEMOTION and self.brushing:
            self._brush(event.pos[0], event.pos[1])

    def _brush(self, mx, my):
        x, y = self._world_pos(mx, my)
        # se começou a pintar agora, tira snapshot
        if self.last_brush is None:
            self.snapshot()
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
        # grade do cursor do pincel (apenas se não estiver arrastando)
        if not self.drag_active:
            mx, my = pygame.mouse.get_pos()
            gx, gy = self._world_pos(mx, my)
            r = self.tool_size // 2
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    rect = pygame.Rect((gx + dx) * ts - cam_x,
                                       (gy + dy) * ts - cam_y, ts, ts)
                    pygame.draw.rect(surface, (255, 220, 60), rect, 2)

        # --- fantasma do drag & drop ---
        if self.drag_active and self.drag_ghost_pos:
            dx, dy = self.drag_ghost_pos
            if self.drag_source and self.drag_source[0] == "tile":
                th_ = self._drag_thumb(self.drag_source[1])
                surface.blit(th_, (dx - ts // 2, dy - ts // 2))
            elif self.drag_source and self.drag_source[0] == "entity":
                col = ENTITY_TYPES[self.drag_source[1]]
                pygame.draw.circle(surface, col, (dx, dy), 14)
                pygame.draw.circle(surface, (255, 255, 255), (dx, dy),
                                   14, 2)

        # --- painel de entidades (drag & drop) ---
        self._draw_entity_panel(surface)
        # HUD
        font = pygame.font.SysFont("dejavusans", 14, bold=True)
        tool_name = {"brush": "Pincel", "eraser": "Borracha",
                     "fill": "Balde"}[self.tool]
        hud = (f"Editor | {tool_name} (tam {self.tool_size}) | camada "
               f"{self.tilemap.active_layer} | {self.tilemap.width}x"
               f"{self.tilemap.height} | Ctrl+S salvar | T testar")
        t = font.render(hud, True, (230, 230, 230))
        surface.blit(t, (10, 8))
        self.palette.draw(surface, 10, 40)
        if self.status_timer > 0:
            st = font.render(self.status_msg, True, (255, 240, 150))
            surface.blit(st, (10, surface.get_height() - 24))

    # ------------------------------------------------------------------
    def _draw_entity_panel(self, surface: pygame.Surface):
        """Painel inferior de entidades arrastáveis (player/inimigo/moeda)."""
        ts = self.tile_size
        ew, eh = 40, 34
        y0 = surface.get_height() - eh - 6
        bg = pygame.Surface((10 + len(ENTITY_TYPES) * 40 + 6, eh + 8),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, (6, y0 - 2))
        label = pygame.font.SysFont("dejavusans", 12, bold=True).render(
            "ENTIDADES (arraste):", True, (230, 230, 230))
        surface.blit(label, (6, y0 - 16))
        for i, (kind, col) in enumerate(ENTITY_TYPES.items()):
            x = 10 + i * 40
            rect = pygame.Rect(x, y0, 34, 34)
            pygame.draw.circle(surface, col, rect.center, 13)
            pygame.draw.circle(surface, (255, 255, 255), rect.center,
                               13, 2)
            lbl = pygame.font.SysFont("dejavusans", 10).render(
                kind, True, (255, 255, 255))
            surface.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                               y0 + 36))

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
        loaded = fmt.load(path)
        world = loaded[0] if isinstance(loaded, tuple) else loaded
        self.tilemap = world.tilemap
        if hasattr(world, "entities"):
            self.world.entities = world.entities
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.status(f"Carregado {path}")
