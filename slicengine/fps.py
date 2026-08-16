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


# ---------------- tipos de inimigos ----------------
# hp, velocidade (tiles/s), dano, alcance de ataque, cooldown, sprite
ENEMY_TYPES = {
    "melee":  {"hp": 3, "speed": 1.2, "damage": 10,
               "attack_range": 0.9, "cooldown": 1.2,
               "sprite": "enemy_fps.png", "label": "Zumbi"},
    "fast":   {"hp": 2, "speed": 2.6, "damage": 8,
               "attack_range": 0.9, "cooldown": 0.8,
               "sprite": "enemy_fast.png", "label": "Rápido"},
    "tank":   {"hp": 7, "speed": 0.7, "damage": 20,
               "attack_range": 1.0, "cooldown": 1.6,
               "sprite": "enemy_tank.png", "label": "Tanque"},
    "ranged": {"hp": 4, "speed": 0.9, "damage": 15,
               "attack_range": 7.0, "cooldown": 1.8,
               "sprite": "enemy_ranged.png", "label": "Arqueiro"},
}


class Enemy(Entity):
    """Inimigo do FPS: persegue o jogador e ataca quando perto.

    Aceita um tipo ("melee", "fast", "tank", "ranged") que define
    vida, velocidade, dano e alcance. O ranged ataca à distância
    se tiver linha de visão, senão se aproxima."""

    def __init__(self, x=0.0, y=0.0, kind="melee", label=None):
        super().__init__("enemy", x, y)
        spec = ENEMY_TYPES.get(kind, ENEMY_TYPES["melee"])
        self.enemy_kind = kind
        self.hp = spec["hp"]
        self.max_hp = spec["hp"]
        self.speed = spec["speed"]
        self.damage = spec["damage"]
        self.attack_range = spec["attack_range"]
        self.attack_cooldown = spec["cooldown"]
        self.flash = 0.0         # timer de flash vermelho (dano recebido)
        self.stun = 0.0          # timer de atordoamento (levou tiro)
        self.projectile = None   # projétil do ranged (dict ou None)
        self.label = label or spec["label"]
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

        # --- projétil do ranged ---
        if self.projectile is not None:
            p = self.projectile
            px = p["x"] + p["vx"] * 6.0 * dt
            py = p["y"] + p["vy"] * 6.0 * dt
            p["x"], p["y"] = px, py
            p["life"] -= dt
            if 0 <= int(py) < len(map_grid) and 0 <= int(px) < \
                    len(map_grid[0]) and map_grid[int(py)][int(px)]:
                p["life"] = 0                      # bateu na parede
            if p["life"] > 0 and math.hypot(px - player_x,
                                            py - player_y) < 0.4:
                game.take_damage(self.damage)
                self.projectile = None
                return
            if p["life"] <= 0:
                self.projectile = None

        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)

        # ranged atira à distância se tiver linha de visão
        line_of_sight = (self.enemy_kind == "ranged" and dist < 8.0
                         and not game._wall_between_to(self.x, self.y))

        if dist > self.attack_range and not line_of_sight:
            # mover na direção do jogador com colisão simples
            if dist > 0:
                vx, vy = dx / dist, dy / dist
            # fast desvia melhor: ajusta eixo dominante
            if self.enemy_kind == "fast":
                if abs(vx) >= abs(vy):
                    vy = 0
                else:
                    vx = 0
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
        elif line_of_sight and self.projectile is None:
            # disparar projétil na direção do jogador
            if dist > 0:
                vx, vy = dx / dist, dy / dist
            self.projectile = {"x": self.x, "y": self.y,
                               "vx": vx, "vy": vy, "life": 2.0}
        elif dist <= self.attack_range:
            # atacar de perto (melee/fast/tank)
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


