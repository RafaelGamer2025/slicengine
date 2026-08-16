"""Teste rápido do renderizador 3D real (projeção de polígonos)."""
import os
import sys

import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine.renderer3d import Mesh, Renderer3D, Scene3D  # noqa: E402

sc = Scene3D()
sc.add_cube(0, 0, 4, color=(200, 50, 50))
sc.add_cube(3, 0, 7, size=2.0, color=(200, 160, 40))
sc.add_pyramid(-3, 0, 6, color=(50, 150, 200))
sc.add(Mesh.ground())

screen = pygame.display.set_mode((640, 360), 0, 32)
r = Renderer3D(screen, sc, camera_pos=(0, 1.6, 0), yaw=0.3)
r.draw()
pygame.image.save(screen, "tests/shots/demo_3d_real.png")
print("render ok")
