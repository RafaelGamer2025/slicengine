"""Teste GUI do renderer 3D real (xvfb-run).

Renderiza uma cena com cubos, pirâmide e chão e salva screenshot."""
import os
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "x11"
pygame.init()
pygame.display.init()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine.renderer3d import Mesh, Scene3D, Renderer3D  # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  [{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


screen = pygame.display.set_mode((800, 480))
scene = Scene3D()
scene.add_cube(0, 0, 4, color=(200, 50, 50))
scene.add_cube(3, 0, 7, size=2.0, color=(200, 160, 40))
scene.add_pyramid(-3, 0, 6, color=(50, 150, 200))
scene.add(Mesh.ground())
renderer = Renderer3D(screen, scene, yaw=0.3)
renderer.draw()
pygame.display.flip()

px = pygame.PixelArray(screen)
non_black = 0
total = screen.get_width() * screen.get_height()
for y in range(0, screen.get_height(), 8):
    for x in range(0, screen.get_width(), 8):
        if px[x][y] != 0:
            non_black += 1
del px
ratio = non_black / (total / 64)
print(f"  pixels não-pretos (amostra 1/64): {ratio:.1%}")
check("cena renderizada com conteúdo", ratio > 0.3)

shot = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "shots", "demo_3d_real_gui.png")
os.makedirs(os.path.dirname(shot), exist_ok=True)
pygame.image.save(screen, shot)
check("screenshot salvo em tests/shots/demo_3d_real_gui.png",
      os.path.exists(shot))
print("  screenshot:", shot)

print(f"\n{len(FAILS)} falha(s):", FAILS)
sys.exit(1 if FAILS else 0)
