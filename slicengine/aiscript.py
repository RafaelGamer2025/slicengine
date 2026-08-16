"""
SlicEngine — IA Assistente embutida.

Ajuda o criador a fazer jogos, mods e scripts diretamente na engine.

Dois modos:
1. API_KEY via variável de ambiente SLIC_AI_KEY (OpenAI-compatible)
   -> gera código real com modelo de linguagem
2. Sem chave -> modo local com templates inteligentes (heurísticas +
   banco de receitas) que montam scripts Lua/Python/português prontos

Uso na engine:
    engine.ai("crie um inimigo que persegue o jogador")
    engine.ai_help("como faço um pulo em lua?")
"""
import os
import re
import json
import urllib.request
import urllib.error

from .utils import VERSION

SYSTEM_PROMPT = f"""Você é o assistente da SlicEngine {VERSION}, uma game
engine em Python com suporte a Lua e C. Ela faz jogos 3D raycasting
(estilo Doom) e 2D com tile maps, tem editor com pincel, mods, formato
.se e uma linguagem de script em português.

Quando o usuário pedir um script/mod, responda SEMPRE com um bloco de
código Lua funcional usando a API:
- engine.on_event("update", function(dt) ... end)
- engine.on_event("colidir:moeda", function(dados) ... end)
- engine.on_event("tecla:space", function() ... end)
- engine.get_var/set_var/add_var(nome, valor)
- engine.play_sound("arq.wav"), engine.play_music("arq.ogg"),
  engine.stop_music(), engine.show_text("texto", segundos)
- engine.move_player(dx, dy), engine.spawn_entity("tipo", x, y)
- engine.log(msg)

Se pedir em português, use a sintaxe .sl:
    quando tecla "espaço" for pressionada:
        aumentar 1 no "PONTOS"
Explique brevemente em português e dê o código."""


