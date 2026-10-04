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
SKILLS_DIR = ".agents/skills"
VERSION_FILE = ".harness/harness.version"

# Artefactos cuya version declara el manifiesto, y donde vive esa version.
# La clave es la que usa `.harness/harness.version` -> declared.
VERSIONED_ARTIFACTS = {
    "agents_contract": LAW_FILE,
    "config": CONFIG_FILE,
    "models": MODELS_FILE,
    "providers": PROVIDERS_FILE,
    "routing": ROUTING_FILE,
}

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# El orquestador es el único rol cuya definición ES la skill: no tiene prompt
# propio en .agents/agents/, así que se auto-consume y no puede ser huérfana.
ORCHESTRATOR_SKILL = "sdd-orchestrator"

# Skills cuyo OBJETO es el modelo, no su consumidor. `model-switching` explica
# cómo cambiar el modelo de un rol: citar nombres de modelo es su contenido, no
# un acoplamiento. La regla de agnosticismo protege el conocimiento
# procedimental de los roles, no la documentación sobre modelos.
MODEL_SCOPED_SKILLS = {"model-switching"}

# Roles que NO producen artefactos propios: entregan su informe a otro rol.
# Se eximen del check de `edit` porque escribir no es su trabajo, no por olvido.
ROLES_WITHOUT_OWN_ARTIFACT = {"sdd-security-reviewer"}

# Compromisos que init.sh DEBE conservar. Es el unico gate (R6), y desde 2026-10-04 el
# rol harness-maintainer puede escribir en el (ADR-017). Este check compensa el permiso:
# el archivo es escribible, pero no se puede vaciar en silencio.
INIT_SH_REQUIRED_CHECKS = (
    "secrets",
    "lint",
    "format",
    "typecheck",
    "tests",
    "harness",
    "guardrails",
)

# Rutas que cada rol debe seguir teniendo vetadas, y en cual. Se comprueba que siguen
# protegidas tras ampliar el alcance del maintainer.
ALWAYS_PROTECTED_FOR_MAINTAINER = ("AGENTS.md", ".github/workflows/**")

MAINTAINER_ROLE = "harness-maintainer"

# Solo el maintainer puede escribir aqui; ningun otro rol puede declararlo.
HARNESS_WRITE_PREFIXES = ("scripts/", ".harness/", ".agents/")

# Ni siquiera el maintainer puede escribir la ley ni CI (ADR-007).
LAW_PATHS_NEVER_WRITABLE = ("AGENTS.md", ".github/workflows/**")
# Unicas rutas de global_deny que admiten una excepcion, y solo para el maintainer.
MAINTAINER_EXCEPTION_PATTERNS = {".harness/**", ".agents/**"}

EXPECTED_ROLES = [
    "sdd-init",
    "sdd-tech-lead",
    "sdd-developer",
    "sdd-verifier",
    "sdd-security-reviewer",
    MAINTAINER_ROLE,
]

# Referencia oficial de VS Code (Agent Skills): campos ADMITIDOS en el
# frontmatter de SKILL.md. Un campo desconocido aquí no da error: produce un
# fallo silencioso de descubrimiento. Por eso el vínculo inverso (qué rol usa
# cada skill) se DERIVA del campo `skills:` de los roles, en vez de declararse
# en la skill.
SKILL_FRONTMATTER_KEYS = {
    "name",
    "description",
    "argument-hint",
    "user-invocable",
    "disable-model-invocation",
}

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


def _catalog_ids(entry: object) -> tuple[set[str], set[str]]:
    """Extrae (ids, ids_de_extension) de la entrada de catálogo de un runtime."""
    ids: set[str] = set()
    from_extension: set[str] = set()

    if isinstance(entry, dict):
        items = entry.get("models") or []
    elif isinstance(entry, list):
        items = entry
    else:
        return ids, from_extension

    for item in items:
        if isinstance(item, dict):
            model_id = item.get("id")
            if not model_id:
                continue
            ids.add(str(model_id))
            if str(item.get("provided_by", "")).startswith("extension:"):
                from_extension.add(str(model_id))
        elif item:
            ids.add(str(item))

    return ids, from_extension


