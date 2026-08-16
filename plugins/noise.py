"""
SlicEngine — Mod Python que expõe o plugin nativo C `noise.so`
para a linguagem de script em português, Lua e Python.

Coloque `noise.py` e `noise.so` na pasta `plugins/`.
O plugin C é registrado automaticamente; este módulo adiciona atalhos:

    engine.noise_next()      -> inteiro 0..255
    engine.noise_fill(n)     -> lista com n bytes de ruído
"""
import ctypes
import os
import sys

_EXT = {
    "linux": ".so",
    "win32": ".dll",
    "darwin": ".dylib",
}


def _lib_path():
    here = os.path.dirname(os.path.abspath(__file__))
    ext = _EXT.get(sys.platform, ".so")
    return os.path.join(here, "slic_noise" + ext)


def register(engine):
    try:
        lib = ctypes.CDLL(_lib_path())
    except OSError as e:
        print(f"[Mods] plugin noise não disponível: {e}")
        return

    lib.noise_seed.argtypes = [ctypes.c_ulong]
    lib.noise_next.restype = ctypes.c_int
    lib.noise_fill.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
    lib.noise_fill.restype = ctypes.c_int

    def noise_next():
        return lib.noise_next()

    def noise_fill(n):
        buf = (ctypes.c_ubyte * n)()
        lib.noise_fill(buf, int(n))
        return list(buf)

    def noise_seed(s=0):
        lib.noise_seed(s)

    # expõe na API global da engine
    engine.add_var = getattr(engine, "add_var", lambda *a: None)
    api = engine._build_api()
    engine._noise_api = api

    # atalhos diretos no objeto engine
    engine.noise_next = noise_next
    engine.noise_fill = noise_fill
    engine.noise_seed = noise_seed
    print("[Mods] noise (plugin C) disponível via engine.noise_*")
