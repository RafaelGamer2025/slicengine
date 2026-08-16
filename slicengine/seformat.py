"""
SlicEngine — Formato de pacote .SE (SlicEngine Package).

Um arquivo .se é um ZIP contendo:
    manifest.json   — nome, versão, autor, tipo (2d/3d), script principal
    world.json      — mapa (tilemap + grade raycaster) e entidades
    main.lua        — script Lua (opcional)
    main.py         — script Python (opcional)
    script.sl       — script em português (opcional)
    assets/         — sprites, sons, músicas, gifs

Uso:
    fmt = SEFormat()
    fmt.save(world, "jogo.se", title="Meu Jogo", scripts=...)
    world = fmt.load("jogo.se")
"""
import json
import os
import zipfile
import shutil

from .utils import VERSION, ENGINE_NAME, ensure_dir

MANIFEST_VERSION = "1.0"


class SEFormat:
    """Leitura e escrita do formato .se."""

    def __init__(self):
        self.last_error = None

    # ------------------------------------------------------------------
    def save(self, world, path: str, title="Meu Jogo", author="Autor",
             mode="2d", scripts=None, extra_files=None):
        """Salva um World completo em um pacote .se.

        scripts: dict {nome_arquivo: conteúdo} ex. {"main.lua": "..."}
        extra_files: lista de caminhos de arquivos p/ assets/
        """
        ensure_dir(os.path.dirname(path) or ".")
        manifest = {
            "engine": ENGINE_NAME,
            "format_version": MANIFEST_VERSION,
            "title": title,
            "author": author,
            "mode": mode,
            "game_version": "0.1.0",
            "scripts": list((scripts or {}).keys()),
        }
        tmpdir = path + ".tmp"
        ensure_dir(os.path.join(tmpdir, "assets"))
        with open(os.path.join(tmpdir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        with open(os.path.join(tmpdir, "world.json"), "w") as f:
            json.dump(world.to_dict(), f, indent=1, ensure_ascii=False)
        for name, content in (scripts or {}).items():
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write(content)
        for fpath in (extra_files or []):
            if os.path.exists(fpath):
                dest = os.path.join(tmpdir, "assets", os.path.basename(fpath))
                shutil.copy2(fpath, dest)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmpdir):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, tmpdir)
                    zf.write(full, rel)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return path

    # ------------------------------------------------------------------
    def load(self, path: str, extract_dir=None):
        """Carrega um pacote .se retornando um World + metadados.
        Se extract_dir fornecido, extrai tudo para lá."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Pacote .se não encontrado: {path}")
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json")) if \
                "manifest.json" in names else {}
            world_json = zf.read("world.json").decode("utf-8") if \
                "world.json" in names else "{}"
            if extract_dir:
                ensure_dir(extract_dir)
                zf.extractall(extract_dir)

        from .world import World
        world = World.from_json(world_json)
        world.flags["title"] = manifest.get("title", "Sem título")
        world.flags["mode"] = manifest.get("mode", "2d")
        world.flags["scripts"] = manifest.get("scripts", [])
        world.flags["package"] = path
        return world

    def list_contents(self, path: str):
        with zipfile.ZipFile(path) as zf:
            return zf.namelist()

    def read_file(self, path: str, name: str) -> str:
        with zipfile.ZipFile(path) as zf:
            return zf.read(name).decode("utf-8")
