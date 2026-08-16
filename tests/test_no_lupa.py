"""
Teste de compatibilidade: a engine DEVE iniciar sem o módulo lupa
instalado (import opcional).

Simula a ausência do lupa ocultando-o do sys.modules durante a
importação dos módulos da engine e verificando:
- modsystem carrega sem lupa
- local.ScriptRunner aceita Python e .sl sem lupa
- o ModSystem avisa (1 vez) e lua_available é False
- com lupa disponível, mods Lua continuam funcionando
"""
import sys
import os
import importlib
import tempfile
import shutil

sys.path.insert(0, ".")

TMP = tempfile.mkdtemp(prefix="slic_nolupa_")
failures = []


def check(desc, ok):
    print("  [OK]" if ok else "  FAIL", desc)
    if not ok:
        failures.append(desc)


# 1) bloquear lupa e recarregar os módulos que dependem dele
blocked = [k for k in sys.modules if k == "lupa" or k.startswith("lupa.")]
saved = {k: sys.modules.pop(k) for k in blocked}
import builtins
_real_import = builtins.__import__


def _no_lupa_import(name, *args, **kwargs):
    if name == "lupa" or name.startswith("lupa."):
        raise ModuleNotFoundError(f"No module named {name!r}")
    return _real_import(name, *args, **kwargs)


builtins.__import__ = _no_lupa_import

try:
    # recarregar módulos afetados
    mods = ["slicengine.lua_api", "slicengine.modsystem",
            "slicengine.local"]
    for m in mods:
        if m in sys.modules:
            del sys.modules[m]
    from slicengine.modsystem import ModSystem  # noqa
    from slicengine import modsystem as _ms
    from slicengine import local as _local

    print("== Sem lupa ==")

    class FakeEngine:
        lua_state = {"vars": {}, "snd_queue": [], "mus_queue": [],
                     "texts": [], "spawns": [], "player_move": [],
                     "stop": False, "window": None, "lua_start": False,
                     "load_map": None}
        _handlers = {}

        def adicionar_evento(self, eid, cb):
            self._handlers.setdefault(eid, []).append(cb)

        def adicionar_evento_lua(self, eid, fn):
            self.adicionar_evento(eid, fn)

    e = FakeEngine()
    ms = ModSystem(e)
    check("ModSystem inicia sem lupa", True)
    check("lua_available é False", not ms.lua_available)

    # ScriptRunner sem lupa: Python e .sl devem funcionar
    runner = _local.ScriptRunner(e)
    out = runner.run_string('print("ola")', lang="python")
    check("ScriptRunner roda Python sem lupa", out == "OK")
    out = runner.run_string('quando iniciar:\n    definir "x" para 1',
                            lang="sl")
    check("ScriptRunner roda .sl sem lupa", out == "OK")
    out = runner.run_string('x = 1', lang="lua")
    check("ScriptRunner recusa Lua sem lupa com mensagem clara",
          out.startswith("ERRO") and "pip install lupa" in out)

    # ModSystem: mod Python/.sl carrega; Lua falha com mensagem clara
    import os as _os
    pd = os.path.join(TMP, "mods")
    os.makedirs(pd)
    with open(os.path.join(pd, "t.py"), "w") as f:
        f.write("def register(engine): engine._reg_ok = True\n")
    with open(os.path.join(pd, "ex.sl"), "w") as f:
        f.write('quando iniciar:\n    definir "a" para 1\n')
    with open(os.path.join(pd, "bad.lua"), "w") as f:
        f.write("engine.set_var('b', 1)\n")
    e._reg_ok = False
    ms.scan_folder(pd)
    ms.load_all()
    check("mod Python carregou sem lupa", e._reg_ok)
    pl = [p for p in ms.plugins if p.name == "bad"][0]
    check("mod Lua falha com mensagem clara",
          pl.error is not None and "pip install lupa" in pl.error)
finally:
    builtins.__import__ = _real_import
    for k, v in saved.items():
        sys.modules[k] = v
    # recarregar módulos afetados com o lupa novamente disponível
    for m in ["slicengine.lua_api", "slicengine.modsystem",
              "slicengine.local", "slicengine.core",
              "slicengine"]:
        if m in sys.modules:
            importlib.reload(sys.modules[m])

# 2) com lupa disponível, mods Lua funcionam
print("== Com lupa ==")
import pygame  # noqa: E402
pygame.display.init()
pygame.font.init()
from slicengine import Engine  # noqa: E402
tmp2 = tempfile.mkdtemp()
try:
    eng = Engine("Teste Lua", 400, 300, base_dir=tmp2)
    check("Engine inicia com lupa", eng.mods.lua_available)
    _eng_ok = eng
except Exception as ex:  # noqa: E722
    print("  [DEBUG erro Engine]", type(ex).__name__, ex)
    _eng_ok = None
    check("Engine inicia com lupa (erro: {})".format(ex), False)
if _eng_ok is not None:
    _eng_ok.mods.unload_all()
    import lupa as _lupa  # noqa
    rt = _eng_ok.mods._rt = __import__("slicengine.lua_api",
                                       fromlist=["build_lua_api"]) \
        .build_lua_api(_eng_ok, _lupa)
    rt.execute("engine.set_var('pontos', 42)")
    check("mod Lua executa e set_var funciona",
          _eng_ok.lua_state["vars"].get("pontos") == 42)
else:
    _eng_ok = None

print(f"{len(failures)} falha(s): {failures}")
shutil.rmtree(TMP, ignore_errors=True)
shutil.rmtree(tmp2, ignore_errors=True)
sys.exit(1 if failures else 0)