class AIAssistant:
    def __init__(self, api_base=None, api_key=None, model=None):
        self.api_base = api_base or os.environ.get(
            "SLIC_AI_BASE", "https://api.openai.com/v1")
        self.api_key = api_key or os.environ.get("SLIC_AI_KEY")
        self.model = model or os.environ.get(
            "SLIC_AI_MODEL", "gpt-4o-mini")
        self.history = []

    # ------------------------------------------------------------------
    # Modo online (LLM real)
    # ------------------------------------------------------------------
    def ask_online(self, prompt: str, timeout=30) -> str:
        if not self.api_key:
            return self.ask_local(prompt)
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base.strip('/')}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
            return f"[IA] falha na API ({e}). Usando receitas locais:\n\n" + \
                self.ask_local(prompt)

    # ------------------------------------------------------------------
    # Modo local (receitas inteligentes — funciona sem internet/chave)
    # ------------------------------------------------------------------
    def ask_local(self, prompt: str) -> str:
        p = prompt.lower()

        recipes = [
            (["pulo", "pular", "jump"], self._recipe_pulo),
            (["inimigo", "persegu", "seguir", "ai ", "ia que"], self._recipe_inimigo),
            (["moeda", "ponto", "pontos", "colet"], self._recipe_coleta),
            (["vida", "dano", "morre", "game over"], self._recipe_vida),
            (["som", "música", "musica", "audio", "áudio"], self._recipe_som),
            (["menu", "tela inicial", "gif"], self._recipe_menu),
            (["3d", "raycast", "doom", "parede"], self._recipe_3d),
            (["ajuda", "help", "como", "exemplo", "tutorial"], self._recipe_ajuda),
        ]
        for keys, fn in recipes:
            if any(k in p for k in keys):
                return fn()
        return self._recipe_ajuda()

    def _code(self, title, body):
        return f"### {title}\n\n```lua\n{body}\n```"

    def _recipe_ajuda(self):
        return (
            "Olá! Sou a IA da SlicEngine. Posso criar mods e scripts para "
            "você. Tente pedir, por exemplo:\n"
            "- 'crie um inimigo que persegue o jogador'\n"
            "- 'faça um pulo quando apertar espaço'\n"
            "- 'sistema de pontos com moedas'\n"
            "- 'tocar música de fundo'\n"
            "Respondo com código Lua pronto (ou em português .sl). "
            "Dica: para respostas com IA real, defina a variável de "
            "ambiente SLIC_AI_KEY com sua chave de API.\n\n" +
            self._code("Exemplo: script em português (.sl)", """
quando tecla "espaço" for pressionada:
    aumentar 1 no "PONTOS"
    tocar som "pulo.wav"

quando colidir com "moeda":
    aumentar 10 no "PONTOS"
    tocar som "moeda.wav"
    mostrar texto "Moeda!" por 1 segundo"""))

    def _recipe_pulo(self):
        return self._code("Pulo com gravidade", """
engine.set_var("vy", 0)
engine.set_var("no_chao", true)

function update(dt)
    local vy = engine.get_var("vy")
    if engine.tecla_pressionada("space") and engine.get_var("no_chao") then
        engine.set_var("vy", -9)
        engine.set_var("no_chao", false)
        engine.play_sound("pulo.wav")
    end
    vy = vy + 20 * dt          -- gravidade
    engine.set_var("vy", vy)
    engine.move_player(0, vy * dt)
end
engine.on_event("update", update)""")

    def _recipe_inimigo(self):
        return self._code("Inimigo que persegue o jogador", """
function update(dt)
    local px = engine.get_var("player_x")
    local py = engine.get_var("player_y")
    local ex = engine.get_var("enemy_x")
    local ey = engine.get_var("enemy_y")
    local dx, dy = px - ex, py - ey
    local dist = math.sqrt(dx*dx + dy*dy)
    if dist > 0.01 then
        engine.move_player((dx/dist) * 2 * dt, (dy/dist) * 2 * dt)
    end
end
engine.on_event("update", update)

function ao_tocar(dados)
    engine.show_text("Aii! Dano!", 1)
    engine.play_sound("dano.wav")
end
engine.on_event("colidir:inimigo", ao_tocar)""")

    def _recipe_coleta(self):
        return self._code("Coleta de moedas e pontos", """
engine.set_var("pontos", 0)

function pegar_moeda(dados)
    engine.add_var("pontos", 1)
    engine.play_sound("moeda.wav")
    engine.show_text("+" .. tostring(engine.get_var("pontos")) ..
                     " pontos!", 1)
end
engine.on_event("colidir:moeda", pegar_moeda)""")

    def _recipe_vida(self):
        return self._code("Sistema de vida", """
engine.set_var("vida", 3)

function levar_dano(dados)
    engine.add_var("vida", -1)
    engine.play_sound("dano.wav")
    if engine.get_var("vida") <= 0 then
        engine.show_text("Fim de jogo!", 3)
        engine.stop_game()
    end
end
engine.on_event("colidir:inimigo", levar_dano)""")

    def _recipe_som(self):
        return self._code("Música de fundo e sons", """
engine.play_music("tema.ogg")

function apertar(dados)
    engine.play_sound("tiro.wav")
end
engine.on_event("tecla:space", apertar)""")

    def _recipe_menu(self):
        return (
            "No código Python, use o AssetManager para o menu com GIF:\n\n"
            "```python\n"
            "from slicengine import Engine\n"
            "e = Engine()\n"
            "menu_gif = e.assets.gif('assets/menu_bg.gif', fps=15)\n"
            "e.set_menu(gif=menu_gif, title='MEU JOGO', "
            "start_action=lambda: e.run_game('jogo.se'))\n"
            "e.run()\n"
            "```\n"
            "O GIF roda como fundo animado do menu automaticamente.")

    def _recipe_3d(self):
        return (
            "Para um jogo 3D estilo Doom, crie o mundo com paredes '#' "
            "e rode em modo raycast:\n\n"
            "```python\n"
            "from slicengine import Engine\n"
            "mapa = '''\n"
            "############\n"
            "#P.........#\n"
            "#.###.####.#\n"
            "#...#..#...#\n"
            "#.E.#..#.C.#\n"
            "############\n"
            "'''\n"
            "e = Engine(mode='3d')\n"
            "e.build_from_ascii(mapa)\n"
            "e.run()\n"
            "```\n"
            "Controles: WASD mover, Q/E girar. Coloque sprites em "
            "assets/ para texturas das paredes (wall1.png, wall2.png ...).")
