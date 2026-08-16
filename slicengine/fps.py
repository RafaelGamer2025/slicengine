"""
SlicEngine — Modo FPS 3D completo estilo Doom.

Adiciona ao Raycaster:
- Inimigos interativos (perseguem o jogador, causam dano, têm vida)
- Sistema de tiro (raio do centro da tela, hit detection, dano por bala)
- HUD (vida, munição, inimigos restantes, mira, efeito de dano e flash)
- Estados de jogo (jogando, game over, vitória)
"""
import math
import random
import pygame

from .world import Entity


class Enemy(Entity):
    """Inimigo do FPS: persegue o jogador e ataca quando perto."""

    def __init__(self, x=0.0, y=0.0):
        super().__init__("enemy", x, y)
        self.hp = 3              # pontos de vida
        self.max_hp = 3
        self.speed = 1.2         # tiles/segundo
        self.damage = 10         # dano por ataque
        self.attack_range = 0.9  # distância de ataque
        self.attack_cooldown = 1.2
        self.flash = 0.0         # timer de flash vermelho (dano recebido)
        self.stun = 0.0          # timer de atordoamento (levou tiro)
        self.alive = True

    # ------------------------------------------------------------------
    def update(self, dt, map_grid, player_x, player_y, game):
        """IA simples: vai em direção ao jogador (burlando paredes)."""
        if not self.alive:
            return
        self.flash = max(0.0, self.flash - dt)
        self.stun = max(0.0, self.stun - dt)
        if self.stun > 0:
            return

        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)

        if dist > self.attack_range:
            # mover na direção do jogador com colisão simples
            if dist > 0:
                vx, vy = dx / dist, dy / dist
            nx = self.x + vx * self.speed * dt
            ny = self.y + vy * self.speed * dt
            mh = 0.25
            ix = int(nx + (mh if vx > 0 else -mh))
            iy = int(ny + (mh if vy > 0 else -mh))
            mh_rows = len(map_grid)
            mh_cols = len(map_grid[0])
            if 0 <= ix < mh_cols and 0 <= int(self.y) < mh_rows \
                    and not map_grid[int(self.y)][ix]:
                self.x = nx
            if 0 <= iy < mh_rows and 0 <= int(self.x) < mh_cols \
                    and not map_grid[iy][int(self.x)]:
                self.y = ny
        else:
            # atacar
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                game.take_damage(self.damage)
                self.attack_cooldown = self.attack_range + 0.6

    def hit(self, amount=1):
        """Leva dano de tiro."""
        self.hp -= amount
        self.flash = 0.25
        self.stun = 0.3
        if self.hp <= 0:
            self.alive = False


