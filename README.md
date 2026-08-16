# SlicEngine

**SlicEngine** é uma game engine brasileira feita do zero em **Python**, com suporte a **Lua** e **C**, para criar jogos **3D raycasting estilo Doom** e jogos **2D com tile maps**. Ela cria sua própria extensão de projeto, o **`.se`** (formato SlicEngine), e permite escrever scripts na sua própria linguagem de script em português, totalmente compatível com Lua e Python.

## Recursos

| Recurso | Descrição |
|---|---|
| 3D Raycasting | Renderizador estilo Doom: DDA, paredes texturizadas, sprites billboard, fog, z-buffer |
| 2D Tile Maps | Mapas em camadas, tile size configurável, importação de tilesets |
| Editor com Pincel | Editor integrado: pincel, borracha e preenchimento para pintar tiles |
| Scripting em Português | Linguagem própria `.sl`: `quando tecla "espaço" for pressionada: ...` |
| Lua | Mods Lua completos com API da engine (`engine.on_event`, `engine.set_var`...) |
| C (nativo) | Plugins `.so/.dll/.dylib` carregados via ctypes com interface padrão |
| Python | Mods Python com função `register(engine)` |
| Formato `.se` | Pacotes zipados com manifest, mundo, scripts embarcados e assets |
| Assets | Sprites (PNG/JPG/GIF/BMP), sons (WAV/OGG), músicas (MP3/OGG), GIFs animados |
| Menu com GIF | Menu inicial com GIF animado de fundo |
| IA Assistente | IA embutida que ajuda a criar scripts e mapas (modo online ou local com receitas) |
| Modo Local | Executor de scripts na hora + terminal embutido (pip, etc.) |
| Perfis em DB | Banco SQLite com perfis, projetos e saves |
| Hierarquia | Árvore de nós com prioridade para assets, scripts, comandos e câmeras |
| Mods/Plugins | Pastas `mods/` e `plugins/` escaneadas automaticamente |

## Instalação

```bash
git clone <url-do-repositorio>
cd slicengine
pip install pygame lupa pillow numpy
```

## Executando

```bash
python -m slicengine                  # menu da engine (com GIF animado)
python -m slicengine --editor         # editor de tile maps com pincel
python -m slicengine --run jogo.se    # rodar um pacote .se
python -m slicengine --ai "pergunta"  # perguntar à IA assistente
python -m slicengine --shell          # shell interativo (pip etc.)
python examples/demo_3d.py            # demo 3D raycasting
python examples/demo_2d.py            # demo 2D tile map
```

## Demonstração Visual

**Menu com GIF animado:**

![Menu da SlicEngine](tests/shots/menu_real.png)

**3D Raycasting estilo Doom:**

![3D Raycasting](tests/shots/demo_3d.png)

## Estrutura do Projeto

```
slicengine/
├── slicengine/        # código da engine
│   ├── core.py        # Engine, eventos, menu com GIF, modos
│   ├── raycaster.py   # renderizador 3D raycasting
│   ├── world.py       # mundo, tile maps e entidades
│   ├── editor.py      # editor de tile maps com pincel
│   ├── ptscript.py    # linguagem de script em português (.sl)
│   ├── lua_api.py     # API da engine para Lua
│   ├── modsystem.py   # sistema de mods/plugins (Lua, Python, C, .sl)
│   ├── seformat.py    # leitura/escrita do formato .se
│   ├── assets.py      # gerenciador de sprites, sons, músicas e GIFs
│   ├── hierarchy.py   # hierarquia de nós (assets, scripts, comandos, câmeras)
│   ├── aiscript.py    # IA assistente embutida
│   ├── local.py       # executor local de scripts e terminal embutido
│   └── profile_db.py  # perfis e projetos em SQLite
├── examples/          # demos (demo_3d.py, demo_2d.py, demo_game.se)
├── mods/              # mods de exemplo (demo.lua, exemplo.sl)
├── plugins/           # plugin C de exemplo (noise.c + wrapper noise.py)
├── assets/            # sprites e texturas de demonstração
├── tests/             # testes automatizados
└── tools/             # geradores (assets, pacote .se de demo)
```

## Linguagem de Script em Português (.sl)

Escreva regras no estilo "quando X acontecer, faça Y":

```
quando iniciar:
    definir "vida" como 100
    mostrar texto "Bem-vindo!" por 3

quando tecla "espaço" for pressionada:
    aumentar 1 no "JOGO"
    tocar som "pulo.wav"

quando moeda_pegada:
    aumentar 10 no "moedas"

quando vida chegar a 0:
    mostrar texto "Game Over!" por 5
    parar jogo
```

As mesmas regras podem ser escritas em **Lua** (`mods/`) ou **Python** (`mods/` com `register(engine)`), usando a mesma API de eventos: `iniciar`, `quadro`, `moeda_pegada`, `tecla_pressionada`, `vida`, etc.

## Mod em Lua

```lua
engine.on_event("iniciar", function(api)
    engine.set_var("pontos", 0)
    api.mostrar_texto("Mod Lua carregado!", 3)
end)

engine.on_event("moeda_pegada", function(api)
    engine.set_var("pontos", engine.get_var("pontos") + 10)
    api.tocar_som("moeda.wav")
end)
```

## Plugin em C

Compile com `gcc -shared -fPIC -O2 noise.c -o slic_noise.so` e coloque na pasta `plugins/`. A engine chama `se_plugin_register()` e `se_plugin_name()` automaticamente. O wrapper Python (`plugins/noise.py`) expõe `engine.noise_next()`, `engine.noise_fill(n)` e `engine.noise_seed(s)` para qualquer script.

## Formato .se

Um pacote `.se` é um arquivo zip com `manifest.json`, `world.json`, scripts embarcados e uma pasta `assets/`. Crie com `python tools/gen_demo_se.py` ou pelo editor (Salvar como `.se`). Execute com `python -m slicengine --run jogo.se`.

## Controles

| Tecla | Ação |
|---|---|
| WASD / Setas | Mover |
| Mouse / ← → | Olhar (modo 3D) |
| Espaço | Evento personalizado (configurável nos scripts) |
| E | Interagir (modo editor: testar mapa) |

## Licença

MIT — use, modifique e distribua livremente.
