---
name: actualizar
description: Actualiza la fábrica del alumno a la última versión del curso sin pisar su memoria (docs de lo que funciona, hipótesis, decisiones, ideas, episodios, estilo, marca y personajes propios) y con copia de seguridad. Úsala cuando el alumno escriba /fabrica:actualizar o pida traer la versión nueva de la fábrica.
allowed-tools:
  - Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh" *)
  - Bash(powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" *)
  - PowerShell(powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" *)
  - Bash(claude plugin marketplace update tarritoai)
  - Bash(claude plugin update fabrica@tarritoai)
  - Read
---

# Actualizar la fábrica

Trae las mejoras del curso a la carpeta del alumno. Lo que el alumno ha escrito o cambiado **no se pisa nunca**: el
instalador compara cada archivo con la versión que se instaló y decide solo.

FABRICA es:
- **Mac y Linux:** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh" PASO [opciones]`
- **Windows:** `powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" PASO [opciones]`

Lanza cada comando con el tiempo máximo de la herramienta (600000 ms). CARPETA es la carpeta de la fábrica (la actual
si tiene `reels/` y `curso/`; si no, pregunta).

## Pasos
1. **Traer la versión nueva del curso.** `claude plugin marketplace update tarritoai` y luego
   `claude plugin update fabrica@tarritoai`. Si el comando `claude` no funciona desde aquí, pídele al alumno:
   `/plugin` → **Marketplaces** → **tarritoai** → **Update marketplace**, y sigue.
2. **Ver el plan (no cambia nada):** `FABRICA actualizar --proyecto "CARPETA"`. Cuéntaselo en llano:
   - *archivos nuevos* y *archivos que se actualizarán*: piezas del curso que no ha tocado;
   - *archivos que TÚ cambiaste*: se quedan los suyos; la versión nueva queda aparte para comparar;
   - *tu memoria*: no se toca nunca;
   - *archivos que la plantilla ya no usa*: van a la copia de seguridad, no se borran.
3. **Pide el OK** y aplica: `FABRICA actualizar --proyecto "CARPETA" --aplicar`. Antes de sustituir nada se guarda
   una copia en `CARPETA/.fabrica/copias/<fecha>/`.
4. **Archivos que el alumno cambió y que la plantilla también cambió** (sus versiones nuevas están en
   `CARPETA/.fabrica/actualizacion-<versión>/`): ofrécele revisarlos uno a uno. Lee los dos, explica la diferencia
   en una frase y, **solo si dice que sí**, mezcla a mano lo nuevo del curso respetando lo suyo. Si no quiere, se
   queda todo como está.
5. **Herramientas y revisión:** `FABRICA herramientas --proyecto "CARPETA"` (solo descarga lo que cambió de versión)
   y `FABRICA doctor --proyecto "CARPETA"`.
6. Termina diciéndole que escriba `/reload-plugins` (o cierre y abra Claude) para usar las skills nuevas.

Si algo falla, el comando imprime «✘ … Qué hacer … (código del error: …)»: explícalo y, si hace falta, usa
`/fabrica:tarrito`. Nunca borres `.fabrica/copias/`: es su red de seguridad.