class FPSGame:
    """Camada de jogo FPS completa sobre o Raycaster."""

    def __init__(self, engine, player_sprite=None, enemy_sprite=None,
                 gun_sprite=None, wall_hit_sprite=None):
        self.engine = engine
        self.rc = engine.raycaster
        self.player_hp = 100
        self.ammo = 50
        self.kills = 0
        self.state = "playing"      # playing, gameover, win
        self.damage_flash = 0.0     # tela vermelha ao tomar dano
        self.muzzle_flash = 0.0     # flash da arma ao atirar
        self.hit_marker = 0.0       # X de acerto na mira
        self.gun_kick = 0.0         # recuo visual da arma
        self._player_sprite = player_sprite or pygame.Surface((16, 16))
        self._enemy_sprite = enemy_sprite or pygame.Surface((16, 16))
        self._gun_sprite = gun_sprite
        self._wall_hit_sprite = wall_hit_sprite

    # ------------------------------------------------------------------
    def enemies(self):
        return [e for e in self.engine.world.entities
                if e.kind == "enemy" and isinstance(e, Enemy) and e.alive]

    # ------------------------------------------------------------------
    def update(self, dt):
        """Atualiza IA dos inimigos e timers de efeitos."""
        if self.state != "playing":
            return
        self.damage_flash = max(0.0, self.damage_flash - dt)
        self.muzzle_flash = max(0.0, self.muzzle_flash - dt * 6)
        self.hit_marker = max(0.0, self.hit_marker - dt * 3)
        self.gun_kick = max(0.0, self.gun_kick - dt * 5)
        m = self.rc.map
        for e in self.enemies():
            e.update(dt, m, self.rc.x, self.rc.y, self)
        if not self.enemies():
            self.state = "win"
            self.engine.disparar("vitoria")
        if self.player_hp <= 0:
            self.state = "gameover"
            self.engine.disparar("morte")

    # ------------------------------------------------------------------
    def take_damage(self, amount):
        self.player_hp = max(0, self.player_hp - amount)
        self.damage_flash = 0.35
        try:
            self.engine._api_tocar_som("sounds/dano.wav")
        except Exception:
            pass
        self.engine.disparar("dano", {"amount": amount})

    # ------------------------------------------------------------------
    def shoot(self):
        """Dispara: raio do centro da tela, atinge o inimigo mais próximo
        na mira (e no campo de visão), gasta 1 munição."""
        if self.state != "playing":
            return False
        if self.ammo <= 0:
            return False
        self.ammo -= 1
        self.muzzle_flash = 1.0
        self.gun_kick = 1.0
        try:
            self.engine._api_tocar_som("sounds/tiro.wav")
        except Exception:
            pass

        # varredura de inimigos: o mais próximo no cone da mira
        targets = []
        for e in self.enemies():
            d = math.hypot(e.x - self.rc.x, e.y - self.rc.y)
            if d > 20:
                continue
            ang = math.atan2(e.y - self.rc.y, e.x - self.rc.x)
            diff = math.atan2(math.sin(ang - self.rc.angle),
                              math.cos(ang - self.rc.angle))
            half = math.atan2(0.45, d)   # largura aparente do sprite
            if abs(diff) <= half + 0.08:
                targets.append((d, e))
        targets.sort(key=lambda t: t[0])

        hit = False
        for d, e in targets:
            # verificar parede entre jogador e alvo (raio DDA até d)
            if not self._wall_between(d):
                alive_before = e.alive
                e.hit(1)
                self.hit_marker = 1.0
                hit = True
                if alive_before and not e.alive:
                    self.kills += 1
                    self.engine.disparar("inimigo_morto", {"enemy": e})
                self.engine.disparar("tiro")
                break
        if not hit:
            self.engine.disparar("tiro", {"hit": False})
        return hit

    def _wall_between(self, max_dist):
        """Reusa o DDA do Raycaster (cast): se a parede mais próxima na
        mira estiver a menos de max_dist, bloqueia o tiro."""
        dist, tile, _side, _u = self.rc.cast(self.rc.x, self.rc.y,
                                             self.rc.angle)
        return dist <= max_dist

    # ------------------------------------------------------------------
    def respawn_enemies(self, positions):
        """Recria inimigos nas posições dadas (para reinício)."""
        self.engine.world.entities = [
            e for e in self.engine.world.entities if e.kind != "enemy"]
        for x, y in positions:
            self.engine.world.entities.append(Enemy(x, y))

    # ------------------------------------------------------------------
    def render_hud(self, surface):
        """Desenha HUD estilo Doom: barra inferior, vida, munição, kills,
        mira, flashes e arma."""
        w, h = surface.get_size()
        font = pygame.font.SysFont("dejavusansmono", 26, bold=True)
        font_big = pygame.font.SysFont("dejavusansmono", 40, bold=True)

        # --- barra inferior ---
        bar = pygame.Surface((w, 48))
        bar.fill((60, 55, 50))
        pygame.draw.rect(bar, (110, 100, 90), (0, 0, w, 48), 2)
        surface.blit(bar, (0, h - 48))

        # --- vida ---
        hp_color = (200, 50, 50) if self.player_hp < 35 else (60, 200, 60)
        pygame.draw.rect(surface, (30, 30, 30), (16, h - 40, 160, 24))
        pygame.draw.rect(surface, hp_color, (16, h - 40,
                         max(0, int(160 * self.player_hp / 100)), 24))
        lbl = font.render(f"VIDA {self.player_hp}", True, (255, 255, 255))
        surface.blit(lbl, (18, h - 37))

        # --- munição (lado esquerdo, ao lado da vida) ---
        ammo = font.render(f"MUNICAO {self.ammo}", True,
                           (255, 220, 120))
        surface.blit(ammo, (190, h - 37))

        # --- kills / inimigos (lado direito) ---
        alive = len(self.enemies())
        kills = font.render(f"ELIMINADOS {self.kills}  RESTANTES {alive}",
                            True, (255, 255, 255))
        surface.blit(kills, (w - kills.get_width() - 16, h - 37))

        # --- mira ---
        cx, cy = w // 2, (h - 48) // 2 + 20
        pygame.draw.line(surface, (255, 255, 255), (cx - 10, cy),
                         (cx - 4, cy), 2)
        pygame.draw.line(surface, (255, 255, 255), (cx + 4, cy),
                         (cx + 10, cy), 2)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy - 10),
                         (cx, cy - 4), 2)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy + 4),
                         (cx, cy + 10), 2)
        if self.hit_marker > 0:
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                pygame.draw.line(surface, (255, 60, 60),
                                 (cx + dx * 5, cy + dy * 5),
                                 (cx + dx * 12, cy + dy * 12), 2)

        # --- arma ---
        if self._gun_sprite:
            gw, gh = self._gun_sprite.get_size()
            ox = (w - gw) // 2 + int(self.gun_kick * 14)
            oy = (h - 48) - gh + int(self.gun_kick * 10)
            surface.blit(self._gun_sprite, (ox, oy))
            if self.muzzle_flash > 0:
                flash = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.circle(flash,
                                   (255, 220, 100, int(220 *
                                    self.muzzle_flash)), (32, 32), 28)
                surface.blit(flash, (ox + gw // 2 - 32, oy - 40))

        # --- flashes ---
        if self.damage_flash > 0:
            red = pygame.Surface((w, h), pygame.SRCALPHA)
            red.fill((255, 0, 0, int(90 * self.damage_flash)))
            surface.blit(red, (0, 0))

        # --- overlays de estado ---
        if self.state == "gameover":
            self._overlay(surface, "GAME OVER",
                          "Pressione R para reiniciar", (220, 40, 40))
        elif self.state == "win":
            self._overlay(surface, "VITORIA!",
                          "Pressione R para jogar de novo", (60, 220, 60))

    def _overlay(self, surface, title, sub, color):
        w, h = surface.get_size()
        dark = pygame.Surface((w, h), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 150))
        surface.blit(dark, (0, 0))
        font = pygame.font.SysFont("dejavusans", 64, bold=True)
        small = pygame.font.SysFont("dejavusans", 28)
        t = font.render(title, True, color)
        s = small.render(sub, True, (255, 255, 255))
        surface.blit(t, (w // 2 - t.get_width() // 2, h // 2 - 90))
        surface.blit(s, (w // 2 - s.get_width() // 2, h // 2 - 20))

    # ------------------------------------------------------------------
    def handle_event(self, event):
        """Trata eventos de teclado/mouse do FPS."""
        if self.state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN \
                    and event.button == 1:
                return self.shoot()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                return self.shoot()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r \
                and self.state in ("gameover", "win"):
            self.restart()
        return False

    def restart(self):
        """Reinicia o jogo mantendo o mapa."""
        self.player_hp = 100
        self.ammo = 50
        self.kills = 0
        self.state = "playing"
        m = self.rc.map
        pos = [(e.x, e.y) for e in self.engine.world.entities
               if e.kind == "enemy"]
        if not pos:
            # posições padrão espalhadas pelo mapa
            pos = [(4.5, 4.5), (8.5, 2.5), (12.5, 7.5), (3.5, 9.5),
                   (14.5, 3.5)]
        self.respawn_enemies(pos)
        p = next((e for e in self.engine.world.entities
                  if e.kind == "player"), None)
        if p:
            self.rc.x, self.rc.y = p.x, p.y
        self.engine.disparar("reiniciar")
