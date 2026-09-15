#!/usr/bin/env python3
"""Valida la coherencia de la configuración del harness.

Comprueba que las cuatro capas (ley, definición de roles, configuración de
ejecución, adaptadores) son consistentes entre sí. Falla en lugar de advertir
cuando una incoherencia rompería una regla de `AGENTS.md`.

Uso:
    python scripts/validate_harness.py
    python scripts/validate_harness.py --json

Salida: 0 = coherente · 1 = incoherencias · 2 = bloqueo (config ilegible)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Windows redirige la salida en cp1252 (no UTF-8): los símbolos de marca pueden
# provocar UnicodeEncodeError. Se recuerda la codificación original para elegir
# símbolos representables, con degradación a ASCII.
_ORIGINAL_ENCODING = getattr(sys.stdout, "encoding", None) or "ascii"

try:  # pragma: no cover - red de seguridad
    sys.stdout.reconfigure(errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(errors="replace")  # type: ignore[attr-defined]
except (AttributeError, OSError, ValueError):  # pragma: no cover
    pass


def _supports_unicode() -> bool:
    """¿La salida original puede representar los símbolos de marca?"""
    try:
        "✘✔".encode(_ORIGINAL_ENCODING)
    except (UnicodeEncodeError, LookupError, TypeError):
        return False
    return True

# Rutas canónicas (evita literales duplicados y erratas).
LAW_FILE = "AGENTS.md"
CONFIG_FILE = "harness.config.json"
MODELS_FILE = ".harness/models.yaml"
PROVIDERS_FILE = ".harness/providers.yaml"
ROUTING_FILE = ".harness/routing.yaml"
POLICIES_FILE = ".agents/policies/permissions.yaml"
AGENTS_DIR = ".agents/agents"

EXPECTED_ROLES = [
    "sdd-init",
    "sdd-tech-lead",
    "sdd-developer",
    "sdd-verifier",
    "sdd-security-reviewer",
]

# Modelos locales permitidos solo en roles de bajo riesgo (Nivel 1).
ROLES_SIN_MODELO_LOCAL = {"sdd-verifier", "sdd-security-reviewer"}

MODEL_IN_PROMPT = re.compile(
    r"\b(gpt-[0-9][\w.\-]*|claude-[\w.\-]+|gemini-[\w.\-]+|qwen[\w.\-]*|"
    r"llama[\w.\-]*|mistral[\w.\-]*|deepseek-[\w.\-]+)\b",
    re.IGNORECASE,
)

SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{30,}|"
    r"(api[_-]?key|secret|token)\s*[:=]\s*[\"'][^\"']{16,})",
    re.IGNORECASE,
)


def read_text(relative: str) -> str:
    """Lee un archivo del repositorio; devuelve cadena vacía si no existe."""
    path = ROOT / relative
    return path.read_text(encoding="utf-8") if path.exists() else ""


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: int = 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def tick(self) -> None:
        self.checks += 1


def frontmatter(path: Path) -> dict[str, object]:
    """Extrae el frontmatter YAML de un archivo Markdown de agente/skill."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    data: dict[str, object] = {}
    current_list: list[str] | None = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(("  - ", "    - ")) and current_list is not None:
            current_list.append(line.split("- ", 1)[1].strip())
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip().strip("\"'")
        if value:
            data[key] = value
            current_list = None
        else:
            current_list = []
            data[key] = current_list
    return data


def body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :]
    return text


def check_base_artifacts(report: Report) -> None:
    """Comprueba que existen los artefactos base declarados en AGENTS.md §4."""
    for required in (
        LAW_FILE,
        CONFIG_FILE,
        "init.sh",
        MODELS_FILE,
        PROVIDERS_FILE,
        ROUTING_FILE,
        POLICIES_FILE,
    ):
        report.tick()
        if not (ROOT / required).exists():
            report.error(f"falta artefacto base: {required} (AGENTS.md §4)")


def check_roles_declared(report: Report, roles_cfg: dict) -> None:
    """Cada rol esperado debe tener modelo asignado y prompt en disco."""
    agents_dir = ROOT / AGENTS_DIR
    for role in EXPECTED_ROLES:
        report.tick()
        if role not in roles_cfg:
            report.error(f"rol '{role}' sin entrada en models.yaml")
        if not (agents_dir / f"{role}.md").exists():
            report.error(f"rol '{role}' sin prompt en {AGENTS_DIR}/{role}.md")


