"""
SlicEngine — Sistema de mods e plugins.

Carrega:
- Mods Lua   (.lua)  — script com engine.on_event(...)
- Scripts Python (.py) — módulo com função register(engine)
- Scripts em português (.sl) — linguagem própria da engine
- Plugins nativos C (.so/.dll/.pyd) — via ctypes

Também carrega todos os scripts embarcados dentro de um pacote .se.
"""
import os
import sys
import importlib
import importlib.util
import ctypes
import traceback
import lupa

from .lua_api import build_lua_api, _wrap_callable
from .ptscript import PTScript


class Plugin:
    def __init__(self, name, kind, path):
        self.name = name
        self.kind = kind      # "lua", "python", "sl", "c", "embedded"
        self.path = path
        self.loaded = False
        self.error = None


class ModSystem:
    def __init__(self, engine):
        self.engine = engine
        self.plugins: list[Plugin] = []
        self._rt = None
        self._c_libs = []

    # ------------------------------------------------------------------
    def scan_folder(self, folder: str):
        """Varre uma pasta em busca de mods carregáveis."""
        if not os.path.isdir(folder):
            return
        for fn in sorted(os.listdir(folder)):
            full = os.path.join(folder, fn)
            if fn.endswith(".lua"):
                self.plugins.append(Plugin(fn[:-4], "lua", full))
            elif fn.endswith(".py") and fn != "__init__.py":
                self.plugins.append(Plugin(fn[:-3], "python", full))
            elif fn.endswith(".sl"):
                self.plugins.append(Plugin(fn[:-3], "sl", full))
            elif fn.endswith((".so", ".dll", ".pyd")):
                self.plugins.append(Plugin(fn, "c", full))

    # ------------------------------------------------------------------
    def load_all(self):
        """Carrega todos os plugins registrados."""
        for p in self.plugins:
            try:
                self._load_one(p)
                p.loaded = True
            except Exception as e:
                p.error = str(e)
                print(f"[Mods] falha ao carregar {p.name}: {e}")
                traceback.print_exc()

    def _load_one(self, p: Plugin):
        if p.kind == "lua":
            if self._rt is None:
                self._rt = build_lua_api(self.engine)
            with open(p.path, encoding="utf-8") as f:
                src = f.read()
            self._rt.execute(src)
        elif p.kind == "python":
            spec = importlib.util.spec_from_file_location(p.name, p.path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(self.engine)
        elif p.kind == "sl":
            with open(p.path, encoding="utf-8") as f:
                src = f.read()
            PTScript(src).register(self.engine)
        elif p.kind == "c":
            lib = ctypes.CDLL(p.path)
            self._c_libs.append(lib)
            if hasattr(lib, "se_plugin_register"):
                lib.se_plugin_register()
            if hasattr(lib, "se_plugin_name"):
                lib.se_plugin_name.restype = ctypes.c_char_p
                print(f"[Mods] plugin C carregado: "
                      f"{lib.se_plugin_name().decode()}")

    # ------------------------------------------------------------------
    def unload_all(self):
        self.plugins.clear()
        self._c_libs.clear()
        self._rt = None
