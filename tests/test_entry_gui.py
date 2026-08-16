"""
Teste GUI do fluxo de entrada da SlicEngine (menu / novo jogo / perfil).

Navega pelo MenuScreen e verifica que:
- o menu principal desenha e os cliques funcionam
- a tela de Novo Jogo grava projeto no banco e abre o editor
- a tela de Perfis lista/cria perfis e seleciona
- o banco SQLite fica consistente

Salva screenshots do fluxo em tests/shots/.
"""
import os
import sys
import time
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

pygame.display.init()
pygame.font.init()

from slicengine import Engine  # noqa: E402

TMP = tempfile.mkdtemp(prefix="slicengine_entry_")
SCREEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(SCREEN, exist_ok=True)

failures = []


def check(desc, ok):
    print(" ", "[OK]" if ok else "FAIL", desc)
    if not ok:
        failures.append(desc)


def key_down(key):
    pygame.event.post(pygame.event.Event(
        pygame.KEYDOWN, key=key, mod=0, unicode=""))


def click(x, y):
    pygame.event.post(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y)))


def step(engine, n=3):
    for _ in range(n):
        for ev in pygame.event.get():
            # reproduzir o que o loop da Engine faz no estado menuscreen
            if ev.type == pygame.KEYDOWN:
                engine.disparar(f"tecla:{pygame.key.name(ev.key)}")
                if engine.state == "menuscreen":
                    engine._menu_screen.handle_event(ev)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                engine.disparar("mouse:click", ev.pos)
                engine._menu_screen.handle_event(ev)
        dt = 0.016
        engine.elapsed += dt
        engine._menu_screen.update(dt)
        engine._menu_screen.draw()
        pygame.display.flip()
        time.sleep(0.05)


def shot(name):
    pygame.image.save(engine.screen, os.path.join(SCREEN, name))


engine = Engine("Teste Entrada", 800, 600, base_dir=TMP)
engine.run_entry()
step(engine)
shot("entry_menu_main.png")

# --- menu principal: entrar em Perfis (tecla 3) ---
print("== Menu principal ==")
key_down(pygame.K_3)
step(engine)
shot("entry_perfis.png")
check("tela Perfis aberta", engine._menu_screen.screen == "profiles")

# --- criar perfil ---
print("== Criar perfil ==")
key_down(pygame.K_n)
step(engine)
check("tela novo perfil aberta",
      engine._menu_screen.screen == "profile_new")
for ch in "Marina":
    engine._menu_screen.handle_event(pygame.event.Event(
        pygame.KEYDOWN, key=0, mod=0, unicode=ch))
step(engine)
key_down(pygame.K_RETURN)
step(engine)
check("perfil selecionado", engine.profile_name == "Marina")
check("perfil criado no banco", engine.profile_id > 0)

# --- entrar em Novo Jogo (tecla 2) e criar ---
print("== Novo Jogo ==")
key_down(pygame.K_2)
step(engine)
shot("entry_novo_jogo.png")
check("tela Novo Jogo aberta", engine._menu_screen.screen == "new")
for ch in "Meu Primeiro Jogo":
    engine._menu_screen.handle_event(pygame.event.Event(
        pygame.KEYDOWN, key=0, mod=0, unicode=ch))
step(engine)
key_down(pygame.K_RETURN)
step(engine)
check("editor aberto", engine.state == "editor")
check("projeto gravado no banco",
      any(p["title"] == "Meu Primeiro Jogo"
          for p in engine.db.list_projects(engine.profile_id)))

# --- voltar ao menu (ESC) e ver os jogos ---
print("== Voltar ao menu ==")
engine.state = "menuscreen"
key_down(pygame.K_ESCAPE)
step(engine)
shot("entry_menu_voltou.png")
check("voltou ao menu", engine._menu_screen.screen == "main")

# --- entrar em Jogos/Projetos (tecla 1) e ver o projeto ---
print("== Meus Jogos ==")
key_down(pygame.K_1)
step(engine)
shot("entry_projetos.png")
check("tela projetos aberta",
      engine._menu_screen.screen == "projects")
projs = engine.db.list_projects(engine.profile_id)
check("projeto aparece na lista",
      any(p["title"] == "Meu Primeiro Jogo" for p in projs))

# --- abrir o projeto: como não tem arquivo, vai para o editor ---
print("== Abrir projeto ==")
key_down(pygame.K_1)
step(engine)
check("projeto sem arquivo abre editor", engine.state == "editor")

# --- demos: listar ---
print("== Demos ==")
engine.state = "menuscreen"
key_down(pygame.K_ESCAPE)   # garantir que está no menu principal
step(engine)
key_down(pygame.K_4)
step(engine)
shot("entry_demos.png")
check("tela demos aberta", engine._menu_screen.screen == "demos")
check("5 demos listadas",
      len(engine._menu_screen._demo_items()) == 5)

print(f"{len(failures)} falha(s): {failures}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if failures else 0)
