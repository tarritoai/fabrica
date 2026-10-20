---
name: instalar
description: Instala la fábrica de reels del curso en este ordenador (Windows 10/11, Mac con chip Apple o Linux) sin contraseñas de administrador, y termina con un primer vídeo de prueba gratis. Úsala cuando el alumno escriba /fabrica:instalar, pida instalar o reparar la fábrica, o diga que acaba de instalar el plugin.
argument-hint: "[carpeta donde quieres tu fábrica]"
allowed-tools:
  - Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh" *)
  - Bash(powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" *)
  - PowerShell(powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" *)
  - Read
---

# Instalar la fábrica

Vas a llevar de la mano a una persona que **nunca ha usado una terminal**. Le da miedo romper algo, lee mal el
inglés y no sabe qué es Python. Tu trabajo: que acabe con su fábrica funcionando y su primer vídeo abierto en
pantalla, sin sustos.

## Reglas (no se negocian)

1. **Español llano, frases cortas.** Antes de cada paso, una línea: qué vas a hacer, para qué sirve y cuánto tarda.
   Después, una línea: qué ha pasado. Nada de jerga sin explicar (si dices «terminal», «carpeta», «descargar»,
   explícalo la primera vez en cinco palabras).
2. **Solo ejecutas el instalador de esta skill** (el comando FABRICA de abajo). No improvises instalaciones: nada de
   `apt`, `brew`, `winget`, `pip`, `npm -g`, `curl | sh` ni editar el PATH a mano. Si un paso falla, **no lo
   arregles con otros comandos**: lee el error, explícalo y repite el paso o sigue el «Qué hacer» que imprime.
3. **Nunca `sudo`, nunca contraseñas, nunca «Ejecutar como administrador».** Todo se instala dentro de la carpeta
   de la fábrica. Única excepción, solo en Mac y solo si el instalador lo pide: Rosetta o las herramientas de Apple,
   que el alumno lanza él mismo en la app Terminal (tú le dictas el comando).
4. **Nunca pidas claves en el chat** (ElevenLabs, Vast…). Van en el archivo `.env`, que el alumno edita con su editor
   de texto (paso 8). Si te pega una clave en el chat, dile que no pasa nada, que la borre de su cuenta de ElevenLabs
   y cree otra, y que la próxima vaya al `.env`.
5. **Todo es repetible.** Si un paso se corta (internet, tiempo, se cerró la tapa), se lanza otra vez igual: lo que ya
   está hecho no se repite y las descargas siguen donde se quedaron.
6. Si el alumno se agobia: nada de lo que hacemos toca sus fotos, sus documentos ni su sistema. Todo vive en una
   carpeta; si algo sale mal, se borra la carpeta y en paz.

## El comando FABRICA

Mira en qué sistema estás (lo dice tu entorno: `win32` = Windows, `darwin` = Mac, `linux` = Linux) y usa siempre,
tal cual, con las comillas:

- **Mac y Linux:** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh" PASO [opciones]`
- **Windows** (da igual si tu herramienta es Git Bash o PowerShell):
  `powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" PASO [opciones]`

Lanza cada paso con el **tiempo máximo de la herramienta (600000 ms)**. Los pasos largos (`herramientas` de Blender y
del `modelo`, `dependencias` y `humo`) lánzalos **en segundo plano** (run_in_background) y espera el aviso de que han
terminado: con una conexión lenta pueden pasar de 10 minutos. Si el alumno pregunta cómo va, lee las últimas líneas
de la salida. La primera vez el comando instala `uv` (el ayudante que trae Python; tarda menos de un minuto).
Cuando abajo pone `--proyecto CARPETA`, usa la carpeta elegida en el paso 1, entre comillas dobles y **sin barra
al final** (`"C:\fabrica"`, no `"C:\fabrica\"`).

Si el comando falla, termina con un bloque así:

```
✘ <qué ha pasado>
  Qué hacer: <el arreglo>
  (código del error: <código> · registro: <ruta del registro>)
```

Explícaselo en llano y, si hace falta más detalle, busca el `<código>` (columna id) en
`${CLAUDE_PLUGIN_ROOT}/skills/tarrito/errores-conocidos.md`.

## Pasos

### 0. Bienvenida (no ejecutes nada todavía)
En 3–4 líneas: vamos a montar tu fábrica; tarda entre 30 y 60 minutos (casi todo es esperar descargas, unos 1,5 GB; ocupará unos 5 GB);
no pide contraseñas; puedes seguir usando el ordenador; si es un portátil, **enchúfalo**. Al final verás tu primer
vídeo. Pregunta si empezamos.

### 1. ¿Sirve este ordenador? ¿Dónde vive tu fábrica?
1. `FABRICA sistema` → resume en una línea (sistema, memoria, espacio libre). Si sale algún «✘» en los bloqueos (Mac
   con Intel, Windows muy antiguo, Linux en ARM), explícalo con cariño y para aquí: no es culpa suya; ofrece
   `/fabrica:tarrito`.
2. Propón la carpeta. Si el alumno escribió una carpeta al llamar a la skill (`$ARGUMENTS`), esa es la propuesta.
   Si no, la recomendada que imprime el paso anterior (`C:\fabrica` en Windows, `fabrica` dentro de su carpeta
   personal en Mac y Linux). Explica por qué: **ruta corta, sin tildes ni espacios y fuera de OneDrive / iCloud /
   Dropbox** (la nube se pelea con los miles de archivos del render). Si Claude está abierto en una carpeta vacía
   que ya se llama algo como «fabrica», ofrécela también. **Espera su respuesta.**
3. Comprueba la elegida: `FABRICA sistema --carpeta "CARPETA"`. Si hay «✘» (OneDrive, poco espacio, carpeta con
   otras cosas), explícalo y propón la recomendada. Los «!» son avisos: cuéntalos y sigue si el alumno quiere.

### 2. Preparar la carpeta (segundos)
`FABRICA preparar --proyecto "CARPETA"` → copia la fábrica (código, personajes, efectos, documentos) a su carpeta,
crea su `.env` vacío y su historial de cambios. Si la carpeta ya era una fábrica, no toca nada suyo.

### 3. Las herramientas (la parte larga)
Lánzalas **de una en una**, en este orden, con `FABRICA herramientas --proyecto "CARPETA" --solo NOMBRE`. Antes de
cada una, dile qué es en una frase:

| NOMBRE | Qué es (para el alumno) | Tamaño |
|---|---|---|
| `blender` | el estudio 3D donde se rueda cada escena | ~350 MB |
| `ffmpeg` | la mesa de montaje de vídeo y sonido | ~150 MB |
| `whisper` | el «oído» que comprueba que cada frase suena en su plano | ~10 MB |
| `modelo` | lo que ese oído sabe de idiomas | ~490 MB |
| `rhubarb` | el que mueve los labios de los personajes | ~90 MB |
| `node` | el motor de las pantallas de móvil y los subtítulos | ~30 MB |
| `emojis` | la fuente de emojis (solo hace algo en Linux) | ~10 MB |

Mientras descarga, el instalador imprime el progreso cada pocos segundos. Si el paso falla por la conexión
(`sin-conexion`) o se corta, **lánzalo otra vez igual**: sigue donde se quedó (los megas ya bajados no se pierden).
Si falla tres veces seguidas, propón seguir más tarde o desde otra red: no hay prisa, nada se pierde. En Mac:
- `mac-rosetta`: pide al alumno que abra la app **Terminal** (Aplicaciones → Utilidades) y pegue
  `softwareupdate --install-rosetta --agree-to-license`. Puede pedirle la contraseña de su Mac: es lo único que la
  pide, y la escribe él (no se ve mientras teclea; es normal). Luego repite `--solo rhubarb`.
- `mac-sin-herramientas`: en Terminal, `xcode-select --install` → acepta la ventana de Apple → espera a que termine
  → repite `--solo whisper`.

### 4. Las piezas de Python y de Remotion (3–8 minutos)
`FABRICA dependencias --proyecto "CARPETA"`. Si en Linux avisa de librerías del navegador que faltan, explícale que
eso sí necesita a alguien con la contraseña de administrador una vez, y que de momento seguimos.

### 5. Revisión
`FABRICA doctor --proyecto "CARPETA"`. Todo en ✔ = listo. Los «!» son avisos (rubberband y git en Linux son
opcionales; la clave de ElevenLabs vacía es normal hoy). Si hay «✘»: **no ejecutes los comandos de la flecha →**
que sugiere el doctor (son para quien instala a mano); repite el paso de esta skill que toca esa pieza, p. ej.
`FABRICA herramientas --proyecto "CARPETA" --solo ffmpeg --forzar`.

### 6. Tu primer vídeo (3–15 minutos)
`FABRICA humo --proyecto "CARPETA" --abrir`. Lánzalo **en segundo plano** (run_in_background) y espera el aviso de
que ha terminado. Mientras tanto, cuéntale qué está pasando: un guion de dos frases → la escena 3D en Blender → el
render (fotograma a fotograma; aquí está la espera) → el montaje con voces y subtítulos → el «oído» lo comprueba.
Si el ordenador no tiene una gráfica que sirva, el instalador cambia solo a otro motor más lento y lo apunta: no es
un error. Al terminar, el vídeo se abre solo; si no, `FABRICA abrir video --proyecto "CARPETA"`. Celebra: «esto ha
salido de tu ordenador». Recuérdale que a esta calidad se ve granulado a propósito: es una prueba.

### 7. Actualizaciones y español (pregunta antes)
- «¿Quieres que tu fábrica reciba los arreglos del curso sola?» → si dice que sí:
  `FABRICA ajustes --auto-update`. Si falla, enséñale: escribe `/plugin` → pestaña **Marketplaces** → **tarritoai** →
  **Enable auto-update**.
- «¿Quieres que Claude te hable siempre en español, también fuera de la fábrica?» → si dice que sí:
  `FABRICA ajustes --idioma spanish`.

### 8. La voz (opcional, para más adelante)
Las voces de SUS personajes usarán ElevenLabs, pero **hoy no hace falta** (la prueba trae su voz grabada) y no hay
que pagar nada todavía: el curso le dirá cuándo. Cuando tenga su clave, `FABRICA abrir env --proyecto "CARPETA"`
abre el archivo `.env` en su editor de texto: la pega detrás de `ELEVENLABS_API_KEY=`, guarda y cierra. Nunca en el
chat.

### 9. Cierre: abrir Claude en tu fábrica
Explica que, a partir de ahora, Claude se abre **dentro de su carpeta** (así conoce sus herramientas y sus comandos
propios, como `/episodio` o `/ideas`):
- **Windows 11:** Explorador de archivos → su carpeta (`C:\fabrica`) → clic derecho en un hueco → «Abrir en
  Terminal» → `claude`. **Windows 10:** Mayúsculas + clic derecho en un hueco → «Abrir la ventana de PowerShell
  aquí» → `claude`.
- **Mac:** Terminal → `cd ~/fabrica` → `claude`.
- **Linux:** en la carpeta, clic derecho → «Abrir en una terminal» (o `cd ~/fabrica`) → `claude`.

(Si eligió otra carpeta, usa la suya en estos ejemplos.)

Que cierre esta conversación (`/exit`) y lo haga ahora. Si algo se tuerce más adelante: `/fabrica:tarrito` y pega
el error.

## Reparar o repetir
Toda la skill es segura de repetir sobre una fábrica ya instalada: lo que está bien no se toca. Para reinstalar una
sola herramienta: `--solo NOMBRE --forzar`. `FABRICA estado --proyecto "CARPETA"` resume qué hay instalado. El
registro completo de todo lo que se ha hecho está en `CARPETA/logs/instalacion.log`.