def runtime_catalog(models: dict) -> tuple[str, set[str], set[str]]:
    """Devuelve (runtime, ids válidos, ids aportados por extensión).

    El catálogo válido es el del RUNTIME que ejecuta los agentes, y tiene DOS
    procedencias que hay que considerar juntas:
      - nativos: los sirve el propio GitHub Copilot
      - de extensión: los aporta una extensión vía languageModelChatProviders
    Mirar solo los nativos lleva a concluir por error que un modelo no existe.
    """
    runtime = str(models.get("active_runtime") or "")
    catalog = models.get("catalog") or {}
    entry = catalog.get(runtime) if isinstance(catalog, dict) else None
    ids, from_extension = _catalog_ids(entry)
    return runtime, ids, from_extension


def _check_role_catalog(
    report: Report,
    role: str,
    provided: str,
    runtime: str,
    valid_ids: set[str],
    from_extension: set[str],
    declares_provider: bool,
) -> None:
    """Comprueba que el modelo del rol existe en el catálogo del runtime."""
    if not valid_ids:
        return

    if provided not in valid_ids:
        report.error(
            f"'{role}': el modelo '{provided}' no está en el catálogo del runtime "
            f"'{runtime}'. Válidos: {', '.join(sorted(valid_ids))}"
        )
        return

    # Un modelo de extensión solo se valida si queda registrado de dónde sale.
    if provided in from_extension and not declares_provider:
        report.warn(
            f"'{role}': '{provided}' lo aporta una extensión de terceros, no el "
            "catálogo nativo. Declarar 'provided_by' en models.yaml."
        )


def _check_role_fallbacks(
    report: Report, role: str, model: str, fallback: object, runtime: str, valid_ids: set[str]
) -> None:
    """Valida la lista de reserva de un rol."""
    if not isinstance(fallback, list):
        return

    if model in fallback:
        report.warn(f"'{role}': el fallback incluye el modelo principal")

    for alt in fallback:
        if valid_ids and str(alt) not in valid_ids:
            report.warn(
                f"'{role}': el fallback '{alt}' tampoco está en el catálogo de "
                f"'{runtime}'; no serviría si el principal falla"
            )


def _check_single_role(
    report: Report,
    role: str,
    cfg: object,
    runtime: str,
    valid_ids: set[str],
    from_extension: set[str],
) -> None:
    """Valida un rol contra el catálogo del runtime, con su procedencia."""
    if not isinstance(cfg, dict):
        report.error(f"'{role}': la entrada debe ser un mapa con model/runtime")
        return

    model = cfg.get("model")
    if not model:
        report.error(f"'{role}': sin campo 'model' (la asignación vive solo aquí)")
        return

    # Un modelo de extensión lleva el nombre cualificado en `model` y el id
    # limpio en `model_id`: hay que validar contra el id.
    provided = str(cfg.get("model_id") or model)
    if (cfg.get("runtime") or runtime) == runtime:
        _check_role_catalog(
            report,
            role,
            provided,
            runtime,
            valid_ids,
            from_extension,
            declares_provider=bool(cfg.get("provided_by")),
        )

    reasoning = cfg.get("reasoning")
    if reasoning and reasoning not in {"low", "medium", "high"}:
        report.warn(f"'{role}': reasoning '{reasoning}' fuera de low|medium|high")

    _check_role_fallbacks(report, role, str(model), cfg.get("fallback"), runtime, valid_ids)


