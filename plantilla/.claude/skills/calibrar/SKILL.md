---
name: calibrar
description: Mide cuánto aciertan tus críticos simulados (los 5 espectadores y el jurado) frente a lo que pasó de verdad, con una ronda a ciegas si hace falta, y propone mejorarlos, ponerlos en prueba o despedirlos. Necesita al menos 8 reels con datos maduros (48 h). Nunca cambia nada sin tu OK. Usar desde /revision o con "/calibrar".
---

# /calibrar — despedir a quien no acierta

Los espectadores y el jurado son la misma IA con distintos gorros: solo valen lo que demuestren acertar. Español
claro; a quien manda, de tú. **Nada cambia sin su OK** (enséñale el diff).

## 0. ¿Se puede calibrar ya?
1. Datos al día: si hay API, `uv run reels stats` (si el último registro tiene más de 12 h); si no, que los números
   de `/numeros` tengan menos de una semana.
2. `uv run reels calibrate` → la primera línea dice cuántos **reels maduros** (≥ 48 h con alcance) hay.
3. **Si hay menos de 8, para aquí**: "Con N reels cualquier acierto se confunde con el azar. Hacen falta 8; te
   faltan 8−N. Mientras tanto, los espectadores se usan por lo concreto." No hagas ronda a ciegas ni propongas
   cambios.

## 1. Medir (con ≥ 8 reels maduros)
1. Lee la tabla de `reels calibrate`: por crítico, la correlación de su orden con los compartidos, el alcance y la
   retención (no saltar < 3 s), y el sesgo de las apuestas numéricas. Fuentes: `metrics/predicciones.jsonl` (antes
   de publicar: la honesta) y `metrics/calibracion.jsonl` (a ciegas).
2. **Ronda a ciegas** si hay ≥ 3 reels maduros sin calibrar a ciegas, o si la última estaba contaminada:
   - Describe cada reel como si fuera una idea: título inventado neutro, logline, segundo 0, primera frase, final.
     **Sin números, sin el slug, en orden aleatorio.** Guarda la correspondencia título → slug solo en tu cabeza (o
     en `metrics/calibracion-clave.tmp`, que borras al acabar).
   - Lanza en paralelo el `jurado` en **modo a ciegas** ("puntúalas todas, no mates ninguna, dame la tabla por
     criterios") y los espectadores en modo ideas (ligero: uno en modo panel; completo: uno por persona), con la
     orden expresa: "**no leas** `docs/lo-que-funciona.md`, `docs/hipotesis.md`, `docs/criticos.md`, `metrics/` ni
     `reviews/`; al final lista los archivos que has leído".
   - Si alguno dice haber leído uno de esos archivos o cita un número real → `contaminado: true`.
   - Guarda una línea por crítico en `metrics/calibracion.jsonl`:
     `{"fecha": "AAAA-MM-DD", "critico": "<nombre o jurado>", "modo": "a ciegas", "orden": ["<slug>", ...], "contaminado": false}`
     (el orden, traducido a slugs, del que más mandaría al que menos).
   - Vuelve a ejecutar `uv run reels calibrate`.

## 2. Diagnosticar (por crítico)
- **¿Predice algo?** Con n < 10, |ρ| < 0,6 no se distingue del azar: no saques conclusiones fuertes.
- **¿Sesgo fijo?** ¿Castiga siempre el mismo tipo de reel que luego funciona (pantalla en el fotograma 0, comedia,
  serie)? Busca el porqué en sus respuestas (`episodes/<slug>/critica.md`).
- **¿Redundante?** Dos espectadores con casi el mismo orden (ρ entre ellos > 0,8) en 2 calibraciones: sobra uno.
- **¿Falta alguien?** Quién comenta de verdad (con un script sobre `metrics/comments.jsonl`, sin nombres) y qué
  reels nadie vio venir: ¿qué persona los habría predicho? Esa es la candidata.

## 3. Proponer (con el diff exacto) — reglas para no moverse por ruido
- **Crear**: solo con un motivo en los datos. Como mucho **1 nueva por calibración**, entra **en prueba**.
- **Mejorar**: si un sesgo se repite en 2 calibraciones, una línea concreta en su persona (no reescribirla entera).
- **Subir de en prueba a activa**: ρ compartidos ≥ 0,3 en 2 calibraciones con n ≥ 8.
- **Despedir (retirar)**: ρ ≤ 0 en 2 calibraciones seguidas con n ≥ 8, o redundante. Se apunta en "Retirados" con
  el motivo; el historial nunca se borra. Antes de despedir a alguien de un papel (por ejemplo, el impaciente),
  propón quién ocupa ese papel.
- **Jurado**: si con n ≥ 10 su total no ordena los compartidos (ρ < 0,3), compara criterio a criterio y propone
  cambiar pesos (la suma tiene que seguir siendo sobre 50).
- **Plantilla**: entre 3 y 6 espectadores activos o en prueba. Más gorros de la misma IA no son más votos.

## 4. Guardar (✋ con OK)
- `docs/criticos.md`: tabla con los ρ nuevos, sesgos, historial (`- AAAA-MM-DD · cambio · motivo con números`).
- `docs/publico.md`: las personas nuevas, cambiadas o retiradas (con la plantilla del final del archivo).
- `.claude/agents/jurado.md`: solo si cambian los pesos.
- Borra `metrics/calibracion-clave.tmp` si lo creaste.
- Resumen en 4–6 líneas: quién acierta, quién no, a quién despedirías y por qué (con números).
