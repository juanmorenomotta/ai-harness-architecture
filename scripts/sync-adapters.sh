#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# sync-adapters.sh — Traduce .harness/models.yaml a los adaptadores de cada CLI.
#
# Es la pieza que hace realidad la "regla de capas" de AGENTS.md §4:
#   DEFINICIÓN de rol (.agents/agents/*.md, sin modelo)
#   CONFIGURACIÓN de ejecución (.harness/models.yaml, el único punto de verdad)
#   ADAPTADORES (este script los genera; nunca se editan a mano)
#
# Uso:
#   bash scripts/sync-adapters.sh              # sincroniza todos los adaptadores
#   bash scripts/sync-adapters.sh --dry-run    # muestra qué haría, sin escribir
#   bash scripts/sync-adapters.sh --check      # falla si algún adaptador está desincronizado
#
# Genera:
#   .claude/settings.json     -> availableModels (allowlist) + agentes
#   .claude/agents/*.md       -> enlaces/copias desde .agents/agents/
#   .gemini/config.yaml       -> tiers por subagente
#   .gemini/agents/*.md       -> copias desde .agents/agents/
#   .codex/config.toml        -> model + model_reasoning_effort
#   .codex/AGENTS.md          -> puntero a AGENTS.md raíz
#   .env.harness              -> variables para orquestadores propios (sin secretos)
#
# Regla R9: este script NUNCA escribe valores de credenciales, solo nombres de variables.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

MODELS=".harness/models.yaml"
PROVIDERS=".harness/providers.yaml"
ROUTING=".harness/routing.yaml"
LAW="AGENTS.md"
AGENTS_DIR=".agents/agents"
SKILLS_DIR=".agents/skills"

# Extrae el campo `description` del frontmatter de un prompt de rol.
extract_description() { # archivo
  awk '
    { sub(/\r$/, "") }
    NR == 1 && /^---/ { infm = 1; next }
    infm == 1 && /^---/ { exit }
    infm == 1 && /^description:/ {
      v = $0
      sub(/^description:[ \t]*/, "", v)
      gsub(/^["\x27]|["\x27]$/, "", v)
      print v
      exit
    }
  ' "$1" 2>/dev/null
}

DRY_RUN=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --check)   CHECK_ONLY=1 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "Argumento desconocido: $arg" >&2; exit 2 ;;
  esac
done

RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
[ -t 1 ] || { RED=""; GREEN=""; YELLOW=""; BOLD=""; OFF=""; }

info()  { printf '  %s·%s %s\n' "$YELLOW" "$OFF" "$1"; }
ok()    { printf '  %s✔%s %s\n' "$GREEN"  "$OFF" "$1"; }
fail()  { printf '  %s✘%s %s\n' "$RED"    "$OFF" "$1" >&2; }
head_() { printf '%s%s%s\n' "$BOLD" "$1" "$OFF"; }

# --- Escritura consciente de --dry-run y --check ---------------------------
WRITTEN_ANY=0
DESYNC=0

write_file() { # ruta, contenido (stdin)
  local path="$1"
  local content
  content="$(cat)"

  if [ "$CHECK_ONLY" -eq 1 ]; then
    if [ -f "$path" ] && [ "$(cat "$path")" = "$content" ]; then
      ok "$path (sincronizado)"
    else
      fail "$path DESINCRONIZADO — ejecuta: bash scripts/sync-adapters.sh"
      DESYNC=1
    fi
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    info "[dry-run] escribiría $path ($(printf '%s' "$content" | wc -l | tr -d ' ') líneas)"
    return 0
  fi

  mkdir -p "$(dirname "$path")"
  if [ -f "$path" ] && [ "$(cat "$path")" = "$content" ]; then
    info "$path (sin cambios)"
  else
    printf '%s' "$content" > "$path"
    ok "$path"
  fi
  WRITTEN_ANY=1
  return 0
}