def _check_single_role(report: Report, role: str, cfg: object, provider_names: set[str]) -> None:
    """Valida la coherencia de un rol individual."""
    if not isinstance(cfg, dict):
        report.error(f"'{role}': la entrada debe ser un mapa con model/provider")
        return

    model = cfg.get("model")
    provider = cfg.get("provider")

    if not model:
        report.error(f"'{role}': sin campo 'model' (la asignación vive solo aquí)")
    if not provider:
        report.error(f"'{role}': sin campo 'provider'")
        return

    if provider not in provider_names:
        report.error(
            f"'{role}': proveedor '{provider}' no está definido en providers.yaml "
            f"(disponibles: {', '.join(sorted(provider_names)) or 'ninguno'})"
        )
    if provider == "local" and role in ROLES_SIN_MODELO_LOCAL:
        report.error(
            f"'{role}': Nivel 1 prohíbe modelos locales en este rol; "
            "la verificación exige el máximo criterio disponible"
        )

    reasoning = cfg.get("reasoning")
    if reasoning and reasoning not in {"low", "medium", "high"}:
        report.warn(f"'{role}': reasoning '{reasoning}' fuera de low|medium|high")

    fallback = cfg.get("fallback") or []
    if isinstance(fallback, list) and model in fallback:
        report.warn(f"'{role}': el fallback incluye el modelo principal")


def check_role_provider_pairs(report: Report, roles_cfg: dict, provider_names: set[str]) -> None:
    """Coherencia entre cada rol, su modelo y el proveedor declarado."""
    for role, cfg in roles_cfg.items():
        report.tick()
        _check_single_role(report, role, cfg, provider_names)


def check_layer_separation(report: Report, allowed_aliases: set[str]) -> None:
    """REGLA DE CAPAS: ningún prompt de rol puede mencionar un modelo concreto."""
    agents_dir = ROOT / AGENTS_DIR
    if not agents_dir.exists():
        report.error(f"falta el directorio {AGENTS_DIR}/")
        return

    lowered_aliases = {alias.lower() for alias in allowed_aliases}
    for prompt in sorted(agents_dir.glob("*.md")):
        report.tick()
        if "model" in frontmatter(prompt):
            report.error(
                f"{prompt.relative_to(ROOT)}: declara 'model' en el frontmatter. "
                "Viola la regla de capas (AGENTS.md §4): el modelo vive solo en models.yaml"
            )
        for match in MODEL_IN_PROMPT.finditer(body(prompt)):
            name = match.group(0)
            if name.lower() in lowered_aliases:
                continue
            report.error(
                f"{prompt.relative_to(ROOT)}: menciona el modelo '{name}' en el cuerpo. "
                "El prompt debe ser agnóstico de modelo"
            )
            break


def check_permissions(report: Report, permissions: dict) -> None:
    """Políticas de permisos presentes y con la restricción clave del Verifier."""
    pol_roles = permissions.get("roles") or {}
    for role in EXPECTED_ROLES:
        report.tick()
        if role not in pol_roles:
            report.warn(f"'{role}' no tiene política de permisos declarada")

    verifier_policy = pol_roles.get("sdd-verifier") or {}
    if not isinstance(verifier_policy, dict):
        return

    report.tick()
    if "edit" in (verifier_policy.get("allow") or []):
        report.error("'sdd-verifier' no puede tener 'edit' permitido: destruye la independencia")

    writable = verifier_policy.get("writable_paths") or []
    if isinstance(writable, list):
        for path in writable:
            if "verify.md" not in str(path):
                report.warn(f"'sdd-verifier' escribe '{path}'; se espera solo verify.md")


def check_law_rules(report: Report) -> None:
    """Las diez reglas de oro y la prohibición de auto-merge deben estar en la ley."""
    law = read_text(LAW_FILE)
    for rule in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"):
        report.tick()
        if rule not in law:
            report.error(f"{LAW_FILE}: falta la regla de oro {rule}")
    if "auto-merge" not in law.lower() and "auto_merge" not in law.lower():
        report.warn(f"{LAW_FILE}: no se menciona explícitamente la prohibición de auto-merge")


