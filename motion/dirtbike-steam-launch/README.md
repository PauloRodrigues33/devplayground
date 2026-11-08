# Dirtbike Simulator — "WE ARE ON STEAM" (motion para Instagram)

- **Vídeo final:** `out/dirtbike-on-steam.mp4` — 1080×1350 (4:5, feed), 30 fps, 22 s, áudio mudo
- **Com beat guia:** `out/dirtbike-on-steam_with-guide-beat.mp4` — mesmo vídeo com um beat sintético de 120 BPM, só para conferir a sincronia

## Timeline (120 BPM → 1 batida = 0,5 s = 15 frames)

| Batidas | Tempo | Cena |
|---|---|---|
| 0–8 | 0:00–0:04 | WE / ARE / ON (uma palavra a cada 2 batidas, fundo troca a cada ½) + pilha WE ARE ON |
| 8–16 | 0:04–0:08 | As palavras repetidas de 16 formas, troca a cada ½ batida |
| 16–20 | 0:08–0:10 | Build-up (troca a cada ¼ de batida) + respiro |
| 20–28 | 0:10–0:14 | **DROP:** WE ARE ON STEAM |
| 28–36 | 0:14–0:18 | WISHLIST NOW + botão |
| 36–44 | 0:18–0:22 | Logo do jogo + "WISHLIST NOW ON STEAM" |

Para encaixar na música, alinhe o início do vídeo com o primeiro tempo de um compasso; o drop cai no tempo 1 do compasso 6 (0:10).

## Regerar

```bash
pip install pillow numpy fonttools brotli cairosvg
python3 prep.py <pasta-com-os-screenshots>   # já rodado; gera assets/
python3 render.py                            # ~2 min
python3 render.py --stills 0,150,300         # frames soltos para conferir
```

Fontes: Anton e Archivo Black (SIL Open Font License). Ícone Steam: Simple Icons.
