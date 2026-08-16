"""
SlicEngine — Renderizador 3D raycasting estilo Doom (pseudopolígono 2.5D).

Implementa:
- DDA raycasting com texturização por colunas
- Sprites billboarding (entidades/inimigos)
- Shading por distância (fog)
- Chão e teto com gradiente simples
"""
import math
import pygame


class Raycaster:
    """Renderizador raycasting 2.5D. Renderiza um mapa de grade com paredes
    texturizadas e sprites em um surface Pygame."""

    def __init__(self, map_grid, texture_atlas: dict, width=800, height=480,
                 fov_deg=66.0):
        """
        map_grid: list[list[int]] — 0 = vazio, >0 = id do tile de parede
        texture_atlas: dict[int, pygame.Surface] — texturas por id de tile
        """
        self.map = map_grid
        self.map_h = len(map_grid)
        self.map_w = len(map_grid[0]) if map_grid else 0
        self.atlas = texture_atlas
        self.width = width
        self.height = height
        self.fov = math.radians(fov_deg)
        self.half_fov = self.fov / 2.0
        self.wall_cache = {}
        # estado do jogador
        self.x = 1.5
        self.y = 1.5
        self.angle = 0.0          # direção em radianos
        self.speed = 3.0
        self.rot_speed = 2.2
        self.floor_color = (40, 40, 48)
        self.ceiling_color = (16, 16, 24)

    @property
    def dir_x(self):
        return math.cos(self.angle)

    @property
    def dir_y(self):
        return math.sin(self.angle)

    # ------------------------------------------------------------------
    # Utilitários do DDA
    # ------------------------------------------------------------------
    def _get_tile(self, x: int, y: int) -> int:
        if 0 <= y < self.map_h and 0 <= x < self.map_w:
            return self.map[y][x]
        return 1  # borda = parede

    def cast(self, start_x, start_y, angle):
        """DDA: retorna (distância, tile_id, face, tex_u) de um raio."""
        ray_x = math.cos(angle)
        ray_y = math.sin(angle)
        x = int(start_x)
        y = int(start_y)
        delta_x = abs(1.0 / ray_x) if ray_x != 0 else 1e10
        delta_y = abs(1.0 / ray_y) if ray_y != 0 else 1e10
        step_x = 1 if ray_x >= 0 else -1
        step_y = 1 if ray_y >= 0 else -1
        side_x = (x + 1 - start_x) * delta_x if ray_x >= 0 else (start_x - x) * delta_x
        side_y = (y + 1 - start_y) * delta_y if ray_y >= 0 else (start_y - y) * delta_y

        hit = 0
        side = 0
        while hit == 0:
            if side_x < side_y:
                side_x += delta_x
                x += step_x
                side = 0
            else:
                side_y += delta_y
                y += step_y
                side = 1
            hit = self._get_tile(x, y)
            if hit:
                break
        if side == 0:
            dist = (side_x - delta_x)
            u = start_y + ray_y * dist
        else:
            dist = (side_y - delta_y)
            u = start_x + ray_x * dist
        u -= math.floor(u)
        # corrigir fisheye
        perp = dist * math.cos(angle - self.angle)
        return max(perp, 1e-4), hit, side, u

    # ------------------------------------------------------------------
    # Textura
    # ------------------------------------------------------------------
    def _tex_surface(self, tile_id):
        if tile_id in self.wall_cache:
            return self.wall_cache[tile_id]
        tex = self.atlas.get(tile_id)
        if tex is None:
            tex = pygame.Surface((64, 64))
            tex.fill((110, 110, 110))
        self.wall_cache[tile_id] = tex
        return tex

    def _tex_pixel(self, tile_id, u: float, v: float, shade: float):
        tex = self._tex_surface(tile_id)
        tw, th = tex.get_size()
        px = int(u * tw) % tw
        py = int(v * th) % th
        r, g, b, _a = tex.get_at((px, py))
        k = max(0.15, min(1.0, shade))
        return int(r * k), int(g * k), int(b * k)

    # ------------------------------------------------------------------
    # Z-buffer de sprites
    # ------------------------------------------------------------------
    def _sprite_dist(self, spr_x, spr_y):
        return math.hypot(spr_x - self.x, spr_y - self.y)

    def _sprite_screen(self, spr_x, spr_y):
        """Retorna (x_tela, dist) de um sprite no espaço da câmera.
        A rotação é em torno de -angle para alinhar o dir ao eixo +x."""
        dx = spr_x - self.x
        dy = spr_y - self.y
        cos_a, sin_a = math.cos(-self.angle), math.sin(-self.angle)
        tx = dx * cos_a - dy * sin_a
        ty = dx * sin_a + dy * cos_a
        if ty <= 0.1:
            return None, 0.0
        screen_x = int((self.width / 2) * (1 + tx / (ty * math.tan(self.half_fov))))
        return screen_x, ty

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface, sprites: list = None):
        """Renderiza cena completa. sprites: lista de dicts
        {x, y, surface}. Usa pixelarray para velocidade."""
        w, h = surface.get_size()
        buf = surface.convert()  # surface 32 bits sem alpha para pixels2d
        screen = pygame.surfarray.pixels2d(buf)
        half_h = h // 2

        # --- teto e chão (gradiente) ---
        import numpy as _np
        for y in range(0, half_h):
            c = tuple(int(c0 + (self.ceiling_color[i] - c0) * y / half_h)
                      for i, c0 in enumerate((8, 8, 14)))
            # pixels2d: inteiro nativo ARGB (A no byte alto)
            screen[:, y] = _np.array(
                (255 << 24) | (c[0] << 16) | (c[1] << 8) | c[2],
                dtype=_np.uint32)
        for y in range(half_h, h):
            t = (y - half_h) / (h - half_h)
            c = tuple(int(self.floor_color[i] * (0.55 + 0.45 * t)) for i in range(3))
            screen[:, y] = _np.array(
                (255 << 24) | (c[0] << 16) | (c[1] << 8) | c[2],
                dtype=_np.uint32)

        # --- z-buffer ---
        zbuf = [0.0] * w

        # --- paredes ---
        for x in range(w):
            cam = 2 * x / w - 1
            angle = self.angle + self.half_fov * cam
            dist, tile, side, u = self.cast(self.x, self.y, angle)
            zbuf[x] = dist
            wall_h = int(h / dist)
            draw_start = max(0, half_h - wall_h // 2)
            draw_end = min(h, half_h + wall_h // 2)
            fog = min(1.0, 2.5 / dist)
            if side:
                fog *= 0.75
            for y in range(draw_start, draw_end):
                v = (y - (half_h - wall_h // 2)) / wall_h
                col = self._tex_pixel(tile, u, v, fog)
                screen[x, y] = int(
                    (255 << 24) | (col[0] << 16) | (col[1] << 8) | col[2])
        del screen

        # de volta ao surface original (blit + flip implícito pelo chamador)
        surface.blit(buf, (0, 0))

        # --- sprites (billboard + z-test) ---
        if sprites:
            visible = []
            for s in sprites:
                sx, d = self._sprite_screen(s["x"], s["y"])
                if sx is not None and 0 < d < 40:
                    visible.append((sx, d, s))
            visible.sort(key=lambda t: -t[1])  # longe primeiro
            for sx, dist, spr in visible:
                img = spr["surface"]
                sw, sh = img.get_size()
                sprite_h = int(sh * h / dist / 64)
                sprite_w = int(sw * h / dist / 64)
                y0 = half_h - sprite_h // 2
                x0 = sx - sprite_w // 2
                for dx in range(sprite_w):
                    nx = x0 + dx
                    if 0 <= nx < w and dist < zbuf[nx]:
                        scale = sprite_h / sh
                        for dy in range(sprite_h):
                            ny = y0 + dy
                            if 0 <= ny < h:
                                r, g, b, a = img.get_at(
                                    (int(dx / scale), int(dy / scale)))
                                if a > 8:
                                    fog = min(1.0, 2.5 / dist)
                                    buf.set_at((nx, ny),
                                               (int(r * fog), int(g * fog),
                                                int(b * fog), a))

    # ------------------------------------------------------------------
    # Controles do jogador
    # ------------------------------------------------------------------
    def move(self, keys, dt):
        """Movimento WASD + rotação Q/E (ou setas)."""
        cs = math.cos(self.angle)
        sn = math.sin(self.angle)
        mx = my = 0.0
        if keys.get(pygame.K_w, False) or keys.get(pygame.K_UP, False):
            mx += cs; my += sn
        if keys.get(pygame.K_s, False) or keys.get(pygame.K_DOWN, False):
            mx -= cs; my -= sn
        if keys.get(pygame.K_a, False):
            mx += sn; my -= cs   # strafe esquerda
        if keys.get(pygame.K_d, False):
            mx -= sn; my += cs   # strafe direita
        if keys.get(pygame.K_q, False) or keys.get(pygame.K_LEFT, False):
            self.angle -= self.rot_speed * dt
        if keys.get(pygame.K_e, False) or keys.get(pygame.K_RIGHT, False):
            self.angle += self.rot_speed * dt
        if (mx, my) != (0.0, 0.0):
            L = math.hypot(mx, my)
            mx /= L; my /= L
            nx, ny = self.x + mx * self.speed * dt, self.y + my * self.speed * dt
            m = 0.2
            if not self._get_tile(int(nx + (m if mx > 0 else -m)), int(self.y)):
                self.x = nx
            if not self._get_tile(int(self.x), int(ny + (m if my > 0 else -m))):
                self.y = ny
