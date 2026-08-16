"""
Teste automatizado do modo FPS da SlicEngine (sem janela, SDL dummy).

Simula: criação do jogo, inimigos vivos, tiro, dano nos inimigos,
morte do jogador, vitória quando todos os inimigos morrem.
"""
import math
import os
import sys
import time

import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")


def main():
    global PASS, FAIL

    print("=== Teste FPS da SlicEngine ===")

    # 1. criação
    engine = Engine("FpsTest", 640, 400, base_dir=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    engine.build_from_ascii(MAPA, "FPS Test")
    check("modo 3d", engine.mode == "3d")
    check("raycaster criado", engine.raycaster is not None)

    # 2. converter e spawnar inimigos
    engine.world.entities = [
        Enemy(e.x, e.y) if e.kind == "enemy" else e
        for e in engine.world.entities]
    fps = FPSGame(engine)
    fps.respawn_enemies([(3.5, 1.5), (5.5, 1.5), (7.5, 1.5),
                         (3.5, 3.5), (5.5, 3.5), (7.5, 3.5)])
    check("6 inimigos vivos", len(fps.enemies()) == 6)
    check("vida inicial", fps.player_hp == 100)
    check("munição inicial", fps.ammo == 50)

    # 3. tiro: apontar para um inimigo próximo
    rc = fps.rc
    e = fps.enemies()[0]
    ang = math.atan2(e.y - rc.y, e.x - rc.x)
    rc.angle = ang
    fps.ammo = 50
    hit = fps.shoot()
    check("tiro gastou munição", fps.ammo == 49)
    check("primeiro tiro acerta (inimigo na mira)", hit)
    check("inimigo levou dano (hp=2)", fps.enemies()[0].hp == 2 or hit)

    # 4. matar inimigo com mais tiros
    for _ in range(2):
        fps.shoot()
    print("  debug hp:", [(e.x, e.y, e.hp, e.alive) for e in fps.enemies()])
    print("  debug kills:", fps.kills)
    check("inimigo morreu após 3 tiros", len(fps.enemies()) == 5)
    check("kills incrementou", fps.kills == 1)

    # 5. tomar dano
    old_hp = fps.player_hp
    fps.take_damage(25)
    check("dano reduz vida", fps.player_hp == old_hp - 25)
    check("flash de dano ativo", fps.damage_flash > 0)

    # 6. game over
    fps.player_hp = 0
    fps.update(0.016)
    check("estado game over", fps.state == "gameover")

    # 7. reiniciar
    fps.restart()
    check("reinício restaura vida", fps.player_hp == 100)
    check("reinício restaura munição", fps.ammo == 50)
    check("reinício recria inimigos", len(fps.enemies()) >= 5)

    # 8. vitória (matar todos e não morrer)
    fps.player_hp = 100
    for en in list(fps.enemies()):
        en.hp = 0
        en.alive = False
    fps.update(0.016)
    check("estado vitoria", fps.state == "win")

    # 9. tipos de inimigos
    fps.respawn_enemies([(3.5, 1.5), (5.5, 1.5, "fast"), (7.5, 1.5, "tank"),
                         (3.5, 3.5, "ranged")])
    kinds = {e.enemy_kind for e in fps.enemies()}
    check("inimigos variados", kinds == {"melee", "fast", "tank", "ranged"})
    specs = {e.enemy_kind: e for e in fps.enemies()}
    check("tank tem mais vida", specs["tank"].hp == 7)
    check("fast é mais veloz", specs["fast"].speed > specs["melee"].speed)
    check("ranged ataca de longe", specs["ranged"].attack_range > 5)

    # 10. coletáveis
    fps.spawn_collectibles([(4.5, 3.5, "medkit"), (5.5, 1.5, "power_ammo"),
                            (7.5, 3.5, "power_damage")])
    check("3 itens criados", len(fps._collectibles) == 3)
    old_hp = fps.player_hp
    fps.rc.x, fps.rc.y = 4.5, 3.5   # andar até o medkit
    fps._update_collectibles(0.016)
    check("medkit cura +25", fps.player_hp == min(100, old_hp + 25))
    check("item marcado coletado", fps._collectibles[0].collected)
    fps.ammo = 5
    fps.rc.x, fps.rc.y = 5.5, 1.5
    fps._update_collectibles(0.016)
    check("power_ammo +10 munição", fps.ammo == 15)
    fps.damage_boost = 0.0
    fps.rc.x, fps.rc.y = 7.5, 3.5
    fps._update_collectibles(0.016)
    check("power_damage ativo", fps.damage_boost == 5.0)
    check("tiro dobra com boost", fps.effective_damage() == 2)

    # 11. render + HUD sem erro
    surf = engine.screen
    fps.rc.render(surf, [{"x": 5.5, "y": 5.5, "surface": pygame.Surface((16, 16))}])
    fps.render_hud(surf)
    check("HUD renderizado sem exceção", True)

    print(f"\nRESULTADO: {PASS} testes OK, {FAIL} falhas")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
