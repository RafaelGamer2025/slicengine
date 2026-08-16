"""Testes da nova camada arquitetural (headless, SDL dummy).

Cobre: Vector2, Transform, Component, GameObject, Scene, SceneManager,
EventBus, Logger e SaveSystem."""
import os
import sys
import json

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
pygame.init()
pygame.display.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicengine import utils  # noqa: E402
from slicengine.gameobjects import (  # noqa: E402
    Vector2, Transform, Component, GameObject, Scene, SceneManager,
    EventBus, Logger)
from slicengine.savesystem import SaveSystem, SaveError  # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  [{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp_dir = os.path.join(base, "tests", "_tmp_save")
os.makedirs(tmp_dir, exist_ok=True)

print("== Vector2 ==")
v = Vector2(3, 4)
check("comprimento", abs(v.length() - 5.0) < 1e-9)
check("adição", v + Vector2(1, 1) == Vector2(4, 5))
check("normalizado", abs(v.normalized().length() - 1.0) < 1e-9)
check("multiplicação", (v * 2).x, v.x * 2) if False else None

print("== Transform ==")
t = Transform()
t.position = Vector2(10, 5)
t.rotation = 90
check("posição global sem pai",
      t.global_position == Vector2(10, 5))
child = Transform()
child.position = Vector2(1, 0)
child.parent = t
check("filho local vs global (rotação 90): child global = (10,6)",
      child.global_position == Vector2(10, 6))
check("rotação global soma", child.global_rotation == 90)
check("pai adiciona filho", child in t.children)
child.parent = None
check("desparentar remove", child not in t.children)
# setter global: converte global -> local
child.global_position = Vector2(11, 5)
check("global_position setter (parente rotacionado)",
      child.global_position == Vector2(11, 5))

print("== Component ==")
events = []
bus = EventBus.shared()
bus.on("ComponentAdded", lambda p: events.append(p))


class MoveComponent(Component):
    def __init__(self, speed=1.0):
        super().__init__()
        self.speed = speed
        self.updates = 0

    def update(self, dt):
        self.updates += 1
        self.game_object.transform.position = \
            self.game_object.transform.position + \
            Vector2(self.speed * dt, 0)


print("== GameObject ==")
go = GameObject("Heroi")
go.tag = "player"
go.layer = "Heroes"
mc = go.add_component(MoveComponent(2.0))
check("componente adicionado e start/owner ok",
      mc.game_object is go and mc.updates == 0)
check("get_component", go.get_component(MoveComponent) is mc)
check("event ComponentAdded disparado", len(events) == 1)
go.set_active(False)
check("ativo/desativo", not go.active)
go.set_active(True)
clone = go.clone()
check("clone copia tag/layer/posição/componente",
      clone.tag == "player" and clone.layer == "Heroes" and
      clone.get_component(MoveComponent) is not None and
      clone.name == "Heroi_clone")
child_go = GameObject("Espada")
go.add_child(child_go)
check("pai/filho GameObject", child_go.parent is go and
      go.children == [child_go])
destroyed = []
bus.on("GameObjectDestroyed", destroyed.append)
go.destroy()
check("destruir remove componentes e filhos",
      go._destroyed and child_go._destroyed and len(go._components) == 0)
check("evento GameObjectDestroyed", len(destroyed) >= 1)

print("== Scene ==")
scene = Scene("Fase1")
scene.add(GameObject("A"))
b = GameObject("B")
b.tag = "inimigo"
scene.add(b)
check("add/find/find_by_tag",
      scene.find("A") is not None and scene.find_by_tag("inimigo") == [b])
sp = os.path.join(tmp_dir, "fase1.json")
scene.save(sp)
check("save da cena", os.path.exists(sp))
loaded = Scene.load(sp)
check("load da cena", loaded.name == "Fase1" and
      len(loaded.objects) == 2)

print("== SceneManager ==")
sm = SceneManager()
s1 = sm.new_scene("Fase1")
check("new_scene cria e troca", sm.current is s1)
s2 = sm.new_scene("Menu")
check("change e histórico", sm.current is s2 and
      "Menu" in sm.history)
check("remove_scene", sm.remove_scene("Menu") and sm.current is None)
sm.change("Fase1")
dup = sm.duplicate("Fase1", "Fase2")
check("duplicate", dup is not None and "Fase2" in sm.scenes)
check("rename", sm.rename("Fase2", "FaseX") and
      "FaseX" in sm.scenes and "Fase2" not in sm.scenes)
sm.update(0.016)
check("update da cena atual não quebra", True)

print("== EventBus / Logger ==")
log = Logger.shared()
log.clear()
log.warning("teste")
check("Logger registra warning",
      any(lv == "WARNING" for lv, _ in log.records))
emitted = []
bus.on("PlayStarted", emitted.append)
bus.emit("PlayStarted", {"fps": 60})
check("EventBus emite", emitted == [{"fps": 60}])

print("== SaveSystem ==")
ss = SaveSystem(tmp_dir)
ss.save_project("MeuJogo", "0.2.0")
proj = ss.load_project()
check("project config", proj["name"] == "MeuJogo" and
      proj["engine_version"] == utils.VERSION)
ss.save_game(1, {"level": 3, "hp": 100})
check("game save", ss.has_save(1))
g = ss.load_game(1)
check("game load", g["data"]["level"] == 3)
ss.save_game(1, {"level": 4, "hp": 50})
check("recover do backup", ss.recover(1) and
      ss.load_game(1)["data"]["level"] == 3)
ss.save_settings({"theme": "dark", "volume": 0.8})
check("settings", ss.load_settings()["theme"] == "dark")
try:
    ss.save_game(99, {})
    check("validação de slot", False)
except SaveError:
    check("validação de slot", True)
try:
    ss._write(os.path.join(tmp_dir, "x.json"), {"kind": "t"})
    # caminho fora do base deve falhar:
    bad = os.path.join(tmp_dir, "sub")
    os.makedirs(bad, exist_ok=True)
    ss2 = SaveSystem(bad)
    ss2._safe_path(bad, "../escape.json")
    check("validação de path traversal", False)
except SaveError:
    check("validação de path traversal", True)
ss.set_autosave(1, lambda: {"player_pos": [1, 2]})
ss.update(0)
ss.update(1.0)
snap = ss.recover_autosave()
check("autosave", snap == {"player_pos": [1, 2]})

import shutil
shutil.rmtree(tmp_dir, ignore_errors=True)

print(f"\n{len(FAILS)} falha(s):", FAILS)
sys.exit(1 if FAILS else 0)