# ---------------- tipos de coletáveis ----------------
# efeito aplicado ao pegar
COLLECTIBLES = {
    "medkit":     {"sprite": "medkit.png", "sound": "sounds/heal.wav",
                   "label": "+25 VIDA"},
    "power_ammo": {"sprite": "power_ammo.png", "sound": "sounds/powerup.wav",
                   "label": "+10 MUNICAO"},
    "power_speed": {"sprite": "power_speed.png", "sound": "sounds/powerup.wav",
                    "label": "VELOCIDADE x1.5 (5s)"},
    "power_damage": {"sprite": "power_damage.png",
                     "sound": "sounds/powerup.wav",
                     "label": "DANO x2 (5s)"},
    "power_health": {"sprite": "power_health.png",
                     "sound": "sounds/heal.wav",
                     "label": "+15 VIDA"},
}


class Collectible:
    """Item colecionável no chão do mapa (medkit ou power-up)."""

    def __init__(self, x=0.0, y=0.0, kind="medkit"):
        self.kind = kind
        self.x, self.y = x, y
        self.collected = False
        self.spec = COLLECTIBLES.get(kind, COLLECTIBLES["medkit"])
        self.bob = random.random() * math.pi * 2   # animação flutuante

    def sprite_name(self):
        return self.spec["sprite"]


