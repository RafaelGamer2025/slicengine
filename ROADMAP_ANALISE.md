# SlicEngine — Análise e Plano de Continuação (v0.2)

## Estado atual (v0.1.0 — commit d283d50)
Engine Python/pygame com: raycasting 3D estilo Doom, tile maps 2D, editor com pincel,
linguagem .sl (português), Lua (lupa), plugins C (ctypes), formato .se, menu com GIF,
IA assistente (online/local), shell embutido, perfis SQLite, hierarquia de cena.

Testes existentes (15 headless OK) + teste GUI (3 screenshots OK) rodam no SDL dummy.

## Problemas e gaps identificados (documentação vs. realidade)

### A. Bugs reais
1. `ptscript.py`: gramática `definir "vida" como 100` (usada no README e tools/gen_demo_se.py) NÃO é suportada — só `definir X para Y`.
2. `ptscript.py`: `destruir evento` → `api['destruir_evento']()` que é no-op na engine.
3. `ptscript.py`: `translate_action` com `criar`/`spawn` tem bug de precedência:
   `if low.startswith("spawn") or low.startswith("criar") and "entidade" in low`
   — qualquer linha começando com "criar" casa, mesmo sem "entidade".
4. `lua_api.py`: `show_text` adiciona em `state["texts"]` mas o core nunca processa essa fila (só `_toast` de 1 texto).
5. `lua_api.py`: callbacks Lua com assinatura `(dados)` quebram — a engine chama handlers como `(api, payload)`.
   - Mods Lua com `function(api) api.mostrar_texto(...)` funcionam, mas receitas da IA geram código que não roda.
6. `local.py`: mapa de extensão em `run_file` usa `"lua"` em vez de `".lua"` → inferência Lua falha.
7. `editor.py`: mensagem "Desfazer: use Ctrl+Z no futuro (em breve)" — undo não existe.
8. `editor.py`: câmera limita a `pixels_w - 400`/`pixels_h - 300` — quebrado para mapas pequenos (mínimo negativo → trava em 0, OK, mas 400/300 arbitrário).
9. `raycaster.py`: sprite render por pixel em Python é LENTO — aceleração possível com numpy/surface.blit.
10. `__main__.py --run-dir`: carrega world.json com código estranho (`Engine.__bases__[0] and __import__...`) — funciona mas frágil.
11. `__init__.py`: `VERSION` importado mas `utils.VERSION` = "0.1.0".
12. Editor não tem modo de colocar ENTIDADES (player/inimigo/moeda) — só tiles.

### B. Funcionalidades faltantes (prometidas ou naturais)
1. **Undo/Redo no editor** (Ctrl+Z / Ctrl+Y).
2. **Entidades no editor** (modo entidade: colocar P/E/C no mapa).
3. **Sistema de partículas** (fumaça, explosão, poeira) — feature clássica de engine.
4. **Animação de sprites** (sprite sheets: strip/frames).
5. **Saves persistentes** via `profile_db.py` (já existe a infra, falta integração engine.save_state/load_state).
6. **Debug console** no jogo (F1) para ver variáveis e disparar eventos.
7. **Minimapa** no modo 3D.
8. **Melhorar IA local** para gerar código compatível com a API real.
9. **Suporte a tilesets** (editor escolhe sprite de arquivo).
10. **Efeitos de áudio**: canais múltiplos, volume global, fade de música.
11. **Correção de eventos**: padronizar assinatura dos handlers (`payload`) e documentar.
12. **Bump para v0.2.0**.

## Escopo escolhido para v0.2 (implementar nesta sessão)
1. Corrigir bugs A1–A7, A9 (A10 refator leve).
2. Novo módulo `effects.py`: sistema de partículas (Pool de partículas, emitter,
   integração no core para desenhar e atualizar).
3. Novo módulo suporte `spritesheet.py`: `AnimatedSprite` com strips.
4. Undo/Redo no editor + modo entidades no editor.
5. Saves: `engine.save_state()` / `engine.load_state()` usando profile_db.
6. Debug console (F1) com lista de variáveis.
7. Minimapa no modo 3D.
8. Corrigir receitas da IA para a API real.
9. Adicionar testes para tudo novo; rodar GUI test e regenerar screenshots.
10. Commit + push da v0.2.0.
