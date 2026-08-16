"""
SlicEngine — Modo de plataforma 2D real.

Diferente do modo "2D com tile maps" (slicengine.world + editor,
visão de cima), este módulo é um jogo de plataforma lateral com:

- Física: gravidade, pulo, colisão AABB com tiles sólidos
- Câmera lateral que segue o jogador (scrolling)
- Inimigos 2D que patrulham e matam o jogador ao toque
- Moedas coletáveis e bandeira de chegada (vitória)
- HUD: vida, moedas, mensagem de vitória/morte

Uso rápido::

    platform = PlatformGame(engine, player_sprite, ...)
    platform.build(map_ascii, tile_sprites)   # monta o mundo do ASCII
    platform.update(dt); platform.render(surface)
"""
import pygame

from .world import Entity


# símbolos do mapa ASCII
SOLID = "#"          # chão/plataforma sólida
LAVA = "L"           # perigo: mata o jogador
COIN = "C"           # moeda
ENEMY = "E"          # inimigo patrulhador
GOAL = "G"           # bandeira de chegada


class PlatformPlayer(Entity):
    """Jogador do jogo de plataforma."""

    def __init__(self, x=0.0, y=0.0):
        super().__init__("player", x, y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1            # 1 = direita, -1 = esquerda
        self.hp = 3
        self.invincible = 0.0      # tempo de invencibilidade após dano

    def jump(self, jump_speed=-5.2):
        if self.on_ground:
            self.vy = jump_speed
            self.on_ground = False
            return True
        return False


class PlatformEnemy(Entity):
    """Inimigo 2D que patrulha uma plataforma de um lado ao outro."""

    def __init__(self, x=0.0, y=0.0):
        super().__init__("enemy", x, y)
        self.vx = -1.0
        self.alive = True
        self.flash = 0.0

    def update(self, dt, tiles_w, tiles_h, is_solid):
        if not self.alive:
            return
        self.flash = max(0.0, self.flash - dt)
        nx = self.x + self.vx * dt
        # inverte a direção ao bater em parede ou borda
        tile_x = int(nx + (0.3 if self.vx > 0 else -0.3))
        if 0 <= tile_x < tiles_w and is_solid(tile_x, int(self.y)) \
                or not (0 <= tile_x < tiles_w):
            self.vx *= -1
        else:
            self.x = nx


class PlatformGame:
    """Jogo de plataforma 2D real construído a partir de um mapa ASCII."""

    GRAVITY = 14.0
    SPEED = 3.2

    def __init__(self, engine, player_sprite=None, enemy_sprite=None,
                 coin_sprite=None):
        self.engine = engine
        self.w, self.h = engine.screen.get_size()
        self.tiles = []          # lista de linhas de caracteres
        self.tile_size = 32
        self._player = None
        self.coins = []          # [(x, y, collected)]
        self.enemies = []        # PlatformEnemy
        self.score = 0
        self.state = "playing"   # playing, dead, won
        self.camera_x = 0.0
        self._player_sprite = player_sprite
        self._enemy_sprite = enemy_sprite
        self._coin_sprite = coin_sprite
        self._goal = None        # (tx, ty) da bandeira
        self._status_timer = 0.0

    # ------------------------------------------------------------------
    def build(self, ascii_map):
        """Monta o mundo a partir do ASCII: linhas de cima p/ baixo."""
        self.tiles = [list(line) for line in ascii_map.strip().splitlines()]
        rows = len(self.tiles)
        cols = max(len(r) for r in self.tiles)
        # entidades do mapa
        self.coins = []
        self.enemies = []
        self._goal = None
        for ty, row in enumerate(self.tiles):
            for tx, ch in enumerate(row):
                if ch == COIN:
                    self.coins.append([float(tx) + 0.5, float(ty) + 0.5,
                                       False])
                elif ch == ENEMY:
                    self.enemies.append(
                        PlatformEnemy(float(tx) + 0.5, float(ty) + 0.5))
                elif ch == GOAL:
                    self._goal = (tx, ty)
        self.engine.world.entities = [
            e for e in self.engine.world.entities if e.kind != "player"]
        # achar spawn do player (P) ou usar (1.5, 1.5)
        px = py = 1.5
        for ty, row in enumerate(self.tiles):
            for tx, ch in enumerate(row):
                if ch == "P":
                    px, py = float(tx) + 0.5, float(ty) - 0.2
        self._player = PlatformPlayer(px, py)
        self.engine.world.entities.insert(0, self._player)
        for e in self.enemies:
            self.engine.world.entities.append(e)
        self.world_w = cols
        self.world_h = rows

    # ------------------------------------------------------------------
    def is_solid(self, tx, ty):
        if 0 <= ty < len(self.tiles) and 0 <= tx < len(self.tiles[ty]):
            return self.tiles[ty][tx] == SOLID
        return False

    # ------------------------------------------------------------------
    def update(self, dt, keys):
        if self.state != "playing":
            return
        p = self._player
        # movimento horizontal
        p.vx = 0.0
        if keys.get(pygame.K_LEFT) or keys.get(pygame.K_a):
            p.vx = -self.SPEED
            p.facing = -1
        if keys.get(pygame.K_RIGHT) or keys.get(pygame.K_d):
            p.vx = self.SPEED
            p.facing = 1

        # gravidade + pulo
        p.vy += self.GRAVITY * dt
        if keys.get(pygame.K_SPACE) or keys.get(pygame.K_UP) or \
                keys.get(pygame.K_w):
            if p.jump():
                try:
                    self.engine._api_tocar_som("sounds/pulo.wav")
                except Exception:
                    pass
        p.on_ground = False

        # mover com colisão tile a tile
        self._move(p, p.vx * dt, 0.0)
        self._move(p, 0.0, p.vy * dt)

        # atualizar inimigos
        for e in self.enemies:
            e.update(dt, self.world_w, self.world_h, self.is_solid)

        # colisão com inimigos
        if p.invincible > 0:
            p.invincible -= dt
        for e in self.enemies:
            if not e.alive:
                continue
            if abs(e.x - p.x) < 0.5 and abs(e.y - p.y) < 0.6:
                if p.vy > 0 and p.y < e.y:
                    # pisou no inimigo (mata com pulo)
                    e.alive = False
                    e.flash = 0.0
                    p.vy = -4.5
                    self.engine.disparar("inimigo_pisado", {"enemy": e})
                elif p.invincible <= 0:
                    p.hp -= 1
                    p.invincible = 1.0
                    try:
                        self.engine._api_tocar_som("sounds/dano.wav")
                    except Exception:
                        pass
                    self.engine.disparar("dano")
                    if p.hp <= 0:
                        self.state = "dead"
                        self.engine.disparar("morte")

        # moedas
        for c in self.coins:
            if c[2]:
                continue
            if abs(c[0] - p.x) < 0.45 and abs(c[1] - p.y) < 0.45:
                c[2] = True
                self.score += 1
                try:
                    self.engine._api_tocar_som("sounds/moeda.wav")
                except Exception:
                    pass
                self.engine.disparar("moeda_pegada")

        # lava e queda do mundo
        tx, ty = int(p.x), int(p.y)
        if self._cell(tx, ty) == LAVA or ty >= self.world_h:
            self.state = "dead"
            self.engine.disparar("morte")

        # bandeira de chegada
        if self._goal and abs(p.x - (self._goal[0] + 0.5)) < 0.5 \
                and abs(p.y - (self._goal[1] + 0.5)) < 0.7:
            self.state = "won"
            self.engine.disparar("vitoria")

        # câmera lateral segue o jogador
        target = p.x * self.tile_size - self.w / 2
        target = max(0, min(target,
                            self.world_w * self.tile_size - self.w))
        self.camera_x += (target - self.camera_x) * min(1.0, dt * 8)

    def _cell(self, tx, ty):
        if 0 <= ty < len(self.tiles) and 0 <= tx < len(self.tiles[ty]):
            return self.tiles[ty][tx]
        return "."

    def _move(self, p, dx, dy):
        """Move o jogador (dx, dy) com colisão AABB contra tiles sólidos."""
        p.x += dx
        if dx != 0:
            side = 0.42
            for check_y in (p.y - 0.4, p.y + 0.4, p.y):
                tx = int(p.x + (side if dx > 0 else -side))
                ty = int(check_y)
                if self.is_solid(tx, ty):
                    p.x = (tx - side) if dx > 0 else (tx + 1 + side)
                    break
        p.y += dy
        if dy != 0:
            side = 0.42
            for check_x in (p.x - 0.3, p.x + 0.3):
                tx = int(check_x)
                ty = int(p.y + (side if dy > 0 else -side))
                if self.is_solid(tx, ty):
                    if dy > 0:
                        p.y = ty - side
                        p.on_ground = True
                        p.vy = 0.0
                    else:
                        p.y = ty + 1 + side
                        p.vy = 0.0
                    break
        # limites do mundo
        p.x = max(0.5, min(p.x, self.world_w - 0.5))

    # ------------------------------------------------------------------
    def render(self, surface, tile_sprites=None):
        """Desenha o jogo: tiles, moedas, inimigos, jogador, câmera e HUD.

        ``tile_sprites``: dict {caractere: pygame.Surface} para os tiles."""
        tile_sprites = tile_sprites or {}
        cam = self.camera_x
        ts = self.tile_size

        for ty, row in enumerate(self.tiles):
            for tx, ch in enumerate(row):
                sx = int(tx * ts - cam)
                sy = int(ty * ts)
                if sx < -ts or sx > self.w:
                    continue
                sprite = tile_sprites.get(ch)
                if sprite is None and ch == SOLID:
                    pygame.draw.rect(surface, (90, 140, 70),
                                     (sx, sy, ts, ts))
                elif sprite is None and ch == LAVA:
                    pygame.draw.rect(surface, (200, 60, 30),
                                     (sx, sy, ts, ts))
                elif sprite is None and ch == GOAL:
                    pygame.draw.rect(surface, (255, 220, 60),
                                     (sx, sy, ts, ts))
                elif sprite is not None:
                    surface.blit(sprite, (sx, sy))
                else:
                    # céu/fundo padrão
                    if ch == ".":
                        pass
                    else:
                        pygame.draw.rect(surface, (70, 70, 90),
                                         (sx, sy, ts, ts))

        # moedas
        for c in self.coins:
            if c[2]:
                continue
            sx = int(c[0] * ts - cam)
            sy = int(c[1] * ts)
            if -32 <= sx <= self.w + 32:
                if self._coin_sprite is not None:
                    surface.blit(self._coin_sprite, (sx - 16, sy - 16))
                else:
                    pygame.draw.circle(surface, (255, 220, 60),
                                       (sx, sy), 8)

        # inimigos
        for e in self.enemies:
            if not e.alive:
                continue
            sx = int(e.x * ts - cam)
            sy = int(e.y * ts)
            if self._enemy_sprite is not None:
                s = pygame.transform.flip(self._enemy_sprite,
                                          e.vx > 0, False)
                surface.blit(s, (sx - 28, sy - 28))
            else:
                pygame.draw.rect(surface, (180, 40, 40),
                                 (sx - 14, sy - 14, 28, 28))

        # jogador
        p = self._player
        px = int(p.x * ts - cam)
        py = int(p.y * ts)
        if p.invincible > 0 and int(p.invincible * 10) % 2 == 0:
            pass  # pisca durante invencibilidade
        elif self._player_sprite is not None:
            s = pygame.transform.flip(self._player_sprite,
                                      p.facing < 0, False)
            surface.blit(s, (px - 24, py - 24))
        else:
            pygame.draw.circle(surface, (60, 120, 255), (px, py), 14)

        # HUD
        font = pygame.font.SysFont("dejavusansmono", 24, bold=True)
        lbl = font.render(f"VIDA {p.hp}   MOEDAS {self.score}", True,
                          (255, 255, 255))
        surface.blit(lbl, (10, 10))

        if self.state == "won":
            self._banner(surface, "VITORIA!", (60, 220, 60))
        elif self.state == "dead":
            self._banner(surface, "GAME OVER", (220, 40, 40))

    def _banner(self, surface, text, color):
        font = pygame.font.SysFont("dejavusans", 48, bold=True)
        sub = pygame.font.SysFont("dejavusans", 22)
        t = font.render(text, True, color)
        s = sub.render("Pressione R para reiniciar", True, (255, 255, 255))
        surface.blit(t, (self.w // 2 - t.get_width() // 2,
                         self.h // 2 - 40))
        surface.blit(s, (self.w // 2 - s.get_width() // 2,
                         self.h // 2 + 20))

    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r \
                and self.state in ("won", "dead"):
            self.restart()

    def restart(self):
        self.build("\n".join("".join(r) for r in self.tiles))
        self.score = 0
        self.state = "playing"
        self.camera_x = 0.0
        self.engine.disparar("reiniciar")

    @property
    def player(self):
        return self._player
