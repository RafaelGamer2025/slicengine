"""
SlicEngine — Launcher gráfico (launcher.py).

Inicie com botões, sem precisar de terminal:

    python launcher.py          # janela com botões (usa tkinter, stdlib)
    python launcher.py --demo   # mostra a lista de demos disponíveis

A janela oferece:
- **Iniciar Engine**   → abre o menu de entrada da SlicEngine
- **Editor**           → abre o editor de tile maps diretamente
- **Demos**            → roda as demonstrações (FPS 3D, 3D real,
                         3D raycasting, plataforma 2D, 2D tile map)
- **Shell**            → terminal embutido da engine (pip etc.)
- **Sobre**            → informações e caminhos do projeto

Tudo em subprocessos: a janela do launcher continua viva e você pode
abrir várias coisas. Fecha automaticamente junto se tudo for fechado.

Funciona em Windows, Linux e macOS (tkinter é da biblioteca padrão).
"""
import os
import sys
import subprocess
import threading
import tkinter as tk

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SHELL_SCRIPT = os.path.join(ROOT_DIR, "slicengine", "__main__.py")

# Cada item: (nome do botão, comando, descrição)
ENGINE_COMMANDS = [
    ("Iniciar Engine", [], "Perfis, novos jogos, projetos"),
    ("Menu com GIF", ["--menu"], "Menu clássico com GIF"),
    ("Editor de Mapas", ["--editor"], "Tile maps, pincel, drag & drop"),
    ("Shell (pip)", ["--shell"], "Terminal embutido"),
]

DEMO_COMMANDS = [
    ("Demo FPS 3D", "examples/demo_fps.py", "Estilo Doom: inimigos e tiro"),
    ("Demo 3D Real", "examples/demo_3d_real.py", "Polígonos; mouse p/ olhar"),
    ("Demo 3D Raycast", "examples/demo_3d.py", "3D estilo Doom com raycasting"),
    ("Demo Plataforma 2D", "examples/demo_platform.py", "Plataforma lateral com física real"),
    ("Demo 2D Tile Map", "examples/demo_2d.py", "Mundo 2D com tile maps em camadas"),
]

COLOR_BG = "#0d1117"
COLOR_PANEL = "#161b22"
COLOR_BTN = "#238636"
COLOR_BTN_HOVER = "#2ea043"
COLOR_DEMO_BTN = "#1f6feb"
COLOR_DEMO_HOVER = "#388bfd"
COLOR_TEXT = "#e6edf3"
COLOR_SUB = "#8b949e"
COLOR_DESC = "#c9d1d9"


def _cmd(args):
    """Comando para rodar um alvo da engine em subprocesso."""
    return [sys.executable, "-m", "slicengine"] + list(args)


def _cmd_script(script):
    return [sys.executable, script]


def _run(cmd, label, app):
    """Roda um comando em thread; registra o PID de forma thread-safe."""
    import traceback
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT_DIR,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        app.last_pid = proc.pid
        app.last_error = None
    except Exception as e:
        app.last_pid = None
        app.last_error = f"{label}: {e}"
        print(f"[launcher] erro ao abrir {label}: {traceback.format_exc()}")


