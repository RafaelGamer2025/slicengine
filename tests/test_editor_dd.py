"""Teste do editor: drag & drop de tile e entidade + undo/redo."""
import os
import sys

import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import Engine  # noqa: E402
from slicengine.editor import MapEditor  # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  [{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
engine = Engine("EdDd", 640, 400, base_dir=base)
ed = MapEditor(engine)

# 1. drag & drop de tile: clique no tile 2 da paleta e soltar no mapa
# consumir eventos de inicialização (eventos internos do core) ANTES de postar
while True:
    ev = pygame.event.poll()
    if ev.type == pygame.NOEVENT:
        break
# consumir eventos internos de inicialização
while True:
    ev = pygame.event.poll()
    if ev.type == pygame.NOEVENT:
        break
# simulação direta: clique no tile 2 da paleta e drag até o mapa
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   pos=(100, 50), button=1))
check("drag inicia com tile", ed.drag_active)
ed.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                                   pos=(300, 200)))
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,
                                   pos=(300, 200), button=1))
check("drag termina após soltar", not ed.drag_active)
gx = int((300 + ed.camera.x) // ed.tile_size)
gy = int((200 + ed.camera.y) // ed.tile_size)
check("tile pintado no mapa via drag", ed.tilemap.get(gx, gy) == 2)

# 2. drag de entidade (player) do painel inferior
w, h = engine.screen.get_size()
ey0 = h - 56
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                     pos=(20, ey0 + 12), button=1))
pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(160, 200)))
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP,
                                     pos=(160, 200), button=1))
ev = pygame.event.poll()
while ev.type != pygame.NOEVENT:
    ed.handle_event(ev)
    ev = pygame.event.poll()
ents = [e for e in ed.world.entities if e.kind == "player"]
check("player criado via drag", len(ents) == 1)

# 3. undo / redo
prev = ed.tilemap.get(gx, gy)
ed.snapshot()
ed.tilemap.set(gx, gy, 0)
check("undo reverte pintura", (lambda: (ed.undo(),
                                        ed.tilemap.get(gx, gy) == prev))()[1])
ed.redo()
check("redo restaura borracha", ed.tilemap.get(gx, gy) == 0)

print("RESULTADO:", "TODOS OK" if not FAILS else f"{len(FAILS)} falhas: "
      + ", ".join(FAILS))
