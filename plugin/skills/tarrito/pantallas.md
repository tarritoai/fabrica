# Pantallas en inglés: qué dicen y qué pulsar

Los textos de Claude Code cambian un poco entre versiones: reconócelos por la idea, no por la letra exacta.

| Dónde | Lo que ves (inglés) | Qué significa | Qué pulsar |
|---|---|---|---|
| Claude Code, al abrir una carpeta | «Do you trust the files in this folder?» / «Is this a project you created or one you trust?» | Claude va a poder leer y ejecutar cosas en ESTA carpeta | Si es tu carpeta de la fábrica: **Yes, I trust this folder** (Enter). Si se abrió en tu carpeta personal (con fotos, banco…): **No, exit**, y abre Claude dentro de la carpeta de la fábrica |
| Claude Code, antes de un comando | «Do you want to proceed?» · 1. Yes · 2. Yes, and don't ask again for … · 3. No, and tell Claude what to do differently | Permiso para ejecutar un comando en tu ordenador | Lee la línea del comando. Si es el instalador de la fábrica (`fabrica.sh` / `fabrica.ps1`) o `uv run reels …`: **1** (o **2** para no volver a preguntar). Si pide `sudo`, borrar cosas fuera de tu fábrica o algo que no entiendes: **3** y pregunta |
| Claude Code, al editar un archivo | «Do you want to make this edit to <archivo>?» | Va a cambiar un archivo | **Yes** si es de tu fábrica y es lo que pediste |
| `/plugin install` | «Add marketplace tarritoai/fabrica?» (o parecido) | Añadir la «tienda» de plugins del curso | **Yes / Add** |
| `/plugin install` | «Install for you (user scope)» · «for all collaborators (project scope)» · «in this repo only (local scope)» | Dónde instalarlo | **Install for you (user scope)**: así funciona en cualquier carpeta |
| `/plugin` → Marketplaces → tarritoai | «Enable auto-update» | Recibir los arreglos del curso solos | Púlsalo (Enter) |
| Tras instalar o actualizar | «Run /reload-plugins to apply» | El plugin está, pero esta conversación aún no lo ha cargado | Escribe `/reload-plugins` |
| Límite de uso | «… usage limit reached … resets at 3pm» | Has gastado el uso de tu plan por unas horas. No cuesta dinero | Espera a esa hora y escribe «sigue donde lo dejaste» |
| Windows | «Do you want to allow this app to make changes to your device?» (Control de cuentas de usuario) | Un programa pide permisos de administrador | La fábrica **nunca** lo pide. Solo lo verás si instalas Git for Windows o Claude Code: ahí, **Sí** |
| Windows | «Windows protected your PC» (SmartScreen) | Windows no conoce ese programa | La fábrica no abre programas con doble clic. Si te sale al abrir un instalador oficial (Git, Claude): «More info» → «Run anyway» solo si lo descargaste de su web oficial |
| Windows Terminal | «You are about to paste text that contains multiple lines…» | Vas a pegar varias líneas | **Paste anyway** si es un comando del Manual |
| Mac | «“Terminal” would like to access files in your Documents folder.» | Permiso de macOS para la terminal | **Allow** (OK) si tu fábrica está en Documentos |
| Mac | «“rhubarb” Not Opened. Apple could not verify…» | macOS no reconoce un programa descargado | **Done** (no «Move to Trash») y ver `mac-gatekeeper` en errores-conocidos.md |
| Mac | «The “xcode-select” command requires the command line developer tools. Would you like to install the tools now?» | Faltan las herramientas de Apple | **Install** → **Agree**; tarda 10–20 min |
| Mac | «To open “rhubarb”, you need to install Rosetta. Do you want to install it now?» | Traductor de Apple para programas de Intel | **Install** |
