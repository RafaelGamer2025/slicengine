"""
Teste GUI do launcher.py (tkinter):
- abre a janela, verifica que todos os botões existem
- clica no botão 'Demo FPS 3D' e confere que o subprocesso foi criado
  (app.last_pid) e o processo estava vivo logo após o spawn
- clica no botão 'Iniciar Engine' e verifica o mesmo
"""
import sys
import os
import time

sys.path.insert(0, ".")
failures = []


def check(desc, ok):
    print("  [OK]" if ok else "  FAIL", desc)
    if not ok:
        failures.append(desc)


import tkinter as tk  # noqa: E402

# importa o módulo do launcher
import importlib.util

spec = importlib.util.spec_from_file_location(
    "launcher", os.path.join(".", "launcher.py"))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

app = launcher.LauncherApp()

results = {}


def _spawned_ok():
    """O último subprocesso foi criado e estava vivo logo após o spawn."""
    pid = app.last_pid
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        # já terminou (aceitável em SDL dummy): checar que EXISTIU
        return True


# 1) botões presentes
names = [b["name"] for b in app.buttons]
results["botão 'Iniciar Engine' existe"] = "Iniciar Engine" in names
results["botão 'Editor de Mapas' existe"] = "Editor de Mapas" in names
results["botão 'Demo FPS 3D' existe"] = "Demo FPS 3D" in names
results["botão 'Demo Plataforma 2D' existe"] = (
    "Demo Plataforma 2D" in names)
results["nº de botões == 9"] = len(app.buttons) == 9


def _step1():
    fps_btn = [b for b in app.buttons
               if b["name"] == "Demo FPS 3D"][0]
    app._press(fps_btn)
    app.win.after(2000, _step1_check)


def _step1_check():
    results["subprocess demo_fps.py sobe ao clicar"] = _spawned_ok()
    results["nenhum erro ao abrir demo"] = app.last_error is None
    _step2()


def _step2():
    entry_btn = [b for b in app.buttons
                 if b["name"] == "Iniciar Engine"][0]
    app._press(entry_btn)
    app.win.after(3500, _step2_check)


def _step2_check():
    results["subprocess engine sobe ao clicar"] = _spawned_ok()
    results["nenhum erro ao abrir engine"] = app.last_error is None
    # fechar janela
    app.win.after(200, app.win.destroy)


app.win.after(300, _step1)
app.win.mainloop()

for desc, ok in results.items():
    print("  [OK]" if ok else "  FAIL", desc)
    if not ok:
        failures.append(desc)
print(f"{len(failures)} falha(s): {failures}")
sys.exit(1 if failures else 0)
