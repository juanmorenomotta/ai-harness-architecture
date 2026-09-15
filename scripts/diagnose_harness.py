#!/usr/bin/env python3
"""Auto-diagnóstico del harness en las 9 dimensiones del SDLC agéntico.

En lugar de una nota agregada, puntúa nueve dimensiones independientes: un solo
número oculta más de lo que revela. Cada dimensión se mide con evidencia
verificable en disco, no con auto-percepción.

Uso:
    python scripts/diagnose_harness.py                 # informe por consola
    python scripts/diagnose_harness.py --write         # además escribe el informe
    python scripts/diagnose_harness.py --json          # salida máquina-legible
    python scripts/diagnose_harness.py --dimension 5   # solo una dimensión

Salida: 0 siempre que el informe se genere (el diagnóstico no bloquea el flujo).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_yaml  # noqa: E402

# Windows redirige la salida en cp1252/cp437 (no UTF-8): los caracteres de barra
# revientan el script con UnicodeEncodeError, y forzar UTF-8 produce mojibake en
# consolas no-UTF-8. Solución: recordar la codificación ORIGINAL y elegir los
# símbolos en función de lo que la salida real puede representar.
_ORIGINAL_ENCODING = getattr(sys.stdout, "encoding", None) or "ascii"

try:  # pragma: no cover - red de seguridad para que nada reviente
    sys.stdout.reconfigure(errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(errors="replace")  # type: ignore[attr-defined]
except (AttributeError, OSError, ValueError):  # pragma: no cover
    pass


def _supports_unicode() -> bool:
    """¿La salida original puede representar bloques y marcas?"""
    try:
        "█░✓→⚠".encode(_ORIGINAL_ENCODING)
    except (UnicodeEncodeError, LookupError, TypeError):
        return False
    return True

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / ".spec" / "_harness" / "diagnostic.md"

# Rutas canónicas del harness (evita literales duplicados y typos).
LAW_FILE = "AGENTS.md"
CONFIG_FILE = "harness.config.json"
GATE_FILE = "init.sh"
POLICIES_FILE = ".agents/policies/permissions.yaml"
MODELS_FILE = ".harness/models.yaml"

MAX_SCORE = 4

# Códigos de salida (el diagnóstico nunca bloquea el flujo del harness).
EXIT_OK = 0
EXIT_USAGE = 2

# Rango válido de dimensiones del SDLC agéntico.
MIN_DIMENSION = 1
MAX_DIMENSION = 9

# Perfiles objetivo por nivel de madurez del harness (ver docs/definition-SDD-harness.md).
TARGETS = {
    "nivel-1": {"min_total": 9, "must_have": [1, 3, 5, 6]},
    "nivel-2": {"min_total": 22, "must_have": [1, 2, 3, 4, 5, 6, 9]},
}

DIMENSION_NAMES = {
    1: "Ingeniería de contexto",
    2: "Adopción de herramientas",
    3: "Integración en el workflow",
    4: "Revisión de código con IA",
    5: "Controles de governance",
    6: "Cobertura de skills",
    7: "Autonomía agéntica",
    8: "Generación de tests",
    9: "Gates de CI/CD con IA",
}


@dataclass
class DimensionResult:
    number: int
    score: int
    evidence: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def git_repo() -> bool:
    return (ROOT / ".git").exists()


def project_manifest() -> str | None:
    for name in (
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
    ):
        if (ROOT / name).exists():
            return name
    return None


def inert_checks() -> list[str]:
    """Checks del gate que existen pero NO pueden hacer su trabajo todavía.

    Un check inerte parece verde y no verifica nada: contarlo como cumplido
    produce un diagnóstico inflado (100% falso). Se reporta explícitamente.
    """
    inert: list[str] = []
    if not git_repo():
        inert.append("`secrets`: sin repo git, el escaneo del árbol no se ejecuta")
        inert.append("`guardrails`: sin repo git, no se detectan cambios en archivos protegidos")
    if not project_manifest():
        inert.append("`lint`/`format`/`typecheck`/`tests`: sin manifiesto de proyecto, todo da SKIP")
    if not exists(".gitleaks.toml") or not shutil.which("gitleaks"):
        inert.append("`secrets`: gitleaks no instalado (solo se usa el patrón grep de respaldo)")
    return inert


def read(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8") if path.exists() else ""


def skill_count() -> int:
    skills_dir = ROOT / ".agents" / "skills"
    return len(list(skills_dir.glob("*/SKILL.md"))) if skills_dir.exists() else 0


def run_gate() -> tuple[bool, str]:
    """Ejecuta init.sh y devuelve (pasó, primera línea relevante)."""
    script = ROOT / GATE_FILE
    if not script.exists():
        return False, "init.sh no existe"
    try:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"no se pudo ejecutar init.sh: {exc}"
    tail = (result.stdout or result.stderr).strip().splitlines()
    return result.returncode == 0, tail[-1] if tail else "sin salida"


# ---------------------------------------------------------------------------
# Las 9 dimensiones. Cada una devuelve 0..4 con evidencia y carencias.
# ---------------------------------------------------------------------------

def dimension_1() -> DimensionResult:
    """Ingeniería de contexto: ¿existe una única fuente de verdad actual?"""
    result = DimensionResult(1, 0)
    law = read(LAW_FILE)
    has_law = bool(law) and "R1" in law and len(law) > 2000
    if has_law:
        result.score += 2
        result.evidence.append("AGENTS.md presente con reglas de oro numeradas (ley del repo)")
    else:
        result.gaps.append("AGENTS.md ausente o sin reglas de oro → contexto fragmentado")

    if exists(".spec") or "`.spec/`" in law:
        result.score += 1
        result.evidence.append("convención de artefactos SDD en `.spec/<feature>/` documentada")
    else:
        result.gaps.append("no hay convención de artefactos por feature")

    scoped = read(POLICIES_FILE)
    if "writable_paths" in scoped:
        result.score += 1
        result.evidence.append("contexto acotado por rol vía `writable_paths`")
    else:
        result.gaps.append("no se acota el alcance de lectura/escritura por rol")
    return result


def dimension_2() -> DimensionResult:
    """Adopción de herramientas: ¿hay adaptadores reales, no intenciones?"""
    result = DimensionResult(2, 0)
    adapters = {
        ".claude/settings.json": "Claude Code",
        ".gemini/config.yaml": "Antigravity",
        ".codex/config.toml": "Codex CLI",
        ".env.harness": "orquestador propio",
    }
    present = [name for path, name in adapters.items() if exists(path)]
    if len(present) >= 3:
        result.score += 3
        result.evidence.append(f"adaptadores generados: {', '.join(present)}")
    elif present:
        result.score += 1
        result.evidence.append(f"adaptadores parciales: {', '.join(present)}")
    else:
        result.gaps.append("sin adaptadores generados; ejecuta scripts/sync-adapters.sh")

    if exists("scripts/sync-adapters.sh"):
        result.score += 1
        result.evidence.append("sincronización automatizada de adaptadores")
    else:
        result.gaps.append("la traducción de modelos es manual (error humano probable)")
    return result


def dimension_3() -> DimensionResult:
    """Integración en el workflow: ¿las fases están cableadas end-to-end?"""
    result = DimensionResult(3, 0)
    roles = [p.name for p in (ROOT / ".agents" / "agents").glob("*.md")] if exists(".agents/agents") else []
    if len(roles) >= 4:
        result.score += 2
        result.evidence.append(f"{len(roles)} roles definidos: {', '.join(sorted(roles))}")
    elif roles:
        result.score += 1
        result.gaps.append(f"solo {len(roles)} rol(es): el ciclo no cubre todas las fases")
    else:
        result.gaps.append("sin roles definidos")

    if exists(".agents/skills/sdd-orchestrator/SKILL.md"):
        result.score += 1
        result.evidence.append("skill de orquestación presente (delega fases en frío)")
    else:
        result.gaps.append("sin orquestador: las fases no se encadenan")

    if exists(CONFIG_FILE):
        result.score += 1
        result.evidence.append("workflow declarado en harness.config.json (patrones de commit/rama)")
    else:
        result.gaps.append("sin harness.config.json: el workflow no es verificable")
    return result


def _significant_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Devuelve (indentación, contenido) de las líneas no vacías ni comentadas."""
    result: list[tuple[int, str]] = []
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        result.append((len(raw) - len(raw.lstrip()), stripped))
    return result