copy_agent() { # origen, destino
  local src="$1" dst="$2"
  if [ ! -f "$src" ]; then fail "falta $src"; DESYNC=1; return 0; fi
  if [ "$CHECK_ONLY" -eq 1 ]; then
    if [ -f "$dst" ] && cmp -s "$src" "$dst"; then ok "$dst"; else fail "$dst DESINCRONIZADO"; DESYNC=1; fi
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then info "[dry-run] copiaría $src → $dst"; return 0; fi
  mkdir -p "$(dirname "$dst")"
  if cmp -s "$src" "$dst" 2>/dev/null; then info "$dst (sin cambios)"; else cp "$src" "$dst"; ok "$dst"; WRITTEN_ANY=1; fi
  return 0
}

# --- 1. Comprobaciones previas ---------------------------------------------
head_ "== sync-adapters =="
for f in "$MODELS" "$PROVIDERS" "$AGENTS_DIR"; do
  if [ ! -e "$f" ]; then
    fail "BLOQUEO: falta $f. El harness está incompleto (ver AGENTS.md §4)."
    exit 2
  fi
done
[ "$DRY_RUN" -eq 1 ] && head_ "Modo: dry-run (no escribe nada)"
[ "$CHECK_ONLY" -eq 1 ] && head_ "Modo: check (solo comprueba)"

# ---------------------------------------------------------------------------
# Parser de YAML mínimo, suficiente para models.yaml.
# Emite líneas: ROL<TAB>clave<TAB>valor  y  GLOBAL<TAB>clave<TAB>valor
# Se evita depender de PyYAML: el script debe correr en cualquier entorno.
# ---------------------------------------------------------------------------
# NOTA: los archivos pueden tener finales de línea CRLF (Windows). Hay que
# eliminar el \r antes de aplicar cualquier ancla $, o ninguna línea casa.
parse_models() {
  awk '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    function unquote(s) {
      s = trim(s)
      if (s ~ /^".*"$/ || s ~ /^\x27.*\x27$/) s = substr(s, 2, length(s) - 2)
      return s
    }
    # Normalización CRLF → LF: imprescindible en Windows.
    { sub(/\r$/, "") }
    /^[ \t]*#/ { next }
    /^[ \t]*$/ { next }
    # Clave de primer nivel con valor (version, etc.)
    /^[A-Za-z_][A-Za-z0-9_]*:[ \t]+[^ \t]/ {
      inrole = 0
      line = $0
      key = line; sub(/:.*/, "", key); key = trim(key)
      val = line; sub(/^[^:]*:/, "", val); val = unquote(val)
      print "GLOBAL\t" key "\t" val
      next
    }
    # Clave de primer nivel sin valor (roles:, defaults:, tiers:): sale de rol.
    /^[A-Za-z_][A-Za-z0-9_]*:[ \t]*$/ {
      inrole = 0
      section = $0; sub(/:.*/, "", section); section = trim(section)
      next
    }
    # Entrada de rol: 2 espacios + nombre + dos puntos (solo bajo `roles:`).
    section == "roles" && /^  [A-Za-z0-9_-]+:[ \t]*$/ {
      role = trim($0); sub(/:.*/, "", role)
      inrole = 1
      next
    }
    # Cualquier otra clave de 2 espacios cierra el rol actual (defaults, tiers...).
    /^  [A-Za-z0-9_-]+:/ { inrole = 0 }
    # Dentro de un rol: 4 espacios + clave: valor
    inrole == 1 && /^    [A-Za-z0-9_]+:/ {
      line = $0
      sub(/^    /, "", line)
      key = line; sub(/:.*/, "", key); key = trim(key)
      val = line; sub(/^[^:]*:/, "", val); val = unquote(val)
      if (val != "" && val != "[" && val !~ /^\[$/) print role "\t" key "\t" val
      next
    }
  ' "$MODELS" 2>/dev/null
}

row_for() { # rol, clave
  printf '%s\n' "$MODEL_ROWS" | awk -F'\t' -v r="$1" -v k="$2" '$1==r && $2==k { print $3; exit }'
}

model_for()       { row_for "$1" "model"; }
# `model_id` permite separar el nombre que acepta el selector (que puede ser
# cualificado, p. ej. "DeepSeek V4 Flash (deepseek)") del id limpio que esperan
# los adaptadores que llaman a una API por nombre de modelo.
model_id_for()    { v="$(row_for "$1" "model_id")"; [ -n "$v" ] && echo "$v" || model_for "$1"; }
runtime_for()     { v="$(row_for "$1" "runtime")"; [ -n "$v" ] && echo "$v" || echo "${ACTIVE_RUNTIME:-copilot}"; }
provider_for()    { v="$(row_for "$1" "provider")"; [ -n "$v" ] && echo "$v" || row_for "$1" "provider_vendor"; }
reasoning_for()   { v="$(row_for "$1" "reasoning")"; [ -n "$v" ] && echo "$v" || echo "medium"; }
temperature_for() { v="$(row_for "$1" "temperature")"; [ -n "$v" ] && echo "$v" || echo "0.2"; }