def check_skills_referenced(report: Report) -> None:
    """Las skills referenciadas por los roles deben existir, con frontmatter válido."""
    skills_dir = ROOT / ".agents" / "skills"
    skill_names = {p.parent.name for p in skills_dir.glob("*/SKILL.md")} if skills_dir.exists() else set()

    agents_dir = ROOT / AGENTS_DIR
    if agents_dir.exists():
        for prompt in sorted(agents_dir.glob("*.md")):
            for referenced in re.findall(r"skills/([a-z0-9\-]+)", body(prompt)):
                report.tick()
                if referenced not in skill_names:
                    report.error(
                        f"{prompt.relative_to(ROOT)}: referencia la skill '{referenced}' "
                        "que no existe en .agents/skills/"
                    )

    if not skills_dir.exists():
        return
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        report.tick()
        _check_single_skill(report, skill_file)


def _check_single_skill(report: Report, skill_file: Path) -> None:
    """Valida el frontmatter de una skill (nombre y descripción descubribles)."""
    fm = frontmatter(skill_file)
    folder = skill_file.parent.name

    if fm.get("name") != folder:
        report.error(
            f"{skill_file.relative_to(ROOT)}: 'name: {fm.get('name')}' "
            f"no coincide con la carpeta '{folder}' (fallo silencioso de descubrimiento)"
        )

    description = fm.get("description")
    if not description:
        report.error(f"{skill_file.relative_to(ROOT)}: sin 'description' (no será descubrible)")
    elif "use when" not in str(description).lower():
        report.warn(
            f"{skill_file.relative_to(ROOT)}: la description no incluye trigger "
            "'Use when...' — el agente puede no invocarla"
        )


def check_adapters_synced(report: Report, roles_cfg: dict) -> None:
    """Los adaptadores deben cubrir todos los modelos configurados."""
    configured = {str(c.get("model")) for c in roles_cfg.values() if isinstance(c, dict)}

    # Claude Code: allowlist explícita de modelos.
    report.tick()
    claude_settings = ROOT / ".claude" / "settings.json"
    if not claude_settings.exists():
        report.warn(".claude/settings.json ausente: ejecuta bash scripts/sync-adapters.sh")
    else:
        try:
            settings = json.loads(claude_settings.read_text(encoding="utf-8"))
            allowlist = set(settings.get("availableModels") or [])
            missing = configured - allowlist
            if missing:
                report.error(
                    "adaptadores desincronizados: estos modelos no están en la allowlist de "
                    f"Claude Code: {', '.join(sorted(missing))}. Ejecuta scripts/sync-adapters.sh"
                )
        except json.JSONDecodeError as exc:
            report.error(f".claude/settings.json no es JSON válido: {exc}")

    # GitHub Copilot: un agente por rol, con frontmatter válido.
    report.tick()
    copilot_dir = ROOT / ".github" / "agents"
    if not copilot_dir.exists():
        report.warn(".github/agents/ ausente: ejecuta bash scripts/sync-adapters.sh")
        return

    for role in EXPECTED_ROLES:
        agent_file = copilot_dir / f"{role}.agent.md"
        if not agent_file.exists():
            report.error(f"falta el agente de Copilot para '{role}': .github/agents/{role}.agent.md")
            continue
        fm = frontmatter(agent_file)
        if not fm.get("model"):
            report.error(f"{agent_file.relative_to(ROOT)}: sin campo 'model' en el frontmatter")
        if not fm.get("description"):
            report.error(f"{agent_file.relative_to(ROOT)}: sin 'description' (no será descubrible)")


