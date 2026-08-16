# SlicEngine — Arquitetura

## Visão Geral
SlicEngine é uma game engine em **Python** (com suporte a **Lua** via lupa e **C** via ctypes) para criar:
- Jogos **3D raycasting** estilo Doom (pseudopolígono 2.5D)
- Jogos **2D com tile maps**
- Sistema de **plugins/mods** (scripts Lua/Python/C carregáveis)
- Formato de arquivo próprio **.se** (SlicEngine package, ZIP binário)
- **Editor de mapas** embutido com pincel (brush), camadas e seleção de tiles
- **Importação de assets**: sprites (PNG/JPG/GIF), sons (WAV/OGG/MP3), música (streaming)
- **Menu com GIF** (animação de fundo)
- **IA assistente** embutida que ajuda a gerar código de mods e scripts

## Stack
- Runtime: CPython 3.11+
- Render: Pygame/SDL2
- Scripting: Lua 5.4 (lupa) + Python embutido
- C nativo: carregado via ctypes como .so/.dll (plugin nativo)
- Assets: pygame.image, pygame.mixer, Pillow para GIF

## Estrutura de Diretórios
```
slicengine/
├── slicengine/            # pacote da engine
│   ├── __init__.py        # API pública
│   ├── core.py            # Engine (loop, eventos, estado)
│   ├── raycaster.py       # Renderizador 3D raycasting (Doom-style)
│   ├── world.py           # Mundo 2D/3D, mapas, entidades
│   ├── editor.py          # Editor de tile maps (pincel, camadas)
│   ├── lua_api.py         # Expor API da engine para Lua (lupa)
│   ├── modsystem.py       # Carregador de mods/plugins (.se, .lua, .py, .so)
│   ├── seformat.py        # Formato .se (leitura/escrita)
│   ├── assets.py          # Gerenciador de assets (sprite, audio, gif, music)
│   ├── gifplayer.py       # Player de GIF para menus
│   ├── aiscript.py        # IA assistente (gerador de código via LLM)
│   └── utils.py
├── examples/
│   ├── demo_3d/           # Demo Doom-style
│   ├── demo_2d/           # Demo 2D tile map
│   └── mods/              # Exemplos de mods Lua
├── plugins/               # Plugins nativos (C) — exemplos fonte
│   └── noise.c
└── README.md
```

## Modo de Uso
1. **Editor**: `python -m slicengine --editor` → abre editor com pincel para pintar tile maps, salvar em `.se`
2. **Jogar**: `python -m slicengine --run game.se` → roda um pacote .se
3. **Código**: `from slicengine import Engine; ...` → usa a engine como biblioteca

## Formato .se
Arquivo ZIP com extensão `.se` contendo:
- `manifest.json` — metadados do jogo/mod
- `map.json` — tile map / mapa raycaster
- `main.lua` ou `main.py` — script principal
- `assets/` — sprites, sons, músicas, gifs

## Raycaster (Doom-style)
- Mapa de grade 2D, paredes com alturas
- DDA raycasting com texturização por colunas
- Sprites billboarding (inimigos/itens)
- Floor/ceiling shading simples

## API Lua (exemplos)
```lua
engine.window(title, 800, 600)
map = engine.load_map("level.se")
player = engine.spawn("player", x, y)
engine.on_update(function(dt) ... end)
engine.on_key("space", function() ... end)
sound = engine.load_sound("boom.wav")
sound:play()
```