def _find_deny_entries(
    blocks: list[tuple[int, str]], start: int, role_indent: int
) -> tuple[list[str], int]:
    """Extrae las entradas de la clave `deny:` dentro de la sección de un rol."""
    entries: list[str] = []
    in_deny = False
    deny_indent = 0
    index = start

    while index < len(blocks):
        indent, content = blocks[index]
        if not in_deny:
            if content.startswith("deny:"):
                in_deny = True
                deny_indent = indent
            elif indent <= role_indent:
                break  # fin de la sección del rol
        else:
            if content.startswith("- "):
                entries.append(content[2:].strip())
            elif indent <= deny_indent:
                break
        index += 1
    return entries, index


def verifier_cannot_edit(policies_text: str) -> bool:
    """¿La política impide explícitamente que el Verifier edite código?

    Se analiza por bloques en lugar de con una regex con backtracking: buscar
    las entradas de `deny:` dentro de la sección `sdd-verifier`.
    """
    blocks = _significant_lines(policies_text.splitlines())

    for index, (indent, content) in enumerate(blocks):
        if content != "sdd-verifier:":
            continue
        entries, _ = _find_deny_entries(blocks, index + 1, indent)
        return "edit" in entries

    return False


def dimension_4() -> DimensionResult:
    """Revisión de código con IA: ¿hay un revisor independiente del autor?"""
    result = DimensionResult(4, 0)
    if exists(".agents/agents/sdd-verifier.md"):
        result.score += 2
        result.evidence.append("rol Verifier definido, separado del Developer")
    else:
        result.gaps.append("sin rol de verificación independiente")

    if verifier_cannot_edit(read(POLICIES_FILE)):
        result.score += 1
        result.evidence.append("el Verifier no puede editar código (independencia forzada)")
    else:
        result.gaps.append("el Verifier podría editar lo que revisa → pierde independencia")

    if exists(".agents/skills/verify-report/SKILL.md"):
        result.score += 1
        result.evidence.append("skill de informe de verificación con veredicto PASS/FAIL")
    else:
        result.gaps.append("sin formato de informe de verificación")
    return result