def check_role_provider_pairs(report: Report, roles_cfg: dict, models: dict) -> None:
    """Coherencia entre cada rol y el catálogo del runtime activo."""
    runtime, valid_ids, from_extension = runtime_catalog(models)
    if not runtime:
        report.error("models.yaml: falta 'active_runtime' (¿qué runtime ejecuta los agentes?)")
    elif not valid_ids:
        report.error(f"models.yaml: 'catalog.{runtime}.models' está vacío o mal formado")

    for role, cfg in roles_cfg.items():
        report.tick()
        _check_single_role(report, role, cfg, runtime, valid_ids, from_extension)


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

    # Simetría para skills: el conocimiento procedimental tampoco nombra modelos.
    # Una skill con un nombre de modelo dentro se vuelve inaplicable al cambiar
    # de modelo, que es justo lo que la regla de capas evita.
    skills_dir = ROOT / SKILLS_DIR
    if not skills_dir.exists():
        return
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        report.tick()
        if "model" in frontmatter(skill_file):
            report.error(
                f"{skill_file.relative_to(ROOT)}: declara 'model' en el frontmatter; "
                "no es un campo admitido y la skill debe ser agnóstica de modelo"
            )
        if skill_file.parent.name in MODEL_SCOPED_SKILLS:
            continue  # su objeto es el modelo: los nombres son datos, no acoplamiento
        for match in MODEL_IN_PROMPT.finditer(body(skill_file)):
            name = match.group(0)
            if name.lower() in lowered_aliases:
                continue
            report.error(
                f"{skill_file.relative_to(ROOT)}: menciona el modelo '{name}'. "
                "La skill debe ser agnóstica de modelo (AGENTS.md §4)"
            )
            break


def check_permissions(report: Report, permissions: dict) -> None:
    """Políticas de permisos presentes y con la restricción clave del Verifier.

    El Verifier SÍ necesita `edit`: es la tool de escritura y debe redactar `verify.md`.
    Lo que preserva su independencia es que `writable_paths` lo limite a ese ÚNICO
    artefacto, de modo que no pueda tocar el código que verifica.

    Antes este check exigía lo contrario ("no puede tener 'edit'"), lo que hacía al
    Verifier incapaz de producir su artefacto. Corregido el 2026-09-28.
    """
    pol_roles = permissions.get("roles") or {}
    for role in EXPECTED_ROLES:
        report.tick()
        if role not in pol_roles:
            report.warn(f"'{role}' no tiene política de permisos declarada")

    verifier_policy = pol_roles.get("sdd-verifier") or {}
    if not isinstance(verifier_policy, dict):
        return

    report.tick()
    writable = verifier_policy.get("writable_paths") or []
    if not isinstance(writable, list):
        return

    if not writable:
        report.error(
            "'sdd-verifier' no declara `writable_paths`: sin escritura acotada a verify.md "
            "no puede producir su artefacto"
        )
        return

    outside = [str(p) for p in writable if "verify.md" not in str(p)]
    if outside:
        report.error(
            "'sdd-verifier' declara rutas de escritura fuera de verify.md: "
            f"{', '.join(outside)}. Escribir código destruye la independencia"
        )


def check_init_gate_integrity(report: Report) -> None:
    """init.sh es el unico gate (R6): debe conservar sus comprobaciones obligatorias.

    Desde ADR-017 el rol `harness-maintainer` PUEDE escribir en init.sh (es la unica forma
    de anadirle ramas de stack que el desconocia, como la de PHP). Ese permiso podria usarse
    para VACIAR el gate en lugar de ampliarlo, que es lo que R6 prohibe.

    Este check convierte esa garantia en mecanismo: el archivo es modificable, pero no puede
    perder ninguna de sus comprobaciones. Mismo principio que ADR-015: el check mira algo
    distinto de si mismo.
    """
    path = ROOT / "init.sh"
    report.tick()
    if not path.exists():
        report.error("falta init.sh: es el unico gate del harness (R6)")
        return

    text = path.read_text(encoding="utf-8")

    for check in INIT_SH_REQUIRED_CHECKS:
        report.tick()
        if not re.search(rf'\brecord\s+"{re.escape(check)}"', text):
            report.error(
                f"init.sh: no declara la comprobacion obligatoria '{check}' (R6). "
                "El gate no puede perder checks: si hay que anadir, se anade; si hay que "
                "desactivar, se escala a un humano"
            )

    report.tick()
    if "exit" not in text:
        report.error("init.sh no termina con un codigo de salida: el gate debe poder fallar")


