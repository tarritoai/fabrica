---
name: turno-de-noche
description: Antes de dormir, deja a la fábrica trabajando - render final, montaje, comprobación frase a frase y hojas de fotogramas del episodio (y de su gancho B), sin que la computadora se duerma, y por la mañana un parte en publicar/<slug>/PARTE.md. Nunca publica nada. Usar con "/turno-de-noche <slug>", cuando digas que te vas a dormir con un episodio aprobado, o con "/turno-de-noche parte" por la mañana.
argument-hint: "<slug> [nube] | parte [slug]"
---

# /turno-de-noche — la fábrica trabaja mientras duermes

Español claro; a quien manda, de tú. **La fábrica nunca publica nada**: deja todo listo en `publicar/<slug>/` y el
parte de la mañana. Subir el vídeo es cosa de quien manda.

## Por la noche: `/turno-de-noche <slug>`

### 1. ¿Está listo para el horno? (gratis, 1 minuto)
Lee `episodes/<slug>/estado.md` y comprueba:
- ✔ Puerta 2 (voz) aprobada y existen las voces (`episodes/<slug>/audio/beat_*.wav`);
- ✔ Puerta 3 (animática) aprobada. Si la Puerta 4 (preview) no lo está, avisa: "Vas a renderizar sin haber visto
  el movimiento. Es gratis en local, pero si algo se mueve raro lo verás mañana." Que decida.
- `uv run reels lint <slug>` sin errores;
- el **gancho B**: si existe `episodes/<slug>-b/`, que tenga sus voces (si no, el B se salta y lo dice el parte). Si
  no existe, ofrécelo antes de lanzar: «¿Preparo el gancho B para esta noche?». Prepararlo es el paso 6 de la capa 5
  de `/episodio` **sin render** (guion B, lint, voces con su OK de gasto y `publicar/<slug>/<slug>-b.txt`); el turno
  lo cuece después del A. El B se cuece **entero** (es otro episodio): tarda, o cuesta en la nube, lo mismo que el A;
- `publicar/<slug>/<slug>.txt` (texto del post): si falta, escríbelo ahora con quien manda (capa 5 de `/episodio`).
Si algo falla, dilo en una línea y no lances el turno.

### 2. Local o nube (puerta de gasto si es nube)
- **Local (por defecto, gratis)**: renderiza en su computadora. Tarda horas en máquinas lentas: por eso de noche.
  Que la deje **enchufada**, con la tapa abierta si es portátil, y sin apagarla. La fábrica impide que se duerma
  (en Mac con `caffeinate`, en Windows avisando al sistema, en Linux con `systemd-inhibit`), pero no puede impedir
  que alguien la apague ni que se quede sin batería.
- **Nube** (si lo pide o si `uv run reels doctor --prueba-render` dijo que en local no le da tiempo): GPU alquilada,
  céntimos por reel (con gancho B, el doble). **Pide el OK con el precio** (el saldo de Vast sale en
  `uv run reels doctor`). La máquina se destruye al acabar, también si algo falla, y al final del turno se limpia
  cualquier máquina que haya quedado. Si la computadora se apaga o se queda sin internet a mitad, la propia máquina
  se destruye sola a los 20 minutos (y como mucho a las 2 h 15 min de alquilarla): la fábrica no puede impedir el
  apagón, pero sí que siga cobrando.

### 3. Lanzar (en segundo plano, para que pueda cerrar todo)
```
uv run python .claude/skills/turno-de-noche/turno.py <slug> --segundo-plano [--cloud] [--portada <beat>]
```
- `--portada <beat>`: si en el estado ya hay un beat elegido para la portada.
- `--sin-b`: si no quiere el gancho B esta noche.
- `--calidad preview`: solo si quiere una prueba rápida (no es el vídeo final).
Comprueba a los 30 segundos que arranca: lee las últimas líneas de `publicar/<slug>/turno.log`. Si ya ha fallado,
explica por qué y no le mandes a dormir con un turno roto.

### 4. Despedida
Dile en 3 líneas: qué se va a hacer (A, y B si hay), dónde estará el parte (`publicar/<slug>/PARTE.md`) y que no
apague la computadora. Apunta en `estado.md`: "Turno de noche lanzado AAAA-MM-DD HH:MM (local/nube)".

## Por la mañana: `/turno-de-noche parte [slug]`
1. Si no da slug, busca el `publicar/*/PARTE.md` más reciente.
2. Si no hay `PARTE.md` pero sí `turno.pid`, el turno sigue en marcha o se cortó (la computadora se apagó o se
   durmió): mira la última línea de `turno.log` y dilo. Para seguir, se vuelve a lanzar: el render se reanuda donde
   se quedó.
   **Si el turno era en la nube** (lo dice el parte o `turno.log`) y no hay `PARTE.md`, o el parte dice que la
   limpieza falló: ejecuta `uv run reels cloud-cleanup` (solo destruye máquinas que nadie usa) y di lo que salga.
3. Lee el parte y resúmelo en 4–6 líneas: ¿está el vídeo?, ¿alguna frase fuera de su plano en la comprobación?, qué
   falta en `publicar/<slug>/`.
4. Lanza el `ojo` (modo movimiento) con `episodes/<slug>/sheet_0-3.png` y la hoja del final: lo que vea, en la misma
   respuesta.
5. Siguiente paso: abrir el vídeo (macOS `open`, Windows `start ""`, Linux `xdg-open`), verlo con sonido en el
   teléfono y aprobar la **Puerta 5** con `/episodio <slug>`. Recuerda: reels de prueba A y B, uno al día, en la
   misma franja. Y que lo sube quien manda.
6. Actualiza `estado.md` con el resultado del turno.
