"""
SlicEngine — Sistema de partículas (efeitos visuais).

Emitters e partículas em pool (sem alocação por frame), com gravidade,
atrito, fade de alpha e cores que variam ao longo da vida.

Uso rápido:
    from slicengine.effects import ParticleSystem

    fx = ParticleSystem()
    fx.emit(x=5.0, y=3.0, count=40, color=(255, 200, 50),
            speed=2.5, life=0.8, gravity=6.0)
    fx.emit(x=..., y=..., count=20,  # explosão
            speed=4.0, life=0.5, fade=True)

    # no loop:
    fx.update(dt)
    fx.draw(surface, camera=(cam_x, cam_y), tile_size=32)
"""
import math
import random
import pygame

# cores nomeadas úteis para efeitos
COLORS = {
    "fogo": [(255, 220, 60), (255, 160, 30), (255, 80, 20), (200, 30, 10)],
    "fumaça": [(150, 150, 160), (110, 110, 120), (80, 80, 90)],
    "magia": [(120, 80, 255), (180, 120, 255), (90, 200, 255)],
    "sangue": [(180, 20, 20), (130, 10, 10), (90, 5, 5)],
    "brilho": [(255, 255, 220), (255, 240, 150)],
    "verdes": [(60, 220, 90), (30, 180, 70)],
}


class Particle:
    """Uma partícula individual (usar pool, não instanciar solta)."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color",
                 "size", "gravity", "friction", "fade", "alive",
                 "color_vars", "angle", "spin", "grow")

    def __init__(self):
        self.alive = False

    def reset(self):
        self.alive = False
        return self


class ParticleSystem:
    """Pool de partículas com emitters."""

    def __init__(self, capacity=2000):
        self.capacity = capacity
        self.pool = [Particle() for _ in range(capacity)]
        self.count = 0
        self._rng = random.Random()

    # ------------------------------------------------------------------
    def _spawn(self):
        for p in self.pool:
            if not p.alive:
                p.alive = True
                self.count += 1
                return p
        return None

    def emit(self, x=0.0, y=0.0, count=1, color=(255, 255, 255),
             color_list=None, speed=1.0, spread=360.0, life=1.0,
             life_var=0.4, size=4.0, size_var=2.0, gravity=0.0,
             friction=0.98, fade=True, angle_center=None,
             angle_spread=None, spin=0.0, grow=0.0):
        """Emitir `count` partículas em (x, y).

        Parâmetros:
            color/color_list: cor fixa ou lista de cores (sorteada por
                              partícula)
            speed: velocidade máxima inicial (pixels/s em tela)
            spread: ângulo aleatório em graus (360 = círculo completo)
            life: duração média em segundos
            size: raio médio em pixels
            gravity: aceleração para baixo (pixels/s²)
            friction: fator por segundo aplicado à velocidade
            fade: alpha decai com a vida
        """
        colors = color_list or [color]
        for _ in range(count):
            p = self._spawn()
            if p is None:
                return
            rng = self._rng
            ang = rng.uniform(0, 360) if spread >= 360 \
                else rng.uniform(-spread / 2, spread / 2) + \
                (angle_center or 0)
            v = rng.uniform(speed * 0.2, speed)
            rad = math.radians(ang)
            p.x = x + rng.uniform(-1.5, 1.5)
            p.y = y + rng.uniform(-1.5, 1.5)
            p.vx = math.cos(rad) * v
            p.vy = math.sin(rad) * v
            p.life = life + rng.uniform(-life_var, life_var)
            p.life = max(0.05, p.life)
            p.max_life = p.life
            p.color = colors[rng.randrange(len(colors))]
            p.size = max(1.0, size + rng.uniform(-size_var, size_var))
            p.gravity = gravity
            p.friction = friction
            p.fade = fade
            p.angle = rng.uniform(0, 360)
            p.spin = spin
            p.grow = grow

    # ------------------------------------------------------------------
    def update(self, dt):
        """Atualiza todas as partículas vivas."""
        dt = min(dt, 0.05)
        self.count = 0
        for p in self.pool:
            if not p.alive:
                continue
            p.life -= dt
            if p.life <= 0:
                p.alive = False
                continue
            self.count += 1
            p.vx *= max(0.0, p.friction ** (dt * 60))
            p.vy = p.vy * max(0.0, p.friction ** (dt * 60)) + \
                p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.angle = (p.angle + p.spin * dt) % 360
            if p.grow:
                p.size = min(p.size * (1 + p.grow * dt), p.size + 20)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera=(0.0, 0.0),
             tile_size=32, center_xy=False, fog_factor=None):
        """Desenha partículas.

        Modo tela (padrão): x/y já em pixels, camera=(cam_x, cam_y).
        Modo mundo (center_xy=True): x/y em coordenadas de tile
        (tiles), convertidas para pixels com tile_size e câmera.
        """
        cx, cy = camera
        # agrupar por (cor, fade) para desenhar por círculo sólido:
        # mais rápido que set_at por pixel
        if self.count == 0:
            return
        for p in self.pool:
            if not p.alive:
                continue
            if center_xy:
                px = p.x * tile_size - cx
                py = p.y * tile_size - cy
            else:
                px = p.x - cx
                py = p.y - cy
            t = p.life / p.max_life if p.max_life > 0 else 0.0
            if p.fade:
                alpha = max(0.0, min(1.0, t))
            else:
                alpha = 1.0
            size = max(1.0, p.size * (0.5 + 0.7 * t))
            r, g, b = p.color
            col = (int(r * (0.5 + 0.5 * (alpha if p.fade else 1.0))),
                   int(g * (0.5 + 0.5 * (alpha if p.fade else 1.0))),
                   int(b * (0.5 + 0.5 * (alpha if p.fade else 1.0))))
            pygame.draw.circle(surface, col, (int(px), int(py)),
                               int(size))

    def clear(self):
        for p in self.pool:
            p.alive = False
        self.count = 0

    def alive_count(self):
        return self.count