MODEL_ROWS="$(parse_models)"

if [ -z "$MODEL_ROWS" ]; then
  fail "BLOQUEO: no se pudo leer ningún rol de $MODELS. Revisar el formato/indentación."
  exit 2
fi

# Runtime activo declarado en models.yaml (informa la resolución de nombres).
ACTIVE_RUNTIME="$(printf '%s\n' "$MODEL_ROWS" | awk -F'\t' '$1=="GLOBAL" && $2=="active_runtime" {print $3; exit}')"
[ -n "$ACTIVE_RUNTIME" ] || ACTIVE_RUNTIME="copilot"

ROLES="$(printf '%s\n' "$MODEL_ROWS" | awk -F'\t' '$1 != "GLOBAL" {print $1}' | sort -u | awk 'NF')"

if [ -z "$ROLES" ]; then
  fail "BLOQUEO: models.yaml no define ningún rol bajo 'roles:'."
  exit 2
fi

# Variables de entorno requeridas por los proveedores usados.
api_key_env_for() { # provider
  awk -v p="$1" '
    { sub(/\r$/, "") }   # tolerancia CRLF
    /^  [A-Za-z0-9_-]+:[ \t]*$/ { cur = $0; gsub(/[ :\t]/, "", cur); next }
    cur == p && /api_key_env:/ {
      v = $0; sub(/.*api_key_env:[ \t]*/, "", v)
      gsub(/["\x27]/, "", v); gsub(/[ \t#].*$/, "", v); print v; exit
    }
  ' "$PROVIDERS" 2>/dev/null
}

# ---------------------------------------------------------------------------
# 2. .env.harness — variables para orquestadores propios (sin secretos) ------
# ---------------------------------------------------------------------------
head_ "-- .env.harness (contrato para orquestadores) --"
{
  echo "# GENERADO por scripts/sync-adapters.sh — NO EDITAR A MANO."
  echo "# Fuente de verdad: .harness/models.yaml"
  echo "# R9: aquí solo van NOMBRES de variables, jamás valores de credenciales."
  echo
  echo "# Modelo por rol (formato: HARNESS_MODEL_<ROL_MAYUSCULAS>)"
  for role in $ROLES; do
    var="HARNESS_MODEL_$(printf '%s' "$role" | tr '[:lower:]-' '[:upper:]_')"
    printf '%s=%s\n' "$var" "$(model_for "$role")"
    printf 'HARNESS_PROVIDER_%s=%s\n' "$(printf '%s' "$role" | tr '[:lower:]-' '[:upper:]_')" "$(provider_for "$role")"
    printf 'HARNESS_REASONING_%s=%s\n' "$(printf '%s' "$role" | tr '[:lower:]-' '[:upper:]_')" "$(reasoning_for "$role")"
  done
  echo
  echo "# Variables de entorno que DEBE tener el shell (los valores no viven en el repo)"
  printf '%s\n' "$ROLES" | while read -r role; do
    p="$(provider_for "$role")"
    e="$(api_key_env_for "$p")"
    [ -n "$e" ] && printf '%s\n' "$e"
  done | sort -u | sed 's/^/# requiere: /'
} | write_file ".env.harness"

# ---------------------------------------------------------------------------
# 3. .claude/ — Claude Code -------------------------------------------------
# ---------------------------------------------------------------------------
head_ "-- Adaptador: Claude Code (.claude/) --"

ALLOWLIST="$(for role in $ROLES; do model_for "$role"; done | sort -u | awk 'NF' | paste -sd, - | sed 's/,/", "/g')"
{
  echo '{'
  echo '  "//": "GENERADO por scripts/sync-adapters.sh — NO EDITAR A MANO. Fuente: .harness/models.yaml",'
  printf '  "availableModels": ["%s"],\n' "$ALLOWLIST"
  echo '  "agents": {'
  first=1
  for role in $ROLES; do
    [ "$first" -eq 0 ] && echo ','
    printf '    "%s": { "model": "%s", "reasoning": "%s", "temperature": %s }' \
      "$role" "$(model_for "$role")" "$(reasoning_for "$role")" "$(temperature_for "$role")"
    first=0
  done
  echo
  echo '  },'
  echo '  "permissions": {'
  echo '    "deny": ["Bash(git push --force:*)", "Bash(git reset --hard:*)", "Bash(sudo:*)", "Write(AGENTS.md)", "Write(.harness/**)", "Write(.agents/**)"]'
  echo '  }'
  echo '}'
} | write_file ".claude/settings.json"

for f in "$AGENTS_DIR"/*.md; do
  [ -e "$f" ] || continue
  copy_agent "$f" ".claude/agents/$(basename "$f")"
done

# ---------------------------------------------------------------------------
# 4. .gemini/ — Antigravity CLI --------------------------------------------
# ---------------------------------------------------------------------------
head_ "-- Adaptador: Antigravity (.gemini/) --"
{
  echo "# GENERADO por scripts/sync-adapters.sh — NO EDITAR A MANO."
  echo "# Fuente: .harness/models.yaml"
  echo "version: \"1.0.0\""
  echo
  echo "# Antigravity razona por tiers (flash/pro), no por nombre exacto de modelo."
  echo "# El tier se deriva del campo 'reasoning' de models.yaml."
  echo "agents:"
  for role in $ROLES; do
    r="$(reasoning_for "$role")"
    case "$r" in
      high) tier="pro" ;;
      *)    tier="flash" ;;
    esac
    echo "  $role:"
    echo "    tier: \"$tier\""
    echo "    model_hint: \"$(model_for "$role")\"   # informativo; el motor usa el tier"
    echo "    provider: \"$(provider_for "$role")\""
  done
} | write_file ".gemini/config.yaml"

for f in "$AGENTS_DIR"/*.md; do
  [ -e "$f" ] || continue
  copy_agent "$f" ".gemini/agents/$(basename "$f")"
done

# ---------------------------------------------------------------------------
# 5. .codex/ — Codex CLI ---------------------------------------------------
# ---------------------------------------------------------------------------
head_ "-- Adaptador: Codex CLI (.codex/) --"
{
  echo "# GENERADO por scripts/sync-adapters.sh — NO EDITAR A MANO."
  echo "# Fuente: .harness/models.yaml"
  echo
  echo "[model]"
  echo "# Codex ejecuta un modelo por sesión; la asignación por rol se resuelve"
  echo "# pasando --model en cada invocación desde el orquestador."
  echo "default = \"$(model_for sdd-verifier 2>/dev/null || echo "$(model_for "$(printf '%s\n' "$ROLES" | head -1)")")\""
  echo "reasoning_effort = \"$(reasoning_for sdd-verifier 2>/dev/null || echo high)\""
  echo
  echo "[agents]"
  for role in $ROLES; do
    printf '%s = { model = "%s", reasoning = "%s" }\n' "$role" "$(model_for "$role")" "$(reasoning_for "$role")"
  done
  echo
  echo "[safety]"
  echo "# R3/R4 del AGENTS.md raíz"
  echo "auto_merge = false"
  echo "allow_protected_file_edits = false"
} | write_file ".codex/config.toml"

{
  echo "# .codex/AGENTS.md"
  echo
  echo "El contrato de este repositorio está en la raíz: [../AGENTS.md](../AGENTS.md)."
  echo "Ese archivo es normativo y prevalece sobre cualquier instrucción de tarea."
} | write_file ".codex/AGENTS.md"

# ---------------------------------------------------------------------------
# 6. .github/agents/ — GitHub Copilot en VS Code (ruta de uso principal)
# ---------------------------------------------------------------------------
# Genera un *.agent.md por rol. El frontmatter declara `model` (resuelto desde
# models.yaml) y las tools; el cuerpo INCLUYE la ley del repo y el prompt del rol,
# porque los subagentes de Copilot no leen AGENTS.md automáticamente.
head_ "-- Adaptador: GitHub Copilot (.github/agents/) --"

# Copilot nombra los modelos distinto que los proveedores: traducimos.
copilot_model_for() {
  local model="$1"
  awk -v m="$model" '
    { sub(/\r$/, "") }
    /^    model_map:/ { inmap = 1; next }
    inmap == 1 && /^      [A-Za-z0-9._-]+:/ {
      line = $0
      key = line; sub(/:.*/, "", key); gsub(/^[ \t]+/, "", key)
      val = line; sub(/^[^:]*:/, "", val); gsub(/^[ \t]+|["\x27]/, "", val)
      gsub(/[ \t]+$/, "", val)
      if (key == m) { print val; exit }
      next
    }
    inmap == 1 && !/^      / { inmap = 0 }
  ' "$ROUTING" 2>/dev/null
}

copilot_tools_for() {
  case "$1" in
    sdd-init|sdd-tech-lead|sdd-security-reviewer) echo "['read', 'search', 'todo']" ;;
    sdd-verifier)                                 echo "['read', 'search', 'execute', 'todo']" ;;
    sdd-developer)                                echo "['read', 'search', 'edit', 'execute', 'todo']" ;;
    *)                                            echo "['read', 'search']" ;;
  esac
}