def dimension_5() -> DimensionResult:
    """Controles de governance: permisos, gates, deny-first."""
    result = DimensionResult(5, 0)
    policies = read(".agents/policies/permissions.yaml")
    if "global_deny" in policies and "pattern" in policies:
        result.score += 1
        result.evidence.append("política deny-first con patrones de comando prohibidos")
    else:
        result.gaps.append("sin lista de denegación global")

    config = read(CONFIG_FILE)
    if "protectedFiles" in config:
        result.score += 1
        result.evidence.append("archivos protegidos declarados (AGENTS.md, .harness/, .agents/)")
    else:
        result.gaps.append("sin archivos protegidos: el agente puede reescribir su propia ley")

    if "allowAutoMerge" in config and "false" in config:
        result.score += 1
        result.evidence.append("auto-merge explícitamente deshabilitado (R3)")

    if "G1" in policies and "G2" in policies and "G3" in policies:
        result.score += 1
        result.evidence.append("tres gates humanos definidos (G1 scope, G2 plan, G3 merge)")
    else:
        result.gaps.append("gates humanos incompletos")
    return result


def dimension_6() -> DimensionResult:
    """Cobertura de skills: ¿existen skills para las tareas recurrentes reales?"""
    result = DimensionResult(6, 0)
    count = skill_count()
    if count >= 7:
        result.score = 4
        result.evidence.append(f"{count} skills: cubre spec, tareas, verificación, seguridad y cambio de modelo")
    elif count >= 4:
        result.score = 2
        result.evidence.append(f"{count} skills cubren el ciclo básico")
        result.gaps.append("faltan skills para tareas recurrentes (seguridad, ADR, cambio de modelo)")
    elif count:
        result.score = 1
        result.evidence.append(f"{count} skill(s): cobertura mínima")
        result.gaps.append("cobertura insuficiente para operar sin improvisar")
    else:
        result.gaps.append("sin skills: todo el conocimiento procedimental vive en la conversación")
    return result


