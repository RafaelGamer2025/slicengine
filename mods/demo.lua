-- SlicEngine — Exemplo de mod em Lua.
-- Registra eventos que rodam durante o jogo.

-- Ao iniciar: define pontuação e mostra mensagem
engine.on_event("iniciar", function(api)
    engine.set_var("pontos", 0)
    api.mostrar_texto("Mod Lua carregado! Use WASD para andar.", 3)
end)

-- Ao pegar moeda (evento disparado pelo jogo)
engine.on_event("moeda_pegada", function(api)
    engine.set_var("pontos", engine.get_var("pontos") + 10)
    api.tocar_som("moeda.wav")
    api.mostrar_texto("Pontos: " .. engine.get_var("pontos"), 1)
end)

-- A cada quadro: verifica tecla para pular/atirar
engine.on_event("quadro", function(api)
    if api.tecla_pressionada("space") then
        api.tocar_som("pulo.wav")
    end
end)