def check_harness_maintainer_limits(report: Report, permissions: dict) -> None:
    """ADR-007: solo el maintainer escribe en el harness, y nunca la ley ni CI.

    Un limite es real cuando es capacidad ausente, no una instruccion: se comprueba que
    ningun otro rol declare escritura en el harness y que la excepcion de global_deny
    no se amplie mas alla de .harness/** y .agents/** ni a otros roles.
    """
    pol_roles = permissions.get("roles") or {}

    for role, policy in pol_roles.items():
        if role == MAINTAINER_ROLE or not isinstance(policy, dict):
            continue
        report.tick()
        leaked = [
            str(p)
            for p in (policy.get("writable_paths") or [])
            if str(p).startswith(HARNESS_WRITE_PREFIXES)
        ]
        if leaked:
            report.error(
                f"'{role}': declara escritura en el harness ({', '.join(leaked)}). "
                f"Solo '{MAINTAINER_ROLE}' puede (ADR-007)"
            )

    policy = pol_roles.get(MAINTAINER_ROLE)
    report.tick()
    if not isinstance(policy, dict):
        report.error(f"'{MAINTAINER_ROLE}' no tiene politica en {POLICIES_FILE}")
        return

    writable = {str(p) for p in (policy.get("writable_paths") or [])}
    protected = {str(p) for p in (policy.get("protected_paths") or [])}
    for path in LAW_PATHS_NEVER_WRITABLE:
        report.tick()
        if path in writable:
            report.error(f"'{MAINTAINER_ROLE}': tiene '{path}' en writable_paths; la ley y CI son solo humanas")
        if path not in protected:
            report.error(f"'{MAINTAINER_ROLE}': falta '{path}' en protected_paths")

    for entry in (permissions.get("global_deny") or {}).get("paths") or []:
        if not isinstance(entry, dict) or not entry.get("except_roles"):
            continue
        report.tick()
        pattern = str(entry.get("pattern"))
        if pattern not in MAINTAINER_EXCEPTION_PATTERNS:
            report.error(f"global_deny: la ruta '{pattern}' no admite excepciones de rol (ADR-007)")
        others = [str(r) for r in entry["except_roles"] if str(r) != MAINTAINER_ROLE]
        if others:
            report.error(
                f"global_deny '{pattern}': la excepcion solo puede ser '{MAINTAINER_ROLE}', "
                f"no {', '.join(others)}"
            )


def check_law_rules(report: Report) -> None:
    """Las diez reglas de oro y la prohibición de auto-merge deben estar en la ley."""
    law = read_text(LAW_FILE)
    for rule in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"):
        report.tick()
        if rule not in law:
            report.error(f"{LAW_FILE}: falta la regla de oro {rule}")
    if "auto-merge" not in law.lower() and "auto_merge" not in law.lower():
        report.warn(f"{LAW_FILE}: no se menciona explícitamente la prohibición de auto-merge")


def _declared_skills(prompt: Path) -> set[str]:
    """Skills declaradas en el frontmatter (`skills:`) de un rol."""
    raw = frontmatter(prompt).get("skills")
    if isinstance(raw, list):
        return {str(item).strip() for item in raw if str(item).strip()}
    if isinstance(raw, str) and raw.strip():
        return {part.strip() for part in raw.strip("[]").split(",") if part.strip()}
    return set()


def _cited_skills(text: str) -> set[str]:
    """Skills citadas en el cuerpo de un prompt como `skills/<nombre>`."""
    return set(re.findall(r"skills/([a-z0-9\-]+)", text))