def dimension_7() -> DimensionResult:
    """Autonomía agéntica: ¿cuánto puede avanzar un agente sin humano?"""
    result = DimensionResult(7, 0)
    law = read(LAW_FILE)
    if "BLOQUEO" in law and "Escalado" in law:
        result.score += 2
        result.evidence.append("protocolo de bloqueo/escalado explícito (el agente sabe cuándo parar)")
    else:
        result.gaps.append("sin protocolo de bloqueo: el agente improvisa cuando falta información")

    if exists(".harness/routing.yaml"):
        routing = read(".harness/routing.yaml")
        if "non_retryable_errors" in routing:
            result.score += 1
            result.evidence.append("errores no reintentables clasificados (401/402/403/404)")
        if "on_balance_exhausted" in routing:
            result.score += 1
            result.evidence.append("gestión de saldo/cuota agotada → bloqueo, no reintento infinito")
    else:
        result.gaps.append("sin routing.yaml: los fallos del proveedor no tienen política")
    return result


def dimension_8() -> DimensionResult:
    """Generación de tests: ¿el harness exige y verifica test-first?"""
    result = DimensionResult(8, 0)
    developer = read(".agents/agents/sdd-developer.md")
    if "test" in developer.lower() and ("confirma el fallo" in developer or "que falla" in developer):
        result.score += 2
        result.evidence.append("el Developer debe escribir el test que falla antes de implementar")
    else:
        result.gaps.append("no se exige test-first en la fase de implementación")

    verifier = read(".agents/agents/sdd-verifier.md")
    if "Regresión" in verifier or "regresión" in verifier:
        result.score += 1
        result.evidence.append("el Verifier comprueba regresión y que no se debiliten tests (R7)")

    law = read(LAW_FILE)
    if "R7" in law and "tests" in law.lower():
        result.score += 1
        result.evidence.append("R7 en la ley: prohibido borrar o debilitar tests")
    else:
        result.gaps.append("no hay regla que impida debilitar tests para pasar el gate")
    return result


def dimension_9() -> DimensionResult:
    """Gates de CI/CD con IA: ¿el gate es ejecutable y bloquea de verdad?"""
    result = DimensionResult(9, 0)
    inert = inert_checks()

    if exists(GATE_FILE):
        passed, summary = run_gate()
        result.score += 2
        result.evidence.append(f"gate ejecutable `./init.sh` → {'PASS' if passed else 'FAIL'}: {summary}")
        if not passed:
            result.notes.append("el gate falla ahora mismo; revisar antes de delegar trabajo")
    else:
        result.gaps.append("sin init.sh: no hay gate ejecutable")

    config = read(CONFIG_FILE)
    if '"tests"' in config and '"lint"' in config:
        result.score += 1
        result.evidence.append("checks de lint/tests/formato/typecheck declarados en la configuración")

    if "guardrails" in read(GATE_FILE):
        result.score += 1
        result.evidence.append("el gate incluye verificación de integridad y secretos")
    else:
        result.gaps.append("el gate no comprueba secretos ni integridad del harness")

    # Un gate que pasa porque la mayoría de sus checks están inertes no es un gate:
    # es un semáforo en verde desconectado. Se penaliza explícitamente.
    if inert:
        penalizacion = 1 if len(inert) >= 2 else 0
        result.score = max(0, result.score - penalizacion)
        result.gaps.append(
            f"{len(inert)} check(s) INERTE(S): el gate pasa sin verificar nada real "
            "(un PASS así no debe contarse como 4/4)"
        )
        for item in inert:
            result.notes.append(item)
    return result


DIMENSIONS = [
    dimension_1,
    dimension_2,
    dimension_3,
    dimension_4,
    dimension_5,
    dimension_6,
    dimension_7,
    dimension_8,
    dimension_9,
]


def verdict(score: int) -> str:
    if score == 0:
        return "ausente"
    if score == 1:
        return "incipiente"
    if score == 2:
        return "parcial"
    if score == 3:
        return "sólido"
    return "completo"


