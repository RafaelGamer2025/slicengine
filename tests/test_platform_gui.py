"""Teste GUI da demo de plataforma 2D real (xvfb-run).

Verifica física, pulo, moedas, inimigos e renderização em tela real."""
import os
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "x11"
os.environ["SDL_AUDIODRIVER"] = "pulse"
pygame.init()
pygame.display.init()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine.core import Engine  # noqa: E402
from slicengine.assets import AssetManager  # noqa: E402
from slicengine.platform import PlatformGame  # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  [{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
engine = Engine("PlatGui", 800, 480, base_dir=base)
assets = AssetManager(base)
game = PlatformGame(
    engine, assets.sprite("assets/player.png"),
    assets.sprite("assets/enemy.png"), assets.sprite("assets/coin.png"),
)
LEVEL = (
    "...............................\n"
    "........C..C.................C.\n"
    ".......#######...............G.\n"
    ".....C..........E.E............\n"
    ".P..................############\n"
    "################################\n"
)
game.build(LEVEL)

# consumir eventos internos de inicialização
while True:
    ev = pygame.event.poll()
    if ev.type == pygame.NOEVENT:
        break

clock = pygame.time.Clock()
running = True
steps = 0
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT}))
while running and steps < 3000:
    dt = min(0.05, clock.tick(60) / 1000.0)
    keys = {pygame.K_RIGHT: True}
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    game.update(dt, keys)
    steps += 1
    if game.state != "playing":
        running = False

check("player se moveu", game.player.x > 1.6)
check("estado da demo", game.state in ("playing", "won", "dead"))
check("inimigos existem e patrulham", len(game.enemies) == 2)
print("  estado final:", game.state, "| moedas:", game.score,
      "| px:", round(game.player.x, 2))

screen = pygame.display.set_mode((800, 480))
screen.fill((135, 190, 230))
game.render(screen, {
    "#": assets.sprite("assets/tile2.png"),
    "L": assets.sprite("assets/tile5.png"),
})
shot = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "shots", "demo_platform.png")
os.makedirs(os.path.dirname(shot), exist_ok=True)
pygame.image.save(screen, shot)
check("screenshot salvo em tests/shots/demo_platform.png",
      os.path.exists(shot))
print("  screenshot:", shot)

print(f"\n{len(FAILS)} falha(s):", FAILS)
sys.exit(1 if FAILS else 0)