def check_skills_referenced(report: Report) -> None:
    """Coherencia agente ↔ skill: declaración, uso efectivo y cobertura.

    El vínculo se declara UNA sola vez, en el campo `skills:` del rol, y la
    relación inversa se DERIVA. No se escribe `used_by` en la skill: el
    frontmatter de SKILL.md solo admite campos concretos y uno desconocido es un
    fallo silencioso de descubrimiento (ver ADR-003).

    Se comprueba que: (a) lo declarado existe; (b) lo citado en el procedimiento
    está declarado; (c) ninguna skill queda huérfana; (d) el frontmatter de cada
    skill solo usa campos admitidos.
    """
    agents_dir = ROOT / AGENTS_DIR
    skills_dir = ROOT / SKILLS_DIR
    existing = _skill_names(skills_dir)

    declared_by: dict[str, set[str]] = {}
    corpus: list[str] = [read_text(POLICIES_FILE), read_text("init.sh"), read_text(LAW_FILE)]

    if agents_dir.exists():
        for prompt in sorted(agents_dir.glob("*.md")):
            role_body = body(prompt)
            corpus.append(role_body)
            declared = _declared_skills(prompt)
            declared_by[prompt.stem] = declared

            for name in sorted(declared):
                report.tick()
                if name not in existing:
                    report.error(
                        f"{prompt.relative_to(ROOT)}: declara la skill '{name}' en "
                        f"'skills:', pero no existe en {SKILLS_DIR}/"
                    )

            for cited in sorted(_cited_skills(role_body)):
                report.tick()
                if cited not in declared:
                    report.error(
                        f"{prompt.relative_to(ROOT)}: cita 'skills/{cited}' en el "
                        "procedimiento pero no lo declara en 'skills:'; en arranque en "
                        "frío ese vínculo no existe"
                    )
    else:
        report.error(f"falta el directorio {AGENTS_DIR}/")

    if not skills_dir.exists():
        report.error(f"falta el directorio {SKILLS_DIR}/")
        return

    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        corpus.append(skill_file.read_text(encoding="utf-8"))
    all_text = "\n".join(corpus)

    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        report.tick()
        _check_single_skill(report, skill_file)

        name = skill_file.parent.name
        if name == ORCHESTRATOR_SKILL:
            continue  # su rol es ella misma: no depende de un prompt de agente

        report.tick()
        consumers = {r for r, names in declared_by.items() if name in names}
        mentioned = re.search(rf"\b{re.escape(name)}\b", all_text) is not None
        if not consumers and not mentioned:
            report.warn(
                f"{SKILLS_DIR}/{name}/: ninguna skill declarada la usa ni se menciona "
                "en el harness. ¿Huérfana? Declararla en el 'skills:' de su rol"
            )


def _skill_names(skills_dir: Path) -> set[str]:
    """Nombres de las skills realmente descubribles (carpeta con SKILL.md)."""
    if not skills_dir.exists():
        return set()
    return {p.parent.name for p in skills_dir.glob("*/SKILL.md")}


def _check_single_skill(report: Report, skill_file: Path) -> None:
    """Valida el frontmatter de una skill (descubrible y sin campos ajenos)."""
    fm = frontmatter(skill_file)
    folder = skill_file.parent.name

    if fm.get("name") != folder:
        report.error(
            f"{skill_file.relative_to(ROOT)}: 'name: {fm.get('name')}' "
            f"no coincide con la carpeta '{folder}' (fallo silencioso de descubrimiento)"
        )

    extra = sorted(set(fm) - SKILL_FRONTMATTER_KEYS)
    if extra:
        report.warn(
            f"{skill_file.relative_to(ROOT)}: campo(s) no admitido(s) en el frontmatter: "
            f"{', '.join(extra)}. VS Code solo admite "
            f"{', '.join(sorted(SKILL_FRONTMATTER_KEYS))}"
        )

    description = fm.get("description")
    if not description:
        report.error(f"{skill_file.relative_to(ROOT)}: sin 'description' (no será descubrible)")
    elif "use when" not in str(description).lower():
        report.warn(
            f"{skill_file.relative_to(ROOT)}: la description no incluye trigger "
            "'Use when...' — el agente puede no invocarla"
        )


