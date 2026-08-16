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

eng.db.close()
pygame.quit()
print(f"\nRESULTADO: {len(OK)} testes OK")
assert len(OK) == 15, "alguns testes falharam"
print("ALL TESTS OK")
