# SlicEngine — Linguagem de script em português (.sl)
# Escreva suas regras no estilo "quando X acontecer: faça Y"

quando iniciar:
    definir "vida" como 100
    definir "moedas" como 0
    tocar som "inicio.wav"
    mostrar texto "Bem-vindo à SlicEngine!" por 3

quando tecla "espaço" for pressionada:
    aumentar 1 no "JOGO"
    tocar som "pulo.wav"

quando moeda_pegada:
    aumentar 10 no "moedas"
    mostrar texto "Moedas: " + "moedas" por 1

quando vida chegar a 0:
    mostrar texto "Game Over!" por 5
    parar jogo