def check_role_tools_consistency(report: Report, permissions: dict) -> None:
    """Un rol DEBE poder escribir el artefacto que declara producir.

    Defecto real detectado el 2026-09-28: `sdd-init`, `sdd-tech-lead` y `sdd-verifier`
    declaraban un `outputs` (scope.md, design.md, verify.md) pero tenian `edit` en `deny`
    y no en `tools`, asi que NO podian escribir su propio artefacto. Las fases init,
    design y verify eran inejecutables, y nada lo comprobaba.

    La causa: se uso `edit` (la tool de escritura) para expresar "no editar CODIGO",
    una restriccion que `writable_paths` ya expresa. La tool es la capacidad; la lista
    de rutas es el limite.
    """
    agents_dir = ROOT / AGENTS_DIR
    if not agents_dir.exists():
        return

    pol_roles = permissions.get("roles") or {}

    for prompt in sorted(agents_dir.glob("*.md")):
        fm = frontmatter(prompt)
        role = prompt.stem
        outputs = fm.get("outputs")
        if not outputs:
            continue  # un rol sin artefacto propio no necesita escribir

        report.tick()
        tools = fm.get("tools") if isinstance(fm.get("tools"), list) else []
        tools = [str(t) for t in tools]
        if role in ROLES_WITHOUT_OWN_ARTIFACT:
            if "edit" in tools:
                report.warn(
                    f"{prompt.relative_to(ROOT)}: rol de solo informe, pero declara la tool `edit`. "
                    "Si no escribe artefactos propios, no la necesita"
                )
            continue
        if "edit" not in tools:
            report.error(
                f"{prompt.relative_to(ROOT)}: declara `outputs` ({', '.join(str(o) for o in outputs)})"
                " pero su lista `tools` no incluye `edit`: NO puede escribir su propio artefacto. "
                "La restriccion de donde escribe la impone `writable_paths`, no la ausencia de la tool"
            )

        policy = pol_roles.get(role)
        if not isinstance(policy, dict):
            continue

        report.tick()
        allow = [str(t) for t in (policy.get("allow") or [])]
        deny = [str(t) for t in (policy.get("deny") or [])]
        writable = policy.get("writable_paths") or []

        if "edit" not in allow and writable:
            report.error(
                f"'{role}': declara `writable_paths` ({', '.join(str(w) for w in writable)})"
                " pero no tiene `edit` en su lista `allow`: la politica y el contrato se contradicen"
            )

        if "edit" in deny and writable:
            report.error(
                f"'{role}': `deny` incluye `edit` y a la vez declara `writable_paths`. "
                "Contradiccion: no puede escribir nada de lo que declara. "
                "Usa `writable_paths` para acotar el alcance, no `deny: edit`"
            )


def copilot_name_map(alias_block: dict) -> set[str]:
    """Nombres de modelo válidos en el selector de Copilot (valores del model_map)."""
    copilot = alias_block.get("copilot") if isinstance(alias_block, dict) else None
    if not isinstance(copilot, dict):
        return set()
    model_map = copilot.get("model_map")
    if not isinstance(model_map, dict):
        return set()
    return {str(v) for v in model_map.values()}


def check_adapters_synced(report: Report, roles_cfg: dict, alias_block: dict) -> None:
    """Los adaptadores deben cubrir todos los modelos configurados."""
    configured = {str(c.get("model")) for c in roles_cfg.values() if isinstance(c, dict)}

    # GitHub Copilot: un agente por rol, con frontmatter válido. El `model` debe
    # coincidir con el nombre cualificado que traduce routing.yaml, porque el
    # frontmatter no acepta el slug pelado de un modelo de extensión.
    report.tick()
    copilot_dir = ROOT / ".github" / "agents"
    if not copilot_dir.exists():
        report.warn(".github/agents/ ausente: ejecuta bash scripts/sync-adapters.sh")
        return

    copilot_names = copilot_name_map(alias_block)

    for role in EXPECTED_ROLES:
        agent_file = copilot_dir / f"{role}.agent.md"
        if not agent_file.exists():
            report.error(f"falta el agente de Copilot para '{role}': .github/agents/{role}.agent.md")
            continue
        fm = frontmatter(agent_file)
        model = fm.get("model")
        if not model:
            report.error(f"{agent_file.relative_to(ROOT)}: sin campo 'model' en el frontmatter")
        elif copilot_names and str(model) not in copilot_names:
            report.error(
                f"{agent_file.relative_to(ROOT)}: el modelo '{model}' no está en "
                "aliases.copilot.model_map (.harness/routing.yaml). "
                f"Válidos: {', '.join(sorted(copilot_names))}"
            )
        if not fm.get("description"):
            report.error(f"{agent_file.relative_to(ROOT)}: sin 'description' (no será descubrible)")

    # Claude Code: allowlist explícita de modelos.
    report.tick()
    claude_settings = ROOT / ".claude" / "settings.json"
    if not claude_settings.exists():
        report.warn(".claude/settings.json ausente: ejecuta bash scripts/sync-adapters.sh")
        return
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