def check_harness_config(report: Report) -> None:
    """Coherencia de las reglas duras declaradas en harness.config.json."""
    report.tick()
    try:
        cfg = json.loads((ROOT / CONFIG_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"{CONFIG_FILE} ilegible: {exc}")
        return

    gate = (cfg.get("verification") or {}).get("gate")
    if gate != "./init.sh":
        report.warn(f"{CONFIG_FILE}: el gate declarado es '{gate}', se espera './init.sh'")

    workflow = cfg.get("workflow") or {}
    if workflow.get("allowAutoMerge") is not False:
        report.error(f"{CONFIG_FILE}: allowAutoMerge debe ser false (R3)")
    if workflow.get("oneTaskPerCommit") is not True:
        report.error(f"{CONFIG_FILE}: oneTaskPerCommit debe ser true (R2)")

    protected = set((cfg.get("guardrails") or {}).get("protectedFiles") or [])
    if LAW_FILE not in protected or ".harness/**" not in protected:
        report.error(f"{CONFIG_FILE}: protectedFiles debe incluir {LAW_FILE} y .harness/** (R4)")


def check_no_secrets(report: Report) -> None:
    """R9: ninguna credencial en claro en la configuración del harness."""
    candidates = list((ROOT / ".harness").glob("*.yaml")) + [
        ROOT / CONFIG_FILE,
        ROOT / POLICIES_FILE,
    ]
    for candidate in candidates:
        report.tick()
        if not candidate.exists():
            continue
        if SECRET_PATTERN.search(candidate.read_text(encoding="utf-8")):
            report.error(f"{candidate.relative_to(ROOT)}: posible credencial en claro (R9)")


def validate(report: Report) -> None:
    """Ejecuta todas las comprobaciones de coherencia del harness."""
    check_base_artifacts(report)

    try:
        models = harness_yaml.load(str(ROOT / MODELS_FILE))
        providers = harness_yaml.load(str(ROOT / PROVIDERS_FILE))
        routing = harness_yaml.load(str(ROOT / ROUTING_FILE))
    except (OSError, ValueError) as exc:
        report.error(f"BLOQUEO: no se pudo leer la configuración: {exc}")
        return

    roles_cfg = models.get("roles") or {}
    if not isinstance(roles_cfg, dict) or not roles_cfg:
        report.error(f"BLOQUEO: {MODELS_FILE} no define 'roles'")
        return

    try:
        permissions = harness_yaml.load(str(ROOT / POLICIES_FILE))
    except (OSError, ValueError) as exc:
        report.error(f"no se pudo leer {POLICIES_FILE}: {exc}")
        permissions = {}

    alias_block = routing.get("aliases") or {}
    allowed_aliases: set[str] = set()
    for cli_cfg in alias_block.values():
        if isinstance(cli_cfg, dict):
            allowed_aliases.update(k for k in cli_cfg if not k.endswith("_map"))

    check_roles_declared(report, roles_cfg)
    check_role_provider_pairs(report, roles_cfg, set((providers.get("providers") or {}).keys()))
    check_layer_separation(report, allowed_aliases)
    check_permissions(report, permissions)
    check_law_rules(report)
    check_skills_referenced(report)
    check_adapters_synced(report, roles_cfg)
    check_harness_config(report)
    check_no_secrets(report)


def render_json(report: Report) -> None:
    """Informe legible por máquina."""
    print(
        json.dumps(
            {
                "checks": report.checks,
                "errors": report.errors,
                "warnings": report.warnings,
                "coherent": not report.errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def render_text(report: Report) -> int:
    """Informe legible por humanos. Devuelve el código de salida."""
    color = os.isatty(sys.stdout.fileno())
    red = "\033[31m" if color else ""
    green = "\033[32m" if color else ""
    yellow = "\033[33m" if color else ""
    bold = "\033[1m" if color else ""
    off = "\033[0m" if color else ""

    print(f"{bold}== Validación del harness =={off}")
    print(f"  Comprobaciones: {report.checks}")
    print(f"  Parser YAML: {harness_yaml.backend()}")
    print()

    mark_error = "✘" if _supports_unicode() else "x"
    for warning in report.warnings:
        print(f"  {yellow}!{off} {warning}")
    for error in report.errors:
        print(f"  {red}{mark_error}{off} {error}")
    print()

    if report.errors:
        print(f"{bold}{red}== INVÁLIDO: {len(report.errors)} incoherencia(s) =={off}")
        return 1

    print(f"{bold}{green}== COHERENTE =={off}")
    if report.warnings:
        print(f"Advertencias: {len(report.warnings)} (no bloquean)")
    return 0


def main() -> int:
    report = Report()
    validate(report)

    if "--json" in sys.argv:
        render_json(report)
        return 1 if report.errors else 0
    return render_text(report)


if __name__ == "__main__":
    sys.exit(main())