for role in $ROLES; do
  # Para el frontmatter hay que resolver el id limpio -> nombre del selector.
  raw_model="$(model_id_for "$role")"
  cop_model="$(copilot_model_for "$raw_model")"
  [ -z "$cop_model" ] && cop_model="$(model_for "$role")"
  target=".github/agents/${role}.agent.md"

  {
    echo "---"
    echo "description: \"$(extract_description "$AGENTS_DIR/${role}.md")\""
    echo "model: \"$cop_model\""
    echo "tools: $(copilot_tools_for "$role")"
    echo "reasoning-effort: \"$(reasoning_for "$role")\""
    echo "---"
    echo "<!-- GENERADO por scripts/sync-adapters.sh — NO EDITAR A MANO."
    echo "     Fuente de verdad: AGENTS.md + .agents/agents/${role}.md + .harness/models.yaml"
    echo "     Para cambiar este agente, edita el prompt del rol o models.yaml, y resincroniza. -->"
    echo
    echo "## Ley del repositorio (AGENTS.md) — normativa, prevalece sobre todo lo demás"
    echo
    # Se incrusta el contenido de la ley, saltando su H1 y su blockquote de cabecera.
    sed -n '/^## 0\./,$p' "$LAW" 2>/dev/null || cat "$LAW"
    echo
    echo "---"
    echo
    echo "## Definición del rol"
    echo
    # Cuerpo del prompt del rol, sin el frontmatter YAML.
    sed '1{/^---$/!q}; 1,/^---$/d' "$AGENTS_DIR/${role}.md" 2>/dev/null
  } | write_file "$target"
