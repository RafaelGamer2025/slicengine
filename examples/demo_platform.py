"""
SlicEngine — Demo 2D real: jogo de plataforma lateral.

Este é um jogo de plataforma DE VERDADE (não visão de cima):
- personagem que pula com gravidade real e colisão com plataformas
- inimigos que patrulham e podem ser derrotados com um pulo
- moedas, lava (perigo), bandeira de vitória
- câmera lateral que segue o jogador

Controles:
    A/D ou setas ...... andar
    Espaço / W / cima . pular
    R ................. reiniciar após vitória/morte
    ESC ............... sair
"""
import os
import sys
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine.core import Engine  # noqa: E402
from slicengine.assets import AssetManager  # noqa: E402
from slicengine.platform import PlatformGame  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEVEL = """
................................................................
................................................................
..C..C..C......................................................
.............C.C.........................................G.....
...........#####...........C..............................#####
......................E..........E.E......C..C..C..............
..........#####.....################.....#####################.
.P......#.......C................................................
####...#..########..C..C.....L....L......................#.....#
################################################################
"""

def main():
    engine = Engine("Plataforma2D", 800, 480, base_dir=BASE)
    assets = AssetManager(BASE)
    pygame.display.init()

    player_sprite = assets.sprite("assets/player.png")
    enemy_sprite = assets.sprite("assets/enemy.png")
    coin_sprite = assets.sprite("assets/coin.png")

    game = PlatformGame(engine, player_sprite, enemy_sprite, coin_sprite)

    tile_sprites = {
        "#": assets.sprite("assets/tile2.png"),   # grama
        "L": assets.sprite("assets/tile5.png"),   # lava (tijolos vermelhos)
    }
    game.build(LEVEL)

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = min(0.05, clock.tick(60) / 1000.0)
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            game.handle_event(event)

        game.update(dt, keys)

        engine.screen.fill((135, 190, 230))
        game.render(engine.screen, tile_sprites)
        pygame.display.flip()

    print("Plataforma encerrada. Moedas coletadas:", game.score)


if __name__ == "__main__":
    main()
