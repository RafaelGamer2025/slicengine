"""
SlicEngine — Demo FPS 3D completo estilo Doom.

Jogo jogável com:
- Inimigos interativos que perseguem e atacam o jogador
- Sistema de tiro (clique do mouse ou F): raio na mira, gasto de munição,
  dano nos inimigos, hit markers
- HUD estilo Doom: vida, munição, inimigos restantes, arma, flashes
- Música de fundo e sons de tiro/dano

Controles:
- WASD / Setas: andar       Q/E ou mouse: olhar
- Clique / F: atirar         R: reiniciar (após vitória ou morte)

Execução:
    python examples/demo_fps.py
    python -m slicengine examples/demo_fps.py
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from slicengine import Engine  # noqa: E402
from slicengine.fps import FPSGame, Enemy  # noqa: E402

MAPA = """
####################
#P..#....#.....#...#
#...#....#..E..#...#
#...####.#####.C...#
#.............#....#
#.E.......#...######
#.........#........#
####.#####.####.#.##
#....#...#........##
#....#...#.E.......#
####################
"""


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    engine = Engine("FPS Demo", 800, 480, base_dir=base)
    engine.build_from_ascii(MAPA, "Demo FPS — Caçada no Labirinto")

    # carregar sprites e sons do FPS
    try:
        gun = engine.assets.sprite("assets/gun.png")
    except Exception:
        gun = None
    try:
        enemy_sprite = engine.assets.sprite("assets/enemy_fps.png")
    except Exception:
        enemy_sprite = None

    # converter inimigos genéricos em Enemy (FPSGame precisa)
    engine.world.entities = [
        Enemy(e.x, e.y) if e.kind == "enemy" else e
        for e in engine.world.entities]

    fps = FPSGame(engine, gun_sprite=gun, enemy_sprite=enemy_sprite)
    fps.respawn_enemies([(4.5, 2.5), (8.5, 7.5), (12.5, 2.5),
                         (3.5, 9.5), (14.5, 8.5), (10.5, 6.5)])

    # música de fundo (streaming)
    try:
        engine.assets.music_play("sounds/inicio.wav", volume=0.5, loops=-1)
    except Exception:
        pass

    running = True
    last = time.perf_counter()
    while running and engine.state != "exit":
        now = time.perf_counter()
        dt = min(0.05, now - last)
        last = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                fps.handle_event(event)

        keys = {pygame.K_w: False, pygame.K_s: False,
                pygame.K_a: False, pygame.K_d: False}
        for k in list(keys):
            keys[k] = bool(pygame.key.get_pressed().get(k, False))
        keys[pygame.K_UP] = bool(pygame.key.get_pressed().get(
            pygame.K_UP, False))
        keys[pygame.K_DOWN] = bool(pygame.key.get_pressed().get(
            pygame.K_DOWN, False))
        keys[pygame.K_LEFT] = bool(pygame.key.get_pressed().get(
            pygame.K_LEFT, False))
        keys[pygame.K_RIGHT] = bool(pygame.key.get_pressed().get(
            pygame.K_RIGHT, False))

        fps.update(dt)
        fps.rc.move(keys, dt)

        # rotação com mouse
        mx, *_ = pygame.mouse.get_rel()
        fps.rc.angle += mx * 0.002

        # sprites dos inimigos vivos
        sprites = [
            {"x": e.x, "y": e.y, "surface": enemy_sprite}
            for e in engine.world.entities
            if e.kind == "enemy" and e.alive]

        fps.rc.render(engine.screen, sprites)
        fps.render_hud(engine.screen)
        pygame.display.flip()

        engine.clock.tick(60)


if __name__ == "__main__":
    main()
