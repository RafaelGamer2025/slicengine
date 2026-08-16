"""
SlicEngine — API da engine exposta para scripts Lua (via lupa).

Permite escrever mods e jogos inteiros em Lua:

    engine.window("Meu Jogo Lua", 800, 600)
    engine.set_var("pontos", 0)

    function ao_tocar_moeda(dados)
        engine.add_var("pontos", 1)
        engine.play_sound("moeda.wav")
        engine.show_text("+" .. dados.valor .. " pontos!", 1.5)
    end

    engine.on_event("colidir:moeda", ao_tocar_moeda)

    function atualizar(dt)
        -- lógica por frame
    end
    engine.on_event("update", atualizar)

    engine.start()
"""
def _wrap_callable(fn, lupa):
    """Converte uma callable Lua recebida pela engine em callable Python."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except lupa.LuaError as e:
            print(f"[Lua] erro no callback: {e}")
    return wrapper


def build_lua_api(engine, lupa) -> "lupa.LuaRuntime":
    """Cria um runtime Lua com a tabela `engine` cheia de funções
    vinculadas ao estado interno da engine."""
    rt = lupa.LuaRuntime(unpack_returned_tuples=True)

    state = engine.lua_state

    api = {
        "window": lambda title, w, h: state.setdefault("window",
                                                       [title, w, h]),
        "get_var": lambda name: state["vars"].get(name, 0),
        "set_var": lambda name, val: state["vars"].__setitem__(name, val),
        "add_var": lambda name, n: state["vars"].__setitem__(
            name, state["vars"].get(name, 0) + n),
        "play_sound": lambda path: state["snd_queue"].append(path),
        "play_music": lambda path: state["mus_queue"].append(path),
        "stop_music": lambda: state["mus_queue"].append(None),
        "show_text": lambda text, dur=2.0: state["texts"].append(
            [text, dur, dur]),
        "stop_game": lambda: state.setdefault("stop", True),
        "move_player": lambda dx, dy: state["player_move"].append([dx, dy]),
        "spawn_entity": lambda kind, x=0.0, y=0.0: state["spawns"].append(
            [kind, x, y]),
        "load_map": lambda path: state.setdefault("load_map", path),
        "log": print,
    }

    # tabela engine
    lua_api = rt.eval("{}", ) if False else rt.table_from(api)

    # registrar handler via on_event
    def on_event_py(event_id, fn):
        engine.adicionar_evento_lua(event_id, _wrap_callable(fn, lupa))
    lua_api["on_event"] = on_event_py

    # start: marca que o script Lua quer iniciar o jogo
    lua_api["start"] = lambda: state.setdefault("lua_start", True)

    rt.globals().engine = lua_api
    return rt
