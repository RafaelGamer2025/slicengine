"""
SlicEngine — Telas de entrada da engine.

Entrada completa em camadas:

    Menu Principal
        [Jogar] ........... lista de projetos do perfil -> abrir/tentar
        [Novo Jogo] ....... cria projeto novo (nome + modo 2D/3D, gravado
                            no banco do perfil) -> abre editor
        [Perfis] .......... lista perfis do SQLite, criar perfil,
                            selecionar, ver stats (projetos/saves)
        [Demos] ........... atalhos para as demos
        [Sair]

Nada do núcleo (core.py) é alterado: esta camada usa apenas a API
pública da Engine. As telas são desenhadas por cima do loop com
``state = "menuscreen"`` e retornam a ação escolhida por callback.
"""
import os
import time
import pygame
from . import utils


FONT_PATHS = ("dejavusans", "freesansbold", None)


def _sysfont(size, bold=False):
    for name in FONT_PATHS:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            continue
    return pygame.font.Font(None, size * 2)


# Cores modernas e profissionais
BG = (18, 18, 28)
BG_DARK = (12, 12, 18)
ACCENT = (0, 180, 255)      # Azul Neon
ACCENT_LIGHT = (80, 210, 255)
TEXT = (240, 240, 245)
DIM = (120, 125, 140)
BTN_BG = (35, 35, 50)
BTN_HOVER = (50, 50, 75)
BTN_BORDER = (60, 65, 85)
ITEM_BG = (28, 28, 40)
DANGER = (255, 80, 80)
SUCCESS = (80, 255, 150)