def dash() -> str:
    """Guion largo si la salida lo admite; si no, guion simple."""
    return "—" if _supports_unicode() else "-"


def bar(score: int) -> str:
    """Barra de progreso; ASCII si la consola no puede representar bloques."""
    if _supports_unicode():
        return "█" * score + "░" * (MAX_SCORE - score)
    return "#" * score + "." * (MAX_SCORE - score)


def level(target: str, results: list[DimensionResult]) -> tuple[bool, list[str]]:
    total = sum(r.score for r in results)
    spec = TARGETS[target]
    met = [r.number for r in results if r.score >= 2]
    missing = [n for n in spec["must_have"] if n not in met]
    return total >= spec["min_total"] and not missing, [DIMENSION_NAMES[n] for n in missing]


def render_summary_table(results: list[DimensionResult]) -> list[str]:
    lines = ["## Resumen por dimensión", ""]
    lines.append("| # | Dimensión | Nivel | Puntuación |")
    lines.append("| :-- | :--- | :--- | :--- |")
    for r in results:
        lines.append(
            f"| {r.number} | {DIMENSION_NAMES[r.number]} | {verdict(r.score)} | "
            f"`{bar(r.score)}` {r.score}/{MAX_SCORE} |"
        )
    lines.append("")
    return lines


def render_levels(results: list[DimensionResult]) -> list[str]:    # Con un subconjunto de dimensiones el veredicto de nivel es engañoso:
    # faltarían dimensiones solo porque no se han evaluado, no porque fallen.
    if len(results) < len(DIMENSIONS):
        return [
            "## Lectura frente a los niveles objetivo",
            "",
            f"_Diagnóstico parcial: solo se evaluaron {len(results)} de {len(DIMENSIONS)} dimensiones. "
            "Ejecuta el diagnóstico completo para un veredicto de nivel válido._",
            "",
        ]
    lines = ["## Lectura frente a los niveles objetivo", ""]
    lines.append("| Nivel | Requisito | Estado |")
    lines.append("| :--- | :--- | :--- |")
    for target, spec in TARGETS.items():
        ok, missing = level(target, results)
        detail = f"≥ {spec['min_total']} puntos y dimensiones {spec['must_have']} en nivel ≥ parcial"
        if missing:
            detail += f" — faltan: {', '.join(missing)}"
        lines.append(f"| {target} | {detail} | {'✅ alcanzado' if ok else '❌ no alcanzado'} |")
    lines.append("")
    return lines


def render_details(results: list[DimensionResult]) -> list[str]:
    lines = ["## Detalle", ""]
    for r in results:
        lines.append(f"### {r.number}. {DIMENSION_NAMES[r.number]} — {verdict(r.score)} ({r.score}/{MAX_SCORE})")
        lines.append("")
        for title, items in (
            ("Evidencia", r.evidence),
            ("Carencias", r.gaps),
            ("Atención", r.notes),
        ):
            if not items:
                continue
            lines.append(f"**{title}**")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    return lines


def render_priorities(results: list[DimensionResult]) -> list[str]:
    weakened = [r for r in results if r.score <= 1]
    if not weakened:
        return []
    lines = ["## Prioridades (dimensiones en nivel ausente/incipiente)", ""]
    for r in weakened:
        action = r.gaps[0] if r.gaps else "sin carencias identificadas"
        lines.append(f"{r.number}. **{DIMENSION_NAMES[r.number]}** → {action}")
    lines.append("")
    return lines