class FPSGame:
    """Camada de jogo FPS completa sobre o Raycaster.

    Além do tiro e da IA, gerencia inimigos variados (melee, fast,
    tank, ranged) e itens colecionáveis (medkit, power-ups)."""

    def __init__(self, engine, player_sprite=None, enemy_sprite=None,
                 gun_sprite=None, wall_hit_sprite=None):
        self.engine = engine
        self.rc = engine.raycaster
        self.player_hp = 100
        self.max_hp = 100
        self.ammo = 50
        self.kills = 0
        self.picked = 0
        self.state = "playing"      # playing, gameover, win
        self.damage_flash = 0.0     # tela vermelha ao tomar dano
        self.muzzle_flash = 0.0     # flash da arma ao atirar
        self.hit_marker = 0.0       # X de acerto na mira
        self.gun_kick = 0.0         # recuo visual da arma
        # efeitos de power-up temporários
        self.speed_boost = 0.0      # multiplicador de movimento
        self.damage_boost = 0.0     # multiplicador de dano
        self.move_speed = 3.0       # base tiles/s
        self._player_sprite = player_sprite or pygame.Surface((16, 16))
        self._enemy_sprite = enemy_sprite or pygame.Surface((16, 16))
        self._gun_sprite = gun_sprite
        self._wall_hit_sprite = wall_hit_sprite
        self._collectibles = []     # lista de Collectible do jogo
        self._status_msg = None     # mensagem temporária (item pego)
        self._status_timer = 0.0

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
        self.speed_boost = max(0.0, self.speed_boost - dt)
        self.damage_boost = max(0.0, self.damage_boost - dt)
        self._status_timer = max(0.0, self._status_timer - dt)
        m = self.rc.map
        for e in self.enemies():
            e.update(dt, m, self.rc.x, self.rc.y, self)
        self._update_collectibles(dt)
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
                e.hit(self.effective_damage())
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

    def _wall_between_to(self, tx, ty):
        """Verifica se há parede entre o jogador e um ponto (tx, ty).
        Usa o raio do cast e a distância perpendicular."""
        dist, _tile, _side, _u = self.rc.cast(self.rc.x, self.rc.y,
                                              self.rc.angle)
        ang = math.atan2(ty - self.rc.y, tx - self.rc.x)
        d = math.hypot(tx - self.rc.x, ty - self.rc.y)
        diff = math.atan2(math.sin(ang - self.rc.angle),
                          math.cos(ang - self.rc.angle))
        # alvo na direção da mira (cone amplo) e parede mais perto que ele
        return abs(diff) < 0.4 and dist <= d

    # ------------------------------------------------------------------
    def respawn_enemies(self, positions):
        """Recria inimigos nas posições dadas (para reinício).

        ``positions`` aceita tuplas (x, y) — inimigo melee — ou
        (x, y, tipo) — ex.: (4.5, 4.5, "ranged")."""
        self.engine.world.entities = [
            e for e in self.engine.world.entities if e.kind != "enemy"]
        for pos in positions:
            if len(pos) == 3:
                self.engine.world.entities.append(
                    Enemy(pos[0], pos[1], kind=pos[2]))
            else:
                self.engine.world.entities.append(Enemy(pos[0], pos[1]))

    # ------------------------------------------------------------------
    # Itens colecionáveis
    # ------------------------------------------------------------------
    def spawn_collectible(self, x, y, kind="medkit"):
        """Cria um item colecionável no mapa."""
        self._collectibles.append(Collectible(x, y, kind))

    def spawn_collectibles(self, items):
        """Cria vários itens. ``items``: lista de (x, y) ou (x, y, kind)."""
        for it in items:
            if len(it) == 3:
                self.spawn_collectible(it[0], it[1], kind=it[2])
            else:
                self.spawn_collectible(it[0], it[1])

    def _update_collectibles(self, dt):
        """Anima e coleta itens próximos do jogador."""
        px, py = self.rc.x, self.rc.y
        for c in self._collectibles:
            if c.collected:
                continue
            c.bob += dt * 3.0
            d = math.hypot(c.x - px, c.y - py)
            if d < 0.5:
                c.collected = True
                self._collect(c)

    def _collect(self, c):
        """Aplica o efeito do item coletado."""
        sound = c.spec.get("sound")
        if sound:
            try:
                self.engine._api_tocar_som(sound)
            except Exception:
                pass
        if c.kind == "medkit":
            self.player_hp = min(self.max_hp, self.player_hp + 25)
        elif c.kind == "power_ammo":
            self.ammo += 10
        elif c.kind == "power_speed":
            self.speed_boost = 5.0
        elif c.kind == "power_damage":
            self.damage_boost = 5.0
        elif c.kind == "power_health":
            self.player_hp = min(self.max_hp, self.player_hp + 15)
        self.picked += 1
        self._status_msg = f"{c.spec['label']} PEGO!"
        self._status_timer = 1.5
        self.engine.disparar("item_coletado", {"item": c.kind})

    def effective_damage(self):
        """Dano por tiro considerando o boost de power-up."""
        return 2 if self.damage_boost > 0 else 1

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

        # --- efeitos ativos de power-up ---
        fx = w // 2
        if self.damage_boost > 0:
            lbl = font.render(f"DANO x2 {self.damage_boost:.1f}s",
                              True, (255, 140, 40))
            surface.blit(lbl, (fx - lbl.get_width() // 2, 16))
            fx += 90
        if self.speed_boost > 0:
            lbl = font.render(f"RAPIDO {self.speed_boost:.1f}s",
                              True, (80, 160, 255))
            surface.blit(lbl, (fx - lbl.get_width() // 2, 16))

        # --- mensagem de item pego ---
        if self._status_timer > 0 and self._status_msg:
            lbl = font_big.render(self._status_msg, True,
                                  (255, 220, 60))
            surface.blit(lbl, (w // 2 - lbl.get_width() // 2, 60))

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
        # --- sprites dos itens no chão (flutuando) ---
        for c in self._collectibles:
            if c.collected:
                continue
            d = math.hypot(c.x - self.rc.x, c.y - self.rc.y)
            if d > 0.3 and d < 12:
                surf = self.engine.assets.sprite(
                    {"medkit": "medkit.png",
                     "power_ammo": "power_ammo.png",
                     "power_speed": "power_speed.png",
                     "power_damage": "power_damage.png",
                     "power_health": "power_health.png"}.get(c.kind,
                                                             "medkit.png"))
                if surf is not None:
                    # projeção simples: escala conforme a distância
                    size = max(8, int(26 / d))
                    s = pygame.transform.smoothscale(surf, (size, size))
                    ang = math.atan2(c.y - self.rc.y, c.x - self.rc.x)
                    diff = math.atan2(math.sin(ang - self.rc.angle),
                                      math.cos(ang - self.rc.angle))
                    if abs(diff) < 0.7:
                        cx, cy = w // 2 + int(diff * w * 0.55), \
                            (h - 48) // 2 + 20
                        bob_y = int(4 * math.sin(c.bob))
                        surface.blit(s, (cx - size // 2, cy - size // 2
                                         + bob_y - 60))

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