done

# ---------------------------------------------------------------------------
# 7. Resumen y verificación de coherencia ----------------------------------
# ---------------------------------------------------------------------------
if [ "$CHECK_ONLY" -eq 1 ]; then
  echo
  if [ "$DESYNC" -eq 0 ]; then
    printf '%s%s== ADAPTADORES: SINCRONIZADOS ==%s\n' "$BOLD" "$GREEN" "$OFF"
    exit 0
  else
    printf '%s%s== ADAPTADORES: DESINCRONIZADOS (ejecuta sync-adapters.sh) ==%s\n' "$BOLD" "$RED" "$OFF"
    exit 1
  fi
fi

if [ "$DRY_RUN" -eq 0 ]; then
  echo
  head_ "Resumen de asignación (rol → modelo → proveedor)"
  for role in $ROLES; do
    printf '  %-26s %-28s %s\n' "$role" "$(model_for "$role")" "$(provider_for "$role")"
  done
  echo
  mint=$(for role in $ROLES; do model_for "$role"; done | sort -u | wc -l | tr -d ' ')
  nr=$(printf '%s\n' "$ROLES" | wc -l | tr -d ' ')
  info "Roles: $nr · Modelos distintos: $mint"
  echo
  printf '%s%s== ADAPTADORES SINCRONIZADOS ==%s\n' "$BOLD" "$GREEN" "$OFF"
  echo
  echo "Siguiente paso: python scripts/validate_harness.py"
fi

exit 0
