---
name: numeros
description: Guarda a mano las métricas de tus reels - pegas, dictas o haces captura de lo que ves en Instagram, TikTok o YouTube y la fábrica lo guarda en metrics/<plataforma>.jsonl con el mismo formato que leen /revision, reels review y /calibrar. Sin APIs ni claves. Usar con "/numeros", a las 48 h de publicar y otra vez a los 7 días, o cuando digas cuántas visitas tiene un reel.
argument-hint: "[slug] [instagram|tiktok|youtube]"
---

# /numeros — tus números, a mano y sin APIs

Español claro; a quien manda, de tú. Gratis. No hace falta ninguna clave: quien manda mira las estadísticas en la
app y te las pasa como quiera (texto pegado, dictado o una captura de pantalla).

## 1. ¿Qué falta?
`uv run python .claude/skills/numeros/numeros.py pendientes` → qué reels de `publicar/` no tienen datos o los tienen
viejos. Si dijo un slug y una plataforma, ve a por ese. Si no, propón el primero que falte.
Cuándo: **a las 48 h** de publicar (antes todo es provisional) y **otra vez a los 7 días**.

## 2. Pedir los números (dónde están en cada app)
Pídele que abra el reel y toque "Ver estadísticas" (Instagram), "Analíticas" (TikTok) o "Estadísticas" (YouTube
Studio), y que te pase lo que vea. Los nombres cambian según la versión de la app; busca el equivalente:

| Dato que guardamos | Instagram | TikTok | YouTube Shorts | ¿Obligatorio? |
|---|---|---|---|---|
| visitas | Visualizaciones / Reproducciones | Visualizaciones del video | Visualizaciones | sí |
| alcance | Cuentas alcanzadas | Espectadores totales | Espectadores únicos (si no sale, las visitas) | sí |
| compartidos | Veces compartido / Envíos | Compartidos | Compartidos | sí |
| "me gusta" | Me gusta | Me gusta | Me gusta | no |
| comentarios | Comentarios | Comentarios | Comentarios | no |
| guardados | Guardados | Favoritos | — | no |
| visto medio (s) | Tiempo de reproducción promedio | Tiempo promedio de visualización | Duración media de visualización | no, pero importa |
| se va antes de 3 s (%) | tasa de omisión / "omitieron" | 100 − "% que vio los primeros segundos" si sale | 100 − "Se quedaron a verlo" | no, pero es **el** dato del arranque |
| seguidores | los de tu perfil, ahora | los de tu perfil | suscriptores | recomendado |

Y la **fecha y hora de publicación** (está en el propio reel). Si manda una captura, léela con cuidado y repítele
los números que has entendido antes de guardar. Si algo no aparece en su app, se deja vacío: no lo inventes.

## 3. Guardar (un reel y una plataforma por orden)
```
uv run python .claude/skills/numeros/numeros.py guardar --plataforma <instagram|tiktok|youtube> --slug <slug> \
  --publicado "AAAA-MM-DD HH:MM" --visitas N --alcance N --compartidos N \
  [--likes N] [--comentarios N] [--guardados N] [--visto-medio S] [--salta PCT] [--seguidores N]
```
- El slug es el nombre de la carpeta en `publicar/` (el gancho B es `<slug>-b`).
- Números sin puntos ni comas de miles ("12.345" → `12345`); los decimales, con punto (`14.5`).
- La hora, en la hora local de su computadora.
- Si el script avisa con ⚠, cuéntaselo y corrige si hace falta (se puede volver a guardar: vale la última línea).

## 4. Devolver algo útil (3 líneas)
Lo que importa del reel: **compartidos/alcance** (lo que da alcance), **se va antes de 3 s** (el arranque) y % visto,
comparados con sus otros reels si hay (`uv run reels review` para Instagram;
`uv run python .claude/skills/numeros/numeros.py tabla --plataforma <p>` para las demás). Sin conclusiones con un
solo reel: "un reel no demuestra nada; tres empiezan a hablar".
Si es su primera vez: el ejercicio del curso es calcular % visto, compartidos/alcance y guardados por compartido de
sus 3 primeros reels y escribir **una** hipótesis medible en `docs/hipotesis.md` (con su OK).
Si ya hay 8 reels maduros, recuerda que puede hacer `/calibrar`; si hace una semana del último informe, `/revision`.
