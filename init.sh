#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# init.sh — Gate de verificación del harness (Regla R6 de AGENTS.md).
#
# Es el ÚNICO gate. Si esto falla, la fase NO avanza. Prohibido saltarlo,
# desactivar checks o "arreglarlo" tocando tests/CI (Reglas R6 y R7).
#
# Uso:
#   ./init.sh              # ejecuta todos los checks habilitados
#   ./init.sh --fast       # solo lint + typecheck (sin tests)
#   ./init.sh --json       # salida legible por máquina (para diagnose_harness.py)
#
# Salida: 0 = PASS · 1 = FAIL · 2 = BLOQUEO (config inválida / falta herramienta)
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 2

FAST=0
JSON=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --json) JSON=1 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
  esac
done

# --- Presentación ----------------------------------------------------------
if [ "$JSON" -eq 0 ]; then
  RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
  [ -t 1 ] || { RED=""; GREEN=""; YELLOW=""; BOLD=""; OFF=""; }
  printf '%s\n' "${BOLD}== Gate del harness (init.sh) ==${OFF}"
else
  RED=""; GREEN=""; YELLOW=""; BOLD=""; OFF=""
fi

FAILED=0
declare -a RESULTS=()

record() { # nombre, estado, detalle
  RESULTS+=("$1|$2|$3")
  if [ "$JSON" -eq 0 ]; then
    case "$2" in
      PASS) printf '  %s✔%s %-12s %s\n' "$GREEN" "$OFF" "$1" "$3" ;;
      FAIL) printf '  %s✘%s %-12s %s\n' "$RED" "$OFF" "$1" "$3" ;;
      SKIP) printf '  %s○%s %-12s %s\n' "$YELLOW" "$OFF" "$1" "$3" ;;
    esac
  fi
  [ "$2" = "FAIL" ] && FAILED=1
  return 0
}

# --- Detección de proyecto -------------------------------------------------
has() { command -v "$1" >/dev/null 2>&1; }
file_exists() { [ -f "$ROOT/$1" ]; }

detect_manifest() {
  for f in package.json pyproject.toml requirements.txt setup.py Cargo.toml go.mod pom.xml build.gradle composer.json Gemfile; do
    file_exists "$f" && { echo "$f"; return 0; }
  done
  echo ""
}

MANIFEST="$(detect_manifest)"
[ -n "$MANIFEST" ] && record "manifest" "PASS" "$MANIFEST" \
                  || record "manifest" "SKIP" "sin manifiesto de proyecto (repo de specs/harness)"

# --- 1. Secretos (R9) — primero, porque es bloqueante ----------------------
if file_exists ".gitleaks.toml" && has gitleaks; then
  if gitleaks detect --no-banner --redact -c .gitleaks.toml >/dev/null 2>&1; then
    record "secrets" "PASS" "sin secretos detectados"
  else
    record "secrets" "FAIL" "gitleaks encontró posibles secretos (R9)"
  fi
elif has gitleaks; then
  gitleaks detect --no-banner --redact >/dev/null 2>&1 \
    && record "secrets" "PASS" "sin secretos detectados" \
    || record "secrets" "FAIL" "gitleaks encontró posibles secretos (R9)"
