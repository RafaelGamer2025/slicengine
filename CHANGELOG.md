# CHANGELOG — SlicEngine

## v0.2.0 (2026-08-16)

### Novos recursos
- **Sistema de partículas** (`slicengine/effects.py`): emitters com pool,
  gravidade, atrito, fade de alpha, cores nomeadas (fogo, fumaça, magia,
  sangue, brilho). Integrado aos modos 2D e 3D; `engine.emitir_particulas()`.
- **Sprites animados** (`slicengine/spritesheet.py`): `Animation.strip()`
  para cortar sprite sheets, modos `loop`/`once`/`pingpong` e
  `SpriteAtlas` para carregar várias animações por nome.
- **Saves persistentes** (`slicengine/saves.py`): `engine.save_game(slot)` /
  `engine.load_game(slot)` usando o banco SQLite de perfis.
- **Undo/Redo no editor** (`Ctrl+Z`/`Ctrl+Y`), com restauração de
  entidades junto com os tiles.
- **Modo entidade no editor** (tecla `N`): colocar player (P), inimigo (E)
  e moeda (C) diretamente no mapa, com indicador visual.
- **Minimapa** no modo 3D (tecla `M` para alternar).
- **Console de debug** (tecla `F1`): variáveis de jogo, entidades vivas,
  partículas ativas.
- **Screenshot** (tecla `F2`): salva PNG da tela atual.

### Correções de bugs
- Gramática `.sl`: `definir "vida" como 100` (antes só aceitava `para`).
- Callbacks Lua: assinatura `(api, payload)` compatível com a engine;
  suporte a runtimes Lua separados por mod (erro do lupa corrigido).
- `lua_api.py`: `show_text` agora integra com o toast da engine;
  aliases em português completos (`mostrar_texto`, `tocar_som`,
  `mover_jogador`, `criar_entidade`, `parar_jogo`, `pegar`, `adicionar`,
  `definir`).
- `ScriptRunner.run_file`: detecção de linguagem por extensão corrigida
  (`.lua`, `.py`, `.sl`).
- `ptscript.py`: `destruir evento` agora mata entidades vivas de fato;
  `criar entidade "x"` sem a palavra "entidade" funciona.
- `__main__.py --run-dir`: carregamento de `world.json` corrigido.
- `ModSystem`: cada mod Lua agora roda em runtime próprio (funções entre
  runtimes do lupa não são chamáveis).
- Receitas da IA local (`aiscript.py`) reescritas para a API real.

### Testes
- Suíte expandida de 15 para **32 testes**, cobrindo partículas, sprites
  animados, saves, undo/redo, integração Lua→toast e `run_file`.

## v0.1.0
- Lançamento inicial: engine 2D/3D (raycaster), editor de mapas, scripts
  Lua/Python/.sl, mods, formato `.se`, perfis SQLite.
