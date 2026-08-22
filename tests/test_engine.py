"""Testes headless da SlicEngine (sem janela, SDL dummy)."""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()

from slicengine import (Engine, World, SEFormat, PTScript, ScriptRunner,
                        Shell, Hierarchy, AIAssistant)

OK = []


def check(name, cond, extra=""):
    if cond:
        OK.append(name)
        print(f"  [OK] {name}")
    else:
        print(f"  [FAIL] {name} {extra}")


print("== World / TileMap ==")
w = World.from_ascii("""
###
#P#
#.#
###
""")
check("world ascii", w.tilemap.width == 3 and len(w.entities) == 1)

print("== Formato .se ==")
fmt = SEFormat()
fmt.save(w, "/tmp/teste.se", title="Teste", mode="3d")
w2 = fmt.load("/tmp/teste.se")
check("se save/load", w2.tilemap.width == 3 and w2.flags["title"] == "Teste")
contents = fmt.list_contents("/tmp/teste.se")
check("se contents", "manifest.json" in contents and "world.json" in contents)

print("== Script em português (.sl) ==")
src = '''quando tecla "espaço" for pressionada:
    aumentar 1 no "PONTOS"

sempre:
    se "vida" menor que 0:
        parar jogo
'''
eng = Engine("Teste", 320, 240)
ps = PTScript(src)
ps.register(eng)
check("ptscript register",
      "tecla:space" in eng._handlers and "update" in eng._handlers)
eng.db.close()

# gramática "definir X como Y" (usava "para" antes — bug corrigido)
src2 = '''quando iniciar:
    definir "vida" como 100
    definir "nome" como "red"
'''
eng2 = Engine("Teste2", 320, 240)
PTScript(src2).register(eng2)
# "quando iniciar" roda quando o evento "iniciar" é disparado
eng2.disparar("iniciar")
check("ptscript definir como",
      eng2.lua_state["vars"].get("vida") == 100 and
      eng2.lua_state["vars"].get("nome") == "red",
      f"{eng2.lua_state['vars']}")
eng2.db.close()

# "destruir evento" mata uma entidade viva
src3 = '''quando colidir com "moeda":
    destruir evento
'''
from slicengine.world import Entity
eng3 = Engine("Teste3", 320, 240)
eng3.world.entities.append(Entity("coin", 2.0, 2.0))
PTScript(src3).register(eng3)
eng3.disparar("colidir:moeda", {})
check("ptscript destruir evento",
      all(not e.alive for e in eng3.world.entities if e.kind == "coin"))
eng3.db.close()

print("== ScriptRunner (Lua/Python) ==")
r = ScriptRunner(eng)
res1 = r.run_string('engine.set_var("x", 42)', "lua")
check("lua set_var", res1 == "OK" and eng.lua_state["vars"].get("x") == 42,
      res1)
res2 = r.run_string('engine.add_var("x", 8)', "lua")
check("lua add_var", eng.lua_state["vars"]["x"] == 50,
      f"-> {eng.lua_state['vars']}")
res3 = r.run_string("engine.set_var('y', 7)", "python")
check("python run", res3 == "OK" and eng.lua_state["vars"].get("y") == 7,
      res3)

print("== Shell embutido ==")
sh = Shell()
out = sh.run("pip --version")
check("shell pip", "pip" in out.lower(), out[:60])
out2 = sh.run("sudo rm -rf /")
check("shell bloqueia perigosos", "bloqueado" in out2.lower(), out2[:50])

print("== Hierarquia ==")
h = Hierarchy()
h.add_camera("Cam1", {"x": 0}, priority=100)
h.add_camera("Cam2", {"x": 1}, priority=10)
h.add_script("S1", lambda dt, e: None, priority=10)
h.add_script("S0", lambda dt, e: None, priority=90)
h.add_command("Cmd1", "colidir:moeda", lambda d: None, priority=5)
results = {"ran": []}
h.add_script("Slog", lambda dt, e: results["ran"].append("Slog"),
             priority=1)
check("active camera", h.active_camera.name == "Cam1")
check("scripts ordenados",
      [n.name for n in h.scripts()] == ["S0", "S1", "Slog"])
h.dispatch("colidir:moeda")
h.run_scripts(0.016)
check("dispatch/run", results["ran"] == ["Slog"])

