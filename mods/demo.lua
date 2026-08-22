-- SlicEngine — Exemplo de mod em Lua.
-- Registra eventos que rodam durante o jogo.

-- Ao iniciar: define pontuação e mostra mensagem
engine.on_event("iniciar", function(api, payload)
    engine.set_var("pontos", 0)
    engine.show_text("Mod Lua carregado! Use WASD para andar.", 3)
end)

-- Ao pegar moeda (evento disparado pelo jogo)
engine.on_event("colidir:coin", function(api, payload)
    engine.add_var("pontos", 10)
    engine.tocar_som("moeda.wav")
    engine.show_text("Pontos: " .. engine.get_var("pontos"), 1)
end)

-- A cada quadro: dt chega como payload do update
engine.on_event("update", function(api, dt)
    -- lógica por frame (ex.: movimento customizado)
end)