class LauncherApp:
    """Janela principal do launcher com botões de texto (canvas)."""

    def __init__(self):
        self.win = tk.Tk()
        self.win.title("SlicEngine Launcher")
        self.win.configure(bg=COLOR_BG)
        self.win.resizable(False, False)

        W, H = 560, 760
        self.win.geometry(f"{W}x{H}+20+20")

        # ----- cabeçalho -----
        self.header = tk.Frame(self.win, bg=COLOR_BG)
        self.header.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(self.header, text="SlicEngine", font=("Segoe UI", 26,
                 "bold"), bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")
        tk.Label(self.header, text="Launcher — escolha o que iniciar",
                 font=("Segoe UI", 11), bg=COLOR_BG, fg=COLOR_SUB
                 ).pack(anchor="w")

        # ----- canvas com botões -----
        self.canvas = tk.Canvas(self.win, bg=COLOR_BG, bd=0,
                                highlightthickness=0, width=W - 32,
                                height=576)
        self.canvas.pack(fill="x", padx=16)
        self.buttons = []
        self.hover_id = None
        self.last_pid = None   # PID do último subprocesso iniciado (thread-safe)
        self.last_error = None
        self.canvas.bind("<Motion>", self._on_motion)

        # botões da engine
        y = self._section("ENGINE", ENGINE_COMMANDS, COLOR_BTN,
                          COLOR_BTN_HOVER, start_y=8)
        # botões das demos
        self._section("DEMOS DE JOGOS", DEMO_COMMANDS, COLOR_DEMO_BTN,
                      COLOR_DEMO_HOVER, start_y=y + 12)

        # ----- rodapé -----
        foot = tk.Frame(self.win, bg=COLOR_BG)
        foot.pack(fill="x", padx=16, pady=(12, 12))
        self.status = tk.Label(foot, text="pronto", font=("Segoe UI", 9),
                               bg=COLOR_BG, fg=COLOR_SUB, anchor="w")
        self.status.pack(fill="x")

        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

    # --------------------------------------------------------------
    def _section(self, title, items, color, hover, start_y=0):
        tk.Label(self.canvas, text=title, font=("Segoe UI", 10, "bold"),
                 bg=COLOR_BG, fg=COLOR_SUB).place(x=2, y=start_y)
        y = start_y + 24
        for name, target, desc in items:
            y = self._button(y, name, desc, target, color, hover)
        return y

    def _button(self, y, name, desc, target, color, hover):
        H = 54
        btn = {
            "id": None, "text": None, "desc": None,
            "y": y, "h": H, "color": color, "hover": hover,
            "target": target, "name": name,
        }
        btn["id"] = self.canvas.create_rectangle(
            0, y, self.canvas.winfo_reqwidth() or 528, y + H,
            fill=color, outline="", tags="btn")
        btn["text"] = self.canvas.create_text(
            16, y + 21, text=name, anchor="w",
            font=("Segoe UI", 13, "bold"), fill="white", tags="btn")
        btn["desc"] = self.canvas.create_text(
            16, y + 42, text=desc, anchor="w",
            font=("Segoe UI", 9), fill=COLOR_DESC, tags="btn")
        # clique
        self.canvas.tag_bind(btn["id"], "<Button-1>",
                             lambda e, b=btn: self._press(b))
        self.canvas.tag_bind(btn["text"], "<Button-1>",
                             lambda e, b=btn: self._press(b))
        self.buttons.append(btn)
        return y + H + 6

    def _on_motion(self, event):
        inside = None
        for b in self.buttons:
            if b["y"] <= event.y < b["y"] + b["h"]:
                inside = b
                break
        if inside is not self.hover_id:
            # restaurar anterior
            if self.hover_id is not None:
                b = self.hover_id
                self.canvas.itemconfig(b["id"], fill=b["color"])
            # destacar novo
            if inside is not None:
                self.canvas.itemconfig(inside["id"], fill=inside["hover"])
                self.canvas.config(cursor="hand2")
            else:
                self.canvas.config(cursor="")
            self.hover_id = inside

    def _press(self, btn):
        target = btn["target"]
        if isinstance(target, str) and target.endswith(".py"):
            cmd = _cmd_script(os.path.join(ROOT_DIR, target))
        elif isinstance(target, str):
            cmd = _cmd([target])
        else:
            # lista de argumentos CLI (pode ser vazia: menu de entrada)
            cmd = _cmd(target)
        threading.Thread(target=_run, args=(cmd, btn["name"], self),
                         daemon=True).start()


    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        print("Demos disponíveis na pasta examples/:")
        for n, t, d in DEMO_COMMANDS:
            print(f"  {n}: {d}")
        print("Engine:")
        for n, t, d in ENGINE_COMMANDS:
            print(f"  {n}: {d}")
        sys.exit(0)
    try:
        import tkinter as tk
    except ImportError:
        print("O launcher gráfico precisa do módulo 'tkinter', que é")
        print("parte da biblioteca padrão do Python. Ele não foi")
        print("encontrado nesta instalação do Python.")
        print()
        print("Como resolver:")
        print("  Windows: reinstale o Python pelo instalador oficial")
        print("           e marque a opção 'tcl/tk and IDLE'.")
        print("  Ubuntu:  sudo apt install python3-tk")
        print("  Fedora:  sudo dnf install python3-tkinter")
        print()
        print("Ou simplesmente rode pelo terminal:")
        print("  python -m slicengine          (menu de entrada)")
        print("  python examples/demo_fps.py   (demo FPS 3D)")
        sys.exit(1)
    LauncherApp().run()
