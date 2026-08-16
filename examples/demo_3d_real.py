"""
SlicEngine — Demo 3D real: renderizador por projeção de polígonos.

Este é 3D DE VERDADE (não raycasting): o Renderer3D projeta vértices
reais de cubos e pirâmides em espaço 3D para a tela, com z-buffer por
pixel e sombreamento por face.

Cena: cubos coloridos, pirâmides e um chão quadriculado.

Controles:
    A / D ou setas ...... andar para os lados
    W / S ............... avançar / recuar
    Mouse (segurar) ..... olhar ao redor
    ESC ................. sair
"""
import math
import os
import sys
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine.renderer3d import Mesh, Scene3D, Renderer3D  # noqa: E402

pygame.init()
pygame.display.init()


def build_scene():
    scene = Scene3D()
    scene.add_cube(0, 0, 4, color=(200, 50, 50))
    scene.add_cube(3, 0, 7, size=2.0, color=(200, 160, 40))
    scene.add_pyramid(-3, 0, 6, color=(50, 150, 200))
    scene.add_cube(-1.5, 0, 5.5, size=0.7, color=(240, 220, 60))
    scene.add_cube(1.6, 0, 9, size=1.2, color=(160, 80, 220))
    scene.add_pyramid(2.6, 0, 3.6, color=(60, 200, 120))
    scene.add(Mesh.ground())
    return scene


def main():
    screen = pygame.display.set_mode((800, 480))
    pygame.display.set_caption("SlicEngine — Demo 3D real (projeção)")
    scene = build_scene()
    renderer = Renderer3D(screen, scene)

    clock = pygame.time.Clock()
    running = True
    looking = False
    last_mx = 0
    instructions = (
        "A/D ou setas: andar | W/S: avançar/recuar | "
        "Mouse: olhar | ESC: sair"
    )
    while running:
        dt = min(0.05, clock.tick(60) / 1000.0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                looking = True
                last_mx = event.pos[0]
            elif event.type == pygame.MOUSEBUTTONUP:
                looking = False

        keys = pygame.key.get_pressed()
        speed = 2.5 * dt
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            renderer.cam_pos[0] -= math.cos(renderer.yaw) * speed
            renderer.cam_pos[2] -= math.sin(renderer.yaw) * speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            renderer.cam_pos[0] += math.cos(renderer.yaw) * speed
            renderer.cam_pos[2] += math.sin(renderer.yaw) * speed
        if keys[pygame.K_w]:
            renderer.cam_pos[0] += math.cos(renderer.yaw) * speed
            renderer.cam_pos[2] += math.sin(renderer.yaw) * speed
        if keys[pygame.K_s]:
            renderer.cam_pos[0] -= math.cos(renderer.yaw) * speed
            renderer.cam_pos[2] -= math.sin(renderer.yaw) * speed

        if looking:
            mx = pygame.mouse.get_pos()[0]
            renderer.yaw += (mx - last_mx) * 0.004
            last_mx = mx

        renderer.draw()

        font = pygame.font.SysFont("dejavusans", 18, bold=True)
        lbl = font.render(instructions, True, (255, 255, 255))
        screen.blit(lbl, (10, screen.get_height() - 30))
        pygame.display.flip()

    print("Demo 3D encerrada.")


if __name__ == "__main__":
    main()