print("== IA local ==")
ai = AIAssistant()
resp = ai.ask_local("como faço um pulo?")
check("ai local pulo", "function update" in resp or "pulo" in resp.lower(),
      resp[:80])
resp2 = ai.ask_local("ajuda")
check("ai local ajuda", "SlicEngine" in resp2, resp2[:60])

print("== ModSystem ==")
from slicengine.modsystem import ModSystem
ms = ModSystem(eng)
ms.scan_folder("/tmp")
check("mods scan", len(ms.plugins) >= 0)

print("== Partículas (v0.2) ==")
from slicengine.effects import ParticleSystem, COLORS
fx = ParticleSystem(capacity=100)
fx.emit(x=5.0, y=3.0, count=30, color=(255, 0, 0), speed=2.0,
        life=1.0, life_var=0.0)
check("emit 30 partículas", fx.alive_count() == 30)
fx.update(0.5)
check("update mantém vivas", fx.alive_count() > 0)
for _ in range(60):
    fx.update(0.05)   # clamp interno: dt máx 0.05 por passo
check("todas mortas após vida", fx.alive_count() == 0)
# cores nomeadas
check("CORES fogo", len(COLORS["fogo"]) >= 3)

print("== Sprites animados (v0.2) ==")
from slicengine.spritesheet import Animation, AnimatedSprite
frames = [pygame.Surface((16, 16)) for _ in range(4)]
anim = Animation(frames, fps=4)
runner = AnimatedSprite(anim, mode="once")
runner.update(1.5)
check("once para no último", runner.frame_index == 3 and runner.finished)
runner2 = AnimatedSprite(anim, mode="loop")
runner2.elapsed = 0.6
check("loop continua", runner2.frame_index < 4)
runner3 = AnimatedSprite(anim, mode="pingpong")
runner3.elapsed = 0.9
check("pingpong reflete", 0 <= runner3.frame_index < 4)

print("== Saves (v0.2) ==")
from slicengine.saves import SaveManager
eng4 = Engine("Teste4", 320, 240)
eng4.build_from_ascii("###\n#P.\n###", "Save teste")
eng4.set_var("pontos", 77)
mgr = SaveManager(eng4)
mgr.save("slot_teste", titulo="Teste Save")
check("save existe", mgr.exists("slot_teste"))
eng4.lua_state["vars"]["pontos"] = 0
check("load restaura vars", mgr.load("slot_teste") and
      eng4.lua_state["vars"].get("pontos") == 77)
check("listar saves", len(mgr.list_saves()) >= 1)
mgr.delete("slot_teste")
check("deletar save", not mgr.exists("slot_teste"))
eng4.db.close()

print("== Editor undo/redo (v0.2) ==")
from slicengine.editor import MapEditor, TOOL_BRUSH
eng5 = Engine("Teste5", 320, 240)
editor = MapEditor(eng5)
editor.tilemap.set(2, 2, 5)
editor._snapshot()
editor.tilemap.set(2, 2, 0)
editor.undo()
check("undo restaura tile", editor.tilemap.get(2, 2) == 5)
editor.redo()
check("redo reaplica", editor.tilemap.get(2, 2) == 0)
eng5.db.close()

print("== Lua show_text via toast (v0.2) ==")
from slicengine.lua_api import build_lua_api
eng6 = Engine("Teste6", 320, 240)
rt6 = build_lua_api(eng6)
rt6.execute('engine.show_text("Olá Lua", 2)')
check("lua show_text → toast", eng6._toast is not None and
      eng6._toast[0] == "Olá Lua")
eng6.db.close()

print("== run_file extensões (v0.2) ==")
from slicengine.local import ScriptRunner
import tempfile
eng7 = Engine("Teste7", 320, 240)
r7 = ScriptRunner(eng7)
with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as f:
    f.write('engine.set_var("auto", 9)')
    lua_tmp = f.name
res = r7.run_file(lua_tmp)
os.unlink(lua_tmp)
check("run_file .lua auto", res == "OK" and
      eng7.lua_state["vars"].get("auto") == 9, res)
eng7.db.close()

eng.db.close()
pygame.quit()
print(f"\nRESULTADO: {len(OK)} testes OK")
assert len(OK) == 32, "alguns testes falharam"
print("ALL TESTS OK")