else
  # Fallback sin gitleaks: patrones obvios sobre el árbol de trabajo.
  if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    if git -C "$ROOT" grep -IEn \
        -e 'sk-[A-Za-z0-9]{20,}' \
        -e 'ghp_[A-Za-z0-9]{20,}' \
        -e 'AIza[0-9A-Za-z_-]{30,}' \
        -e '(api[_-]?key|secret|token)[[:space:]]*[:=][[:space:]]*["'\''][^"'\'']{16,}' \
        -- ':!*.md' ':!docs/' ':!*.lock' >/dev/null 2>&1; then
      record "secrets" "FAIL" "patrón tipo credencial en el árbol (R9)"
    else
      record "secrets" "PASS" "sin patrones evidentes (fallback grep)"
    fi
  else
    record "secrets" "SKIP" "gitleaks no instalado y no hay repo git"
  fi
fi

# --- 2. Lint ---------------------------------------------------------------
if [ "$JSON" -eq 0 ]; then printf '%s\n' "${BOLD}-- Lint --${OFF}"; fi
if [ -f "$ROOT/pyproject.toml" ] || [ -f "$ROOT/requirements.txt" ]; then
  if has ruff; then
    ruff check . >/dev/null 2>&1 && record "lint" "PASS" "ruff check" \
                                   || record "lint" "FAIL" "ruff check encontró problemas"
  else
    record "lint" "SKIP" "ruff no instalado (pip install ruff)"
  fi
elif [ -f "$ROOT/package.json" ]; then
  if has npx && grep -q '"lint"' "$ROOT/package.json" 2>/dev/null; then
    npm run --silent lint >/dev/null 2>&1 && record "lint" "PASS" "npm run lint" \
                                           || record "lint" "FAIL" "npm run lint falló"
  else
    record "lint" "SKIP" "sin script 'lint' en package.json"
  fi
elif [ -f "$ROOT/go.mod" ]; then
  has go && { go vet ./... >/dev/null 2>&1 && record "lint" "PASS" "go vet" \
                                          || record "lint" "FAIL" "go vet falló"; } \
           || record "lint" "SKIP" "go no instalado"
else
  record "lint" "SKIP" "no aplica (sin código aún)"
fi

# --- 3. Formato (solo comprobación, nunca reescribe) -----------------------
if [ -f "$ROOT/pyproject.toml" ] && has ruff; then
  ruff format --check . >/dev/null 2>&1 && record "format" "PASS" "ruff format --check" \
                                        || record "format" "FAIL" "archivos mal formateados"
elif [ -f "$ROOT/package.json" ] && grep -q '"format:check"' "$ROOT/package.json" 2>/dev/null; then
  npm run --silent format:check >/dev/null 2>&1 && record "format" "PASS" "format:check" \
                                                || record "format" "FAIL" "format:check falló"
else
  record "format" "SKIP" "no aplica"
fi

# --- 4. Typecheck ----------------------------------------------------------
if [ -f "$ROOT/pyproject.toml" ] && has mypy; then
  mypy . >/dev/null 2>&1 && record "typecheck" "PASS" "mypy" \
                         || record "typecheck" "FAIL" "mypy reportó errores"
elif [ -f "$ROOT/tsconfig.json" ] && has npx; then
  npx --no-install tsc --noEmit >/dev/null 2>&1 && record "typecheck" "PASS" "tsc --noEmit" \
                                                || record "typecheck" "FAIL" "tsc reportó errores"
elif [ -f "$ROOT/go.mod" ] && has go; then
  go build ./... >/dev/null 2>&1 && record "typecheck" "PASS" "go build" \
                                 || record "typecheck" "FAIL" "go build falló"
else
  record "typecheck" "SKIP" "no aplica"
fi

# --- 5. Tests --------------------------------------------------------------
if [ "$FAST" -eq 1 ]; then
  record "tests" "SKIP" "--fast activo"
else
  if [ -f "$ROOT/pyproject.toml" ] && has pytest; then
    pytest -q >/dev/null 2>&1 && record "tests" "PASS" "pytest -q" \
                              || record "tests" "FAIL" "pytest falló"
  elif [ -f "$ROOT/package.json" ] && grep -q '"test"' "$ROOT/package.json" 2>/dev/null; then
    npm test --silent >/dev/null 2>&1 && record "tests" "PASS" "npm test" \
                                      || record "tests" "FAIL" "npm test falló"
  elif [ -f "$ROOT/go.mod" ] && has go; then
    go test ./... >/dev/null 2>&1 && record "tests" "PASS" "go test ./..." \
                                  || record "tests" "FAIL" "go test falló"
  else
    record "tests" "SKIP" "no aplica (sin código aún)"
  fi
fi

# --- 6. Integridad del harness --------------------------------------------
files_ok=1
for f in AGENTS.md harness.config.json .harness/models.yaml .harness/providers.yaml .harness/routing.yaml; do
  file_exists "$f" || { files_ok=0; break; }
done
[ "$files_ok" -eq 1 ] && record "harness" "PASS" "artefactos base presentes" \
                      || record "harness" "FAIL" "falta $f (ver AGENTS.md §4)"

# --- 7. Guardrails declarados (R4): el harness no debe ir en el diff de una tarea ----
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  if git -C "$ROOT" diff --name-only HEAD 2>/dev/null | grep -qE '^(AGENTS\.md|harness\.config\.json|init\.sh|\.harness/|\.agents/)'; then
    record "guardrails" "FAIL" "una tarea toca el harness (R4). Requiere PR separado."
  else
    record "guardrails" "PASS" "sin cambios en archivos protegidos"
  fi
else
  record "guardrails" "SKIP" "sin repo git"
fi

# --- Resultado -------------------------------------------------------------
if [ "$JSON" -eq 1 ]; then
  printf '{"failed":%d,"checks":[' "$FAILED"
  first=1
  for r in "${RESULTS[@]}"; do
    IFS='|' read -r n s d <<<"$r"
    [ "$first" -eq 0 ] && printf ','
    printf '{"name":"%s","status":"%s","detail":"%s"}' "$n" "$s" "$d"
    first=0
  done
  printf ']}\n'
else
  echo
  if [ "$FAILED" -eq 0 ]; then
    printf '%s%s== GATE: PASS ==%s\n' "$BOLD" "$GREEN" "$OFF"
  else
    printf '%s%s== GATE: FAIL — la fase no avanza (R6) ==%s\n' "$BOLD" "$RED" "$OFF"
  fi
fi

exit "$FAILED"
