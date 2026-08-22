"""
SlicEngine — MODO LOCAL.

- ScriptRunner: roda scripts na hora (Lua .lua, Python .py, PT .sl)
- Shell: terminal embutido que executa comandos de sistema (pip, etc.)
  dentro da engine (com whitelist de segurança).

Uso:
    runner = ScriptRunner(engine)
    runner.run_file("script.lua")        # roda agora
    out = shell.run("pip install requests")  # terminal embutido
"""
import os
import io
import sys
import subprocess
import contextlib

try:
    import lupa
except (ModuleNotFoundError, ImportError):
    lupa = None

from .lua_api import build_lua_api
from .ptscript import PTScript


class ScriptRunner:
    """Executa scripts Lua, Python e .sl (português) no contexto da engine."""

    def __init__(self, engine):
        self.engine = engine
        self._lua_rt = None
        self.log_lines: list[str] = []

    def _ensure_lua(self):
        if lupa is None:
            raise RuntimeError(
                "o módulo 'lupa' não está instalado. Instale com "
                "'pip install lupa' para rodar scripts Lua")
        if self._lua_rt is None:
            self._lua_rt = build_lua_api(self.engine, lupa)
        return self._lua_rt

    def run_string(self, source: str, lang="auto") -> str:
        """Rodar código como texto. lang: 'lua', 'python', 'sl', 'auto'."""
        self.log_lines.clear()
        lang = lang or "auto"
        if lang == "auto":
            s = source.strip()
            if s.startswith("--") or "function " in s or "end" in s.splitlines()[-1]:
                lang = "lua"
            elif s.startswith("quando") or s.startswith("sempre"):
                lang = "sl"
            else:
                lang = "python"
        try:
            if lang == "lua":
                self._ensure_lua().execute(source)
            elif lang == "sl":
                PTScript(source).register(self.engine)
            else:
                ns = {"engine": self.engine,
                      "print": lambda *a: self.log_lines.append(
                          " ".join(map(str, a)))}
                exec(compile(source, "<local>", "exec"), ns)
            return "OK"
        except Exception as e:
            return f"ERRO: {e}"

    def run_file(self, path: str, lang="auto") -> str:
        if not os.path.exists(path):
            return f"ERRO: arquivo não existe: {path}"
        with open(path, encoding="utf-8") as f:
            src = f.read()
        ext = os.path.splitext(path)[1]
        if lang == "auto":
            lang = {".lua": "lua", ".py": "python",
                    ".sl": "sl"}.get(ext, "auto")
        return self.run_string(src, lang)


class Shell:
    """Terminal embutido — executa comandos de sistema de forma segura."""

    ALLOWED_PREFIX = ("pip", "python", "python3", "dir", "ls", "cd",
                      "echo", "type", "cat", "where", "which", "help",
                      "man", "git", "mkdir", "copy", "del", "rm", "cp",
                      "mv", "ren", "set", "env", "ver", "date", "time",
                      "cls", "clear", "whoami", "hostname", "find",
                      "pip3", "uv", "poetry", "slicengine", "python -m",
                      "python3 -m")
    BLOCKED = ("rm -rf /", "format", "mkfs", "shutdown", "reboot",
               "sudo rm", "del /", "rmdir /s")

    def __init__(self, workdir=".", record_db=None, profile_id=0):
        self.workdir = os.path.abspath(workdir)
        self.record_db = record_db
        self.profile_id = profile_id
        self.history: list[tuple[str, str]] = []

    def _allowed(self, cmd: str) -> bool:
        c = cmd.strip().lower()
        for b in self.BLOCKED:
            if b in c:
                return False
        head = c.split()[0] if c.split() else ""
        if any(c.startswith(p) for p in self.ALLOWED_PREFIX):
            return True
        # aceitar caminhos explícitos tipo /usr/bin/python
        return False

    def run(self, command: str, timeout=120) -> str:
        command = command.strip()
        if not command:
            return ""
        if not self._allowed(command):
            out = ("Comando bloqueado por segurança. Permitidos: pip, "
                   "python, git, ls/dir, echo, mkdir, rm/cp/mv, etc.")
            self.history.append((command, out))
            return out
        old_cwd = os.getcwd()
        os.chdir(self.workdir)
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self.workdir, env=os.environ.copy())
            out = (proc.stdout or "") + (proc.stderr or "")
            if not out.strip():
                out = "(sem saída)"
            self.history.append((command, out[-3000:]))
            if self.record_db:
                self.record_db.record_command(
                    self.profile_id, command, out[-3000:])
            return out
        except subprocess.TimeoutExpired:
            return "ERRO: tempo esgotado (timeout)"
        except Exception as e:
            return f"ERRO: {e}"
        finally:
            os.chdir(old_cwd)