class MenuScreen:
    """Gerencia as telas de entrada. Uso:

        ms = MenuScreen(engine)
        engine.state = "menuscreen"
    """

    MAIN = "main"
    NEW = "new"
    PROJECTS = "projects"
    PROFILES = "profiles"
    DEMOS = "demos"
    PROFILE_NEW = "profile_new"

    def __init__(self, engine):
        self.engine = engine
        self.screen = "main"
        self.hover = -1
        self.sel = 0
        self.input_text = ""
        self.input_focus = False
        self.new_mode = "2d"
        self.message = ""
        self.message_time = 0.0
        self._profiles_cache = None
        self._avatar_cache = {}

    # ------------------------------------------------------------------
    def _font(self, size, bold=False):
        return _sysfont(size, bold)

    def _toast(self, text, t=2.0):
        self.message = text
        self.message_time = self.engine.elapsed + t

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def _profiles(self):
        return self.engine.db.list_profiles()

    def _projects(self):
        return self.engine.db.list_projects(self.engine.profile_id)

    def _avatar(self, name):
        """Desenha um avatar colorido a partir do nome (hash simples)."""
        h = sum(ord(c) for c in name) or 1
        color = (70 + (h * 17) % 140, 90 + (h * 31) % 120,
                 120 + (h * 43) % 90)
        key = name[:2].upper()
        if key in self._avatar_cache:
            return self._avatar_cache[key]
        s = pygame.Surface((40, 40))
        s.fill(color)
        f = self._font(20, True)
        t = f.render(key, True, (255, 255, 255))
        s.blit(t, (20 - t.get_width() // 2, 20 - t.get_height() // 2))
        self._avatar_cache[key] = s
        return s

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def go(self, screen):
        self.screen = screen
        self.hover = -1
        self.sel = 0
        self.input_text = ""
        self.input_focus = screen == self.PROFILE_NEW

    # ------------------------------------------------------------------
    def open_new_game(self):
        """Cria um projeto novo e abre o editor."""
        name = self.input_text.strip()
        if not name:
            self._toast("Digite o nome do jogo!")
            return
        pid = self.engine.profile_id
        self.engine.db.add_project(pid, name, mode=self.new_mode)
        self.engine.db.record_command(pid, f"projeto criado: {name}",
                                      "via menu")
        # limpa mundo atual e abre o editor
        from .world import World
        self.engine.world = World()
        self.engine.mode = self.new_mode
        self.engine.editor = None
        self.engine.state = "editor"
        self.engine.title = name
        pygame.display.set_caption(f"{name} — SlicEngine "
                                   f"{self.engine.title}")

    def open_project(self, project):
        path = project.get("path")
        if path and os.path.exists(path):
            try:
                self.engine.load_package(path)
                self.engine.state = "game"
                return
            except Exception as e:
                self._toast(f"Erro ao abrir: {e}")
        # sem arquivo: cria um mundo vazio com o modo do projeto
        from .world import World
        self.engine.world = World()
        self.engine.mode = project.get("mode", "2d")
        self.engine.editor = None
        self.engine.state = "editor"
        self._toast("Projeto sem arquivo — editor aberto")

    def select_profile(self, profile):
        self.engine.profile_name = profile["name"]
        self.engine.profile_id = profile["id"]
        # preferências do perfil
        st = profile.get("settings", {})
        self.engine.title = st.get("editor_title", "SlicEngine")
        self._toast(f"Perfil: {profile['name']}")

    def create_profile(self):
        name = self.input_text.strip()
        if not name:
            self._toast("Digite o nome do perfil!")
            return
        pid = self.engine.db.create_profile(name)
        self.select_profile(
            {"name": name, "id": pid, "settings": {}})
        self.go(self.MAIN)

    # ------------------------------------------------------------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.screen == self.MAIN:
                    self.engine.running = False
                else:
                    self.go(self.MAIN)
                return
            if self.screen == self.PROFILE_NEW and self.input_focus:
                if ev.key == pygame.K_RETURN:
                    self.create_profile()
                elif ev.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif ev.unicode and ev.unicode.isprintable() and \
                        len(self.input_text) < 24:
                    self.input_text += ev.unicode
                return
            if self.screen == self.NEW:
                if ev.key == pygame.K_1:
                    self.new_mode = "2d"
                elif ev.key == pygame.K_2:
                    self.new_mode = "3d"
                elif ev.key == pygame.K_RETURN:
                    self.open_new_game()
                elif ev.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif ev.unicode and ev.unicode.isprintable() and \
                        len(self.input_text) < 30:
                    self.input_text += ev.unicode
                return
            if self.screen == self.MAIN:
                main = self._main_items()
                if ev.key == pygame.K_1:
                    self._choose_main(0)
                elif ev.key == pygame.K_2 and len(main) > 1:
                    self._choose_main(1)
                elif ev.key == pygame.K_3 and len(main) > 2:
                    self._choose_main(2)
                elif ev.key == pygame.K_4 and len(main) > 3:
                    self._choose_main(3)
                return
            if self.screen == self.PROFILES:
                profs = self._profiles()
                for i in range(min(9, len(profs))):
                    if ev.key == getattr(pygame, f"K_{i + 1}"):
                        self.select_profile(profs[i])
                        return
                if ev.key == pygame.K_n:
                    self.go(self.PROFILE_NEW)
                return
            if self.screen == self.PROJECTS:
                projs = self._projects()
                for i in range(min(9, len(projs))):
                    if ev.key == getattr(pygame, f"K_{i + 1}"):
                        self.open_project(projs[i])
                        return
                return
            if self.screen == self.DEMOS:
                demos = self._demo_items()
                for i in range(len(demos)):
                    if ev.key == getattr(pygame, f"K_{i + 1}"):
                        demos[i][1]()
                        return
                return
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._handle_click(ev.pos)

    def _choose_main(self, index):
        if index == 0:
            self.go(self.PROJECTS)
        elif index == 1:
            self.go(self.NEW)
        elif index == 2:
            self.go(self.PROFILES)
        elif index == 3:
            self.go(self.DEMOS)

    def _handle_click(self, pos):
        mx, my = pos
        items = self._visible_items()
        for i, rect in enumerate(items):
            if rect.collidepoint(mx, my):
                if self.screen == self.MAIN:
                    self._choose_main(i)
                elif self.screen == self.NEW:
                    self.open_new_game()
                elif self.screen == self.PROFILE_NEW:
                    self.create_profile()
                elif self.screen == self.PROJECTS:
                    self.open_project(self._projects()[i])
                elif self.screen == self.PROFILES:
                    self.select_profile(self._profiles()[i])
                elif self.screen == self.DEMOS:
                    self._demo_items()[i][1]()
                return
        # campo de texto
        if self.screen in (self.NEW, self.PROFILE_NEW):
            if self._input_rect().collidepoint(mx, my):
                self.input_focus = True
            else:
                self.input_focus = False

    # ------------------------------------------------------------------
    # Itens de cada tela
    # ------------------------------------------------------------------
    def _main_items(self):
        return ["Jogos / Projetos", "Novo Jogo", "Perfis", "Demos"]

    def _demo_items(self):
        import sys
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        examples = os.path.join(base, "examples")
        def _run(name):
            def _do():
                import subprocess
                pygame.quit()
                subprocess.Popen([sys.executable,
                                  os.path.join(examples, name)])
                self.engine.running = False
            return _do
        return [
            ("Demo FPS 3D (estilo Doom)", _run("demo_fps.py")),
            ("Demo 3D raycasting", _run("demo_3d.py")),
            ("Demo 3D real (polígonos)", _run("demo_3d_real.py")),
            ("Demo 2D plataforma", _run("demo_platform.py")),
            ("Demo 2D tile map", _run("demo_2d.py")),
        ]

    def _visible_items(self):
        sw, sh = self.screen_size()
        # rects verticais dos botões principais
        items = self._main_items() if self.screen == self.MAIN \
            else self._projects() if self.screen == self.PROJECTS \
            else self._profiles() if self.screen == self.PROFILES \
            else self._demo_items() if self.screen == self.DEMOS \
            else []
        y0 = sh // 2 - 20
        rects = []
        for i in range(len(items)):
            rects.append(pygame.Rect(sw // 2 - 160, y0 + i * 48, 320, 40))
        return rects

    def _input_rect(self):
        sw, sh = self.screen_size()
        return pygame.Rect(sw // 2 - 160, sh // 2 + 120, 320, 36)

    def screen_size(self):
        return self.engine.screen.get_size()

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def screen_size(self):
        return self.engine.screen.get_size()

    def _draw_gradient_bg(self, surface):
        sw, sh = surface.get_size()
        for y in range(sh):
            # Gradiente vertical sutil
            r = BG[0] - int(6 * y / sh)
            g = BG[1] - int(6 * y / sh)
            b = BG[2] - int(10 * y / sh)
            pygame.draw.line(surface, (max(0, r), max(0, g), max(0, b)), (0, y), (sw, y))

    def draw(self):
        sw, sh = self.screen_size()
        s = self.engine.screen
        self._draw_gradient_bg(s)
        
        # Desenhar partículas de fundo ou grid sutil
        for i in range(0, sw, 40):
            pygame.draw.line(s, (25, 25, 35), (i, 0), (i, sh))
        for i in range(0, sh, 40):
            pygame.draw.line(s, (25, 25, 35), (0, i), (sw, i))

        big = self._font(52, True)
        small = self._font(20)
        tiny = self._font(14)
        header_font = self._font(28, True)

        if self.screen == self.MAIN:
            # Efeito de brilho no título
            t_glow = big.render("SLICENGINE", True, (0, 100, 200))
            s.blit(t_glow, (sw // 2 - t_glow.get_width() // 2 + 2, 92))
            t = big.render("SLICENGINE", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 90))
            
            sub = small.render(f"PERFIL ATIVO: {self.engine.profile_name.upper()}",
                               True, DIM)
            s.blit(sub, (sw // 2 - sub.get_width() // 2, 160))
            
            pygame.draw.line(s, ACCENT, (sw // 2 - 100, 190), (sw // 2 + 100, 190), 2)

            for i, it in enumerate(self._main_items()):
                r = self._visible_items()[i]
                mpos = pygame.mouse.get_pos()
                is_hover = r.collidepoint(mpos)
                
                col = BTN_HOVER if is_hover else BTN_BG
                border_col = ACCENT if is_hover else BTN_BORDER
                
                # Sombra/Brilho externa
                if is_hover:
                    glow_r = r.inflate(4, 4)
                    pygame.draw.rect(s, (0, 100, 200), glow_r, border_radius=8, width=1)
                
                pygame.draw.rect(s, col, r, border_radius=6)
                pygame.draw.rect(s, border_col, r, border_radius=6, width=2)
                
                t = small.render(f"{i + 1}. {it.upper()}", True, TEXT if not is_hover else ACCENT_LIGHT)
                s.blit(t, (r.x + 20, r.y + (r.height - t.get_height()) // 2))
                
            ver = tiny.render(f"ENGINE VERSION {utils.VERSION}  |  "
                              f"ESC PARA SAIR", True, DIM)
            s.blit(ver, (20, sh - 30))
        elif self.screen == self.NEW:
            t = header_font.render("CRIAR NOVO PROJETO", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 80))
            
            lbl = small.render("NOME DO JOGO:", True, DIM)
            s.blit(lbl, (sw // 2 - 160, 150))
            
            ir = self._input_rect()
            pygame.draw.rect(s, BTN_HOVER if self.input_focus else BTN_BG, ir, border_radius=6)
            pygame.draw.rect(s, ACCENT if self.input_focus else BTN_BORDER, ir, border_radius=6, width=2)
            
            f = small.render(self.input_text + ("|" if self.input_focus and (time.time() % 1 > 0.5) else ""), True, TEXT)
            s.blit(f, (ir.x + 15, ir.y + (ir.height - f.get_height()) // 2))
            
            # Seleção de Modo
            m_y = 260
            s.blit(small.render("MODO DE RENDERIZAÇÃO:", True, DIM), (sw // 2 - 160, m_y))
            
            r2d = pygame.Rect(sw // 2 - 160, m_y + 30, 150, 40)
            r3d = pygame.Rect(sw // 2 + 10, m_y + 30, 150, 40)
            
            for r, mode, lbl_txt, key in [(r2d, "2d", "1. 2D TILEMAP", "1"), (r3d, "3d", "2. 3D RAYCAST", "2")]:
                is_sel = self.new_mode == mode
                is_hover = r.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(s, BTN_HOVER if is_hover or is_sel else BTN_BG, r, border_radius=6)
                pygame.draw.rect(s, ACCENT if is_sel else BTN_BORDER, r, border_radius=6, width=2 if is_sel else 1)
                txt = small.render(lbl_txt, True, TEXT if is_sel else DIM)
                s.blit(txt, (r.x + (r.width - txt.get_width()) // 2, r.y + (r.height - txt.get_height()) // 2))

            btn = pygame.Rect(sw // 2 - 160, sh // 2 + 100, 320, 50)
            is_hover = btn.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(s, SUCCESS if is_hover else BTN_BG, btn, border_radius=8)
            t = small.render("CRIAR E ABRIR EDITOR", True, BG_DARK if is_hover else SUCCESS)
            s.blit(t, (btn.x + (btn.width - t.get_width()) // 2, btn.y + (btn.height - t.get_height()) // 2))
            
            hint = tiny.render("ESC PARA VOLTAR", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))
        elif self.screen == self.PROFILE_NEW:
            t = header_font.render("CRIAR NOVO PERFIL", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 80))
            lbl = small.render("NOME DO PERFIL:", True, DIM)
            s.blit(lbl, (sw // 2 - 160, 160))
            ir = self._input_rect()
            pygame.draw.rect(s, BTN_HOVER if self.input_focus else BTN_BG, ir, border_radius=6)
            pygame.draw.rect(s, ACCENT if self.input_focus else BTN_BORDER, ir, border_radius=6, width=2)
            f = small.render(self.input_text + ("|" if self.input_focus and (time.time() % 1 > 0.5) else ""), True, TEXT)
            s.blit(f, (ir.x + 15, ir.y + (ir.height - f.get_height()) // 2))
            
            btn = pygame.Rect(sw // 2 - 160, sh // 2 + 40, 320, 50)
            is_hover = btn.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(s, SUCCESS if is_hover else BTN_BG, btn, border_radius=8)
            t = small.render("CRIAR PERFIL (ENTER)", True, BG_DARK if is_hover else SUCCESS)
            s.blit(t, (btn.x + (btn.width - t.get_width()) // 2, btn.y + (btn.height - t.get_height()) // 2))
            
            hint = tiny.render("ESC PARA CANCELAR", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))
        elif self.screen in (self.PROJECTS, self.PROFILES):
            title = "MEUS PROJETOS" if self.screen == self.PROJECTS else "GERENCIAR PERFIS"
            t = header_font.render(title, True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 80))
            
            items = (self._projects() if self.screen == self.PROJECTS else self._profiles())
            if not items:
                none_ = small.render("NADA POR AQUI AINDA — CRIE UM NOVO!", True, DIM)
                s.blit(none_, (sw // 2 - none_.get_width() // 2, sh // 2))
            
            y = 160
            for i, it in enumerate(items):
                r = pygame.Rect(sw // 2 - 220, y, 440, 50)
                is_hover = r.collidepoint(pygame.mouse.get_pos())
                is_active = self.screen == self.PROFILES and it["id"] == self.engine.profile_id
                
                pygame.draw.rect(s, BTN_HOVER if is_hover else BTN_BG, r, border_radius=8)
                pygame.draw.rect(s, ACCENT if is_active or is_hover else BTN_BORDER, r, border_radius=8, width=2 if is_active else 1)
                
                if self.screen == self.PROFILES:
                    av = self._avatar(it["name"])
                    s.blit(av, (r.x + 10, r.y + (r.height - av.get_height()) // 2))
                    nm = small.render(f"{i + 1}. {it['name'].upper()}", True, ACCENT if is_active else TEXT)
                    s.blit(nm, (r.x + 60, r.y + (r.height - nm.get_height()) // 2))
                    
                    if is_active:
                        tag = tiny.render("ATIVO", True, BG_DARK)
                        tag_r = pygame.Rect(r.right - 70, r.y + 15, 60, 20)
                        pygame.draw.rect(s, ACCENT, tag_r, border_radius=4)
                        s.blit(tag, (tag_r.x + (tag_r.width - tag.get_width()) // 2, tag_r.y + 3))
                else:
                    nm = small.render(f"{i + 1}. {it['title'].upper()}", True, TEXT if not is_hover else ACCENT_LIGHT)
                    s.blit(nm, (r.x + 20, r.y + (r.height - nm.get_height()) // 2))
                    mode = tiny.render(it.get("mode", "2D").upper(), True, DIM)
                    s.blit(mode, (r.right - mode.get_width() - 20, r.y + (r.height - mode.get_height()) // 2))
                y += 60
            
            if self.screen == self.PROFILES:
                btn = pygame.Rect(sw // 2 - 220, sh - 110, 440, 46)
                is_hover = btn.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(s, BTN_HOVER if is_hover else BTN_BG, btn, border_radius=8)
                pygame.draw.rect(s, ACCENT if is_hover else BTN_BORDER, btn, border_radius=8, width=2)
                t = small.render("+ CRIAR NOVO PERFIL (N)", True, TEXT if not is_hover else ACCENT_LIGHT)
                s.blit(t, (btn.x + (btn.width - t.get_width()) // 2, btn.y + (btn.height - t.get_height()) // 2))
                
            hint = tiny.render("ESC PARA VOLTAR", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))
        elif self.screen == self.DEMOS:
            t = header_font.render("DEMONSTRAÇÕES", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 80))
            y = 160
            for i, (nome, _) in enumerate(self._demo_items()):
                r = pygame.Rect(sw // 2 - 220, y, 440, 50)
                is_hover = r.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(s, BTN_HOVER if is_hover else BTN_BG, r, border_radius=8)
                pygame.draw.rect(s, ACCENT if is_hover else BTN_BORDER, r, border_radius=8, width=1)
                nm = small.render(f"{i + 1}. {nome.upper()}", True, TEXT if not is_hover else ACCENT_LIGHT)
                s.blit(nm, (r.x + 20, r.y + (r.height - nm.get_height()) // 2))
                y += 60
            hint = tiny.render("ESC PARA VOLTAR", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))

        # toast (notificações)
        if self.message and self.engine.elapsed > self.message_time:
            self.message = ""
        if self.message:
            f = self._font(22, True)
            t = f.render(self.message.upper(), True, TEXT)
            tw, th = t.get_width(), t.get_height()
            tr = pygame.Rect(sw // 2 - tw // 2 - 20, 20, tw + 40, th + 20)
            pygame.draw.rect(s, BTN_HOVER, tr, border_radius=10)
            pygame.draw.rect(s, ACCENT, tr, border_radius=10, width=2)
            s.blit(t, (sw // 2 - tw // 2, 30))

    # ------------------------------------------------------------------
    def update(self, dt):
        # refresh do cursor piscando
        pass