def semver_valid(value: str) -> bool:
    """¿La cadena es un semver MAJOR.MINOR.PATCH?"""
    return bool(SEMVER.match(value))


def _artifact_version(artifact: str, relative: str) -> str | None:
    """Version que un artefacto declara REALMENTE, en su propio formato.

    Cada artefacto guarda su version a su manera (cabecera markdown, JSON, YAML),
    asi que no vale un unico parser para los cinco.
    """
    path = ROOT / relative
    if not path.exists():
        return None

    if artifact == "config":
        try:
            return str(json.loads(path.read_text(encoding="utf-8")).get("version") or "") or None
        except (OSError, json.JSONDecodeError):
            return None

    if artifact == "agents_contract":
        match = re.search(r"Versi[óo]n del contrato:\s*`([^`]+)`", path.read_text(encoding="utf-8"))
        return match.group(1).strip() if match else None

    try:
        return str(harness_yaml.load(str(path)).get("version") or "") or None
    except (OSError, ValueError):
        return None


def check_harness_version(report: Report) -> None:
    """ADR-004: una sola version del harness que no diverja de sus artefactos.

    Tres invariantes: (a) `harness` es semver valido; (b) cada artefacto tiene
    entrada en `declared`; (c) la version REAL del artefacto coincide con la
    declarada. El (c) es el que aporta el valor: detecta cambiar un artefacto SIN
    registrarlo, que es la divergencia real. Sin el, el manifiesto solo se validaria
    a si mismo y seria documentacion, no un control.
    """
    path = ROOT / VERSION_FILE
    report.tick()
    if not path.exists():
        report.error(
            f"falta {VERSION_FILE}: sin version del harness no se puede fijar al instanciar (ADR-004)"
        )
        return

    try:
        data = harness_yaml.load(str(path))
    except (OSError, ValueError) as exc:
        report.error(f"{VERSION_FILE} ilegible: {exc}")
        return

    report.tick()
    harness = str(data.get("harness") or "").strip()
    if not semver_valid(harness):
        report.error(
            f"{VERSION_FILE}: 'harness: {harness}' no es semver valido (MAJOR.MINOR.PATCH)"
        )

    declared = data.get("declared")
    if not isinstance(declared, dict):
        report.error(f"{VERSION_FILE}: falta el mapa 'declared' con la version de cada artefacto")
        return

    for artifact, relative in VERSIONED_ARTIFACTS.items():
        report.tick()
        if artifact not in declared:
            report.error(f"{VERSION_FILE}: 'declared' no incluye '{artifact}' ({relative})")
            continue

        expected = str(declared[artifact]).strip()
        actual = _artifact_version(artifact, relative)
        if actual is None:
            report.error(f"{relative}: no se pudo leer su version (¿cambio el formato?)")
        elif actual != expected:
            report.error(
                f"{relative}: declara la version {actual}, pero {VERSION_FILE} dice {expected} "
                f"para '{artifact}'. Actualiza el manifiesto en el mismo cambio (ADR-004)"
            )

    for artifact in sorted(set(declared) - set(VERSIONED_ARTIFACTS)):
        report.warn(
            f"{VERSION_FILE}: 'declared' incluye '{artifact}', que no corresponde a ningun "
            "artefacto conocido. ¿Se renombro sin actualizar el manifiesto?"
        )


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
    check_role_provider_pairs(report, roles_cfg, models)
    check_layer_separation(report, allowed_aliases)
    check_permissions(report, permissions)
    check_role_tools_consistency(report, permissions)
    check_harness_maintainer_limits(report, permissions)
    check_init_gate_integrity(report)
    check_law_rules(report)
    check_skills_referenced(report)
    check_adapters_synced(report, roles_cfg, alias_block)
    check_harness_config(report)
    check_harness_version(report)
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