def render(results: list[DimensionResult], as_of: str) -> str:
    """Compone el informe Markdown a partir de los resultados por dimensión."""
    total = sum(r.score for r in results)
    pct = round(100 * total / (MAX_SCORE * len(results)))
    lines: list[str] = []

    lines.append(f"# Auto-diagnóstico del harness — {as_of}")
    lines.append("")
    lines.append(
        "Informe generado automáticamente por `scripts/diagnose_harness.py`. "
        "Nueve dimensiones independientes: **un solo número agregado oculta más de lo que revela**."
    )
    lines.append("")
    lines.append(f"**Puntuación global**: {total}/{MAX_SCORE * len(results)} ({pct}%)")
    lines.append("")

    inert = inert_checks()
    if inert:
        lines.append("## ⚠ Checks inertes (verde falso)")
        lines.append("")
        lines.append(
            "Estos checks existen y reportan PASS, pero **no pueden verificar nada todavía**. "
            "La puntuación de la dimensión 9 ya está penalizada por ello."
        )
        lines.append("")
        for item in inert:
            lines.append(f"- {item}")
        lines.append("")

    lines += render_summary_table(results)
    lines += render_levels(results)
    lines += render_details(results)
    lines += render_priorities(results)

    lines.append("---")
    lines.append("")
    lines.append(
        "Advertencia operativa: introducir agentes de IA en un estado caótico **acelera el caos, "
        "no la entrega**. Si las dimensiones de contexto (1), workflow (3), governance (5) y gates (9) "
        "están por debajo de *parcial*, el patrón multiagente amplificará la desorganización en lugar "
        "de la productividad."
    )
    lines.append("")
    return "\n".join(lines)


def parse_dimension_arg(args: list[str]) -> int | None:
    """Extrae el número de dimensión de `--dimension N`, validándolo."""
    if "--dimension" not in args:
        return None
    try:
        value = int(args[args.index("--dimension") + 1])
    except (IndexError, ValueError):
        print("Uso: --dimension <1..9>", file=sys.stderr)
        raise SystemExit(EXIT_USAGE) from None
    if not MIN_DIMENSION <= value <= MAX_DIMENSION:
        print(f"Uso: --dimension <{MIN_DIMENSION}..{MAX_DIMENSION}>", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    return value


def render_json(results: list[DimensionResult], as_of: str) -> None:
    """Informe legible por máquina."""
    print(
        json.dumps(
            {
                "as_of": as_of,
                "total": sum(r.score for r in results),
                "max_total": MAX_SCORE * len(results),
                "dimensions": [
                    {
                        "number": r.number,
                        "name": DIMENSION_NAMES[r.number],
                        "score": r.score,
                        "level": verdict(r.score),
                        "evidence": r.evidence,
                        "gaps": r.gaps,
                    }
                    for r in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def render_console(results: list[DimensionResult], as_of: str) -> None:
    """Informe legible por humanos para la terminal."""
    color = os.isatty(sys.stdout.fileno())
    bold = "\033[1m" if color else ""
    off = "\033[0m" if color else ""
    bullet = "·" if _supports_unicode() else "-"

    print(f"{bold}== Auto-diagnóstico del harness (9 dimensiones) =={off}")
    print(f"Fecha: {as_of}\n")
    for r in results:
        print(
            f"  {r.number}. {DIMENSION_NAMES[r.number]:<32} "
            f"{bar(r.score)} {r.score}/{MAX_SCORE}  {verdict(r.score)}"
        )

    total = sum(r.score for r in results)
    maximum = MAX_SCORE * len(results)
    print(f"\n  {bold}Global: {total}/{maximum} ({round(100 * total / maximum)}%){off}\n")

    if len(results) < len(DIMENSIONS):
        print(f"  Diagnóstico parcial: {len(results)} de {len(DIMENSIONS)} dimensiones.")
        print("  El veredicto de nivel requiere el diagnóstico completo.\n")
    else:
        for target in TARGETS:
            ok, missing = level(target, results)
            status = "alcanzado" if ok else f"no alcanzado (faltan: {', '.join(missing) or dash()})"
            print(f"  {target}: {status}")
    weakened = [r for r in results if r.score <= 1]
    if weakened:
        print(f"\n  {bold}Prioridades:{off}")
        for r in weakened:
            print(f"    {bullet} {DIMENSION_NAMES[r.number]}: {r.gaps[0] if r.gaps else dash()}")
    print()


def main() -> int:
    args = sys.argv[1:]
    as_json = "--json" in args
    write = "--write" in args
    only = parse_dimension_arg(args)

    results = [factory() for factory in DIMENSIONS if only is None or factory().number == only]
    as_of = date.today().isoformat()

    if as_json:
        render_json(results, as_of)
        return 0

    render_console(results, as_of)

    if write:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(render(results, as_of), encoding="utf-8")
        print(f"Informe escrito en {REPORT_PATH.relative_to(ROOT)}")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
