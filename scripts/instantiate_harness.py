#!/usr/bin/env python3
"""Instancia el harness en un repositorio nuevo (ADR-006, ADR-012).

Fabrica un repositorio de componente AUTOSUFICIENTE: ley, método, gate, `.spec/` propio y
procedencia registrada. El componente resultante contiene todo lo necesario para su
mantenimiento por cualquier actor, sin consultar el repositorio del harness.

Uso:
    python scripts/instantiate_harness.py --name auth-service --target a:\\proyectos\\auth-service
    python scripts/instantiate_harness.py --check a:\\proyectos\\auth-service

Salida: 0 = OK · 1 = fallo · 2 = bloqueo (precondición no cumplida)

Origen de los archivos (decisión D-1, opción D): se extrae del PROPIO árbol del harness con
`git archive HEAD`, que:
  - toma solo lo COMMITEADO (ignora cambios sin commitear)
  - no necesita red ni credenciales (el repo es privado: clonarlo exigiría un token, y R9
    prohíbe secretos en disco)
Por eso el primer paso es exigir el árbol limpio: si hay cambios sin commitear, lo extraído
no sería lo que se ve.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = "harness.config.json"
LAW_FILE = "AGENTS.md"
VERSION_FILE = ".harness/harness.version"
PROVENANCE_FILE = ".harness/instanced.json"
GENERATED_MARK = "<!-- GENERADO por scripts/instantiate_harness.py"

# Artefactos que NO viajan al componente: son del framework, no de la instancia.
# Llevarlos dentro seria arrastrar la historia de otro repositorio (ADR-012).
HARNESS_ONLY_PATHS = (
    ".spec/_harness",      # los ADR del framework
    ".spec/validator-runner",
    "docs",                # documentacion del framework, no del componente
)

# Secciones de la ley que un componente NO puede heredar tal cual.
IDENTITY_SECTION = "## 4. Estructura del repositorio (capas separadas)"


@dataclass
class Provenance:
    """De qué versión del harness nace una instancia."""

    harness: str
    commit: str

    def as_dict(self) -> dict[str, str]:
        return {"harness": self.harness, "commit": self.commit}


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando y devuelve el resultado, sin lanzar excepción."""
    return subprocess.run(
        args, cwd=str(cwd or ROOT), capture_output=True, text=True, check=False
    )


def die(message: str, code: int = 1) -> None:
    print(f"  ✘ {message}", file=sys.stderr)
    sys.exit(code)


def require_clean_tree() -> None:
    """Exige que no haya cambios en archivos RASTREADOS sin commitear.

    Solo se miran los cambios rastreados. Los archivos sin rastrear (`??`) no importan aquí:
    `git archive HEAD` extrae el COMMIT, así que nunca los incluiría — bloquear por ellos
    impediría instanciar en cualquier repo con archivos locales ignorados a propósito.
    """
    result = run(["git", "status", "--porcelain"])
    if result.returncode != 0:
        die("no se pudo consultar git status (¿es un repositorio git?)", 2)

    tracked_changes = [
        line for line in result.stdout.splitlines() if line.strip() and not line.startswith("??")
    ]
    if tracked_changes:
        detail = "\n     ".join(tracked_changes[:5])
        die(
            "hay cambios sin commitear en archivos rastreados, así que lo que se extraiga\n"
            f"     (el commit HEAD) no incluiría ese trabajo:\n     {detail}\n"
            "     Commitea o descarta esos cambios antes de instanciar.",
            2,
        )


def read_provenance() -> Provenance:
    """Versión del harness (semver) y commit exacto del que se extrae."""
    path = ROOT / VERSION_FILE
    if not path.exists():
        die(f"falta {VERSION_FILE}: sin versión no se puede fijar la procedencia (ADR-004)", 2)

    match = re.search(r'^harness:\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        die(f"{VERSION_FILE} no declara el campo 'harness'", 2)

    commit = run(["git", "rev-parse", "HEAD"])
    if commit.returncode != 0:
        die("no se pudo resolver el commit actual", 2)

    return Provenance(harness=match.group(1), commit=commit.stdout.strip())


def extract(target: Path) -> None:
    """Extrae lo commiteado del propio árbol, sin red ni credenciales.

    Se usa `git archive | tar -x` en lugar de `git clone` por dos motivos: el repositorio es
    privado (un clone exigiría credenciales, prohibidas en disco por R9) y `archive` toma
    exactamente el commit, sin historial ni referencias remotas.

    OJO: `git archive` produce un **tar binario**. Capturarlo como texto (`text=True`) falla
    al decodificar, así que se trabaja con bytes de principio a fin.
    """
    if target.exists() and any(target.iterdir()):
        die(f"el destino ya existe y no está vacío: {target}")

    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"], cwd=str(ROOT), capture_output=True, check=False
    )
    if archive.returncode != 0:
        die(f"git archive falló: {archive.stderr.decode('utf-8', errors='replace').strip()}")
    if not archive.stdout:
        die("git archive no devolvió contenido: ¿el commit HEAD está vacío?")

    target.mkdir(parents=True, exist_ok=True)

    extracted = subprocess.run(
        ["tar", "-x", "-C", str(target)], input=archive.stdout, capture_output=True, check=False
    )
    if extracted.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        die(
            "tar falló al extraer; se limpió el destino parcial: "
            f"{extracted.stderr.decode('utf-8', errors='replace').strip()}"
        )


def clean_inheritance(target: Path) -> list[str]:
    """Quita del componente lo que pertenece al framework, no a la instancia."""
    removed: list[str] = []
    for relative in HARNESS_ONLY_PATHS:
        path = target / relative
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(relative)

    # El .spec/ del componente arranca vacío: sus artefactos son suyos (ADR-012).
    spec = target / ".spec"
    if spec.exists():
        shutil.rmtree(spec)
    spec.mkdir()
    (spec / ".gitkeep").touch()
    return removed


def resolve_identity(target: Path, name: str, branch: str) -> None:
    """Reescribe la identidad del repositorio: nombre y rama por defecto."""
    path = target / CONFIG_FILE
    config = json.loads(path.read_text(encoding="utf-8"))
    repository = config.setdefault("repository", {})
    repository["name"] = name
    repository["defaultBranch"] = branch
    repository["protectedBranches"] = [branch]
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_component_section(name: str, prov: Provenance) -> str:
    """Sección §4 para un COMPONENTE: estructura propia, no la del framework.

    ADR-006: §4 deja de ser ley y pasa a ser parámetro, porque en un repositorio
    instanciado las rutas dependen del componente, no del método.
    """
    return f"""## 4. Estructura del repositorio (capas separadas)

```
{LAW_FILE}                   # ← este archivo. GENERADO, no editar a mano.
{CONFIG_FILE}         # Comandos detectados y gates de verificación.
init.sh                     # Gate ejecutable: lint + tests + typecheck.
.spec/                      # Artefactos SDD de ESTE componente (por feature).
.agents/                    # DEFINICIÓN de roles (agnóstica de modelo).
.harness/                   # CONFIGURACIÓN de ejecución (rol → modelo).
.github/agents/             # Adaptadores para GitHub Copilot en VS Code.
scripts/                    # Utilidades del harness instanciadas.
src/                        # Código de {name}.
tests/                      # Pruebas de {name}.
```

**Este repositorio es un COMPONENTE instanciado del harness, no el harness.**

- Su `.spec/` es **suyo**: describe el comportamiento de {name}.
- **Nunca** se escriben artefactos de {name} en el repositorio del harness.
- El contrato que exponga (si es un componente `cross`, ADR-013) es **suyo y versionado**;
  quien lo consuma lo referencia con pin, sin copiarlo (ADR-012).

**El repositorio del harness es otro.** Este árbol nació de él y quedó enlazado por su
procedencia; `harness.config.json` declara qué versión.

**Procedencia**: harness **{prov.harness}** · commit `{prov.commit[:12]}`

**Regla de capas (crítica):** la definición de rol (`.agents/agents/*.md`) **nunca** menciona un
nombre de modelo. La asignación vive **solo** en `.harness/models.yaml`.
"""


def generate_law(target: Path, name: str, prov: Provenance) -> None:
    """Genera el AGENTS.md: ley base + identidad del componente, marcado como no editable."""
    source = ROOT / LAW_FILE
    text = source.read_text(encoding="utf-8")

    start = text.find(IDENTITY_SECTION)
    if start == -1:
        die(f"no se encontró la sección '{IDENTITY_SECTION}' en {LAW_FILE}", 2)

    end = text.find("\n## 5.", start)
    if end == -1:
        die(f"no se encontró el final de la sección §4 en {LAW_FILE}", 2)

    header = (
        f"{GENERATED_MARK} — NO EDITAR A MANO.\n"
        f"     Componente: {name} · harness {prov.harness} (commit {prov.commit[:12]})\n"
        f"     Para cambiar su contenido, edita el harness y vuelve a instanciar.\n"
        f"     El proyecto puede cambiar sus PARÁMETROS ({CONFIG_FILE}), nunca sus REGLAS. -->\n"
    )

    generated = text[:start] + build_component_section(name, prov) + text[end:]

    # La cabecera de versión del contrato apunta al harness del que nace.
    generated = re.sub(
        r"^> Versión del contrato: .*$",
        f"> Versión del contrato: `{prov.harness}` (heredada del harness) · Alcance: este repositorio",
        generated,
        count=1,
        flags=re.MULTILINE,
    )

    # La marca va justo tras el H1, para que sea lo primero que se ve.
    lines = generated.splitlines(keepends=True)
    insert_at = 1 if lines and lines[0].startswith("#") else 0
    lines.insert(insert_at, f"\n{header}\n")

    (target / LAW_FILE).write_text("".join(lines), encoding="utf-8")


def write_provenance(target: Path, name: str, prov: Provenance) -> None:
    """Deja el enlace auditable: de qué versión del harness nació esta instancia."""
    payload = {
        "//": "GENERADO por scripts/instantiate_harness.py — NO EDITAR A MANO.",
        "component": name,
        **prov.as_dict(),
    }
    path = target / PROVENANCE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_readme(target: Path, name: str, prov: Provenance) -> None:
    """README propio: el del harness describía el framework, no este componente."""
    (target / "README.md").write_text(
        f"# {name}\n\n"
        "Componente instanciado del **harness SDD**.\n\n"
        f"- **Harness**: `{prov.harness}` (commit `{prov.commit[:12]}`)\n"
        "- **Método**: SDD — `scope.md` → `design.md` → `tasks/` → `verify.md`\n"
        f"- **Ley**: [`{LAW_FILE}`](./{LAW_FILE}) — generada, no editar a mano\n"
        "- **Gate**: `bash init.sh`\n\n"
        "## Empezar una feature\n\n"
        "```\n"
        "1. Lanza `sdd-init` EN CONVERSACIÓN NUEVA (ADR-016) para escribir .spec/<feature>/scope.md\n"
        "2. Aprueba el alcance (gate G1) escribiendo 'Aprobado por:' TÚ\n"
        "3. Lanza `sdd-tech-lead` en otra conversación nueva\n"
        "```\n\n"
        "Para actualizar la versión del harness, vuelve a instanciar desde el harness de origen.\n",
        encoding="utf-8",
    )


def init_repository(target: Path, name: str) -> None:
    """Historia propia: el componente no comparte la del harness (ADR-012)."""
    run(["git", "init", "-b", "main"], cwd=target)
    run(["git", "add", "-A"], cwd=target)
    run(
        ["git", "commit", "-m", f"chore: initial scaffold for {name} (instanced from harness)"],
        cwd=target,
    )


def check_instance(target: Path) -> int:
    """Verifica que un repositorio instanciado sigue coherente con su procedencia.

    Es la misma forma que `sync-adapters.sh --check`: no regenera, solo comprueba que lo
    escrito corresponde a lo declarado. Sin esto, el AGENTS.md de un componente podría
    divergir del harness y nadie lo sabría (el drift que ADR-006 quiere evitar).
    """
    print(f"== Comprobación de instancia: {target} ==")
    problems: list[str] = []

    provenance_path = target / PROVENANCE_FILE
    if not provenance_path.exists():
        problems.append(f"falta {PROVENANCE_FILE}: no hay procedencia registrada")
        provenance = None
    else:
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{PROVENANCE_FILE} no es JSON válido: {exc}")
            provenance = None

    law_path = target / LAW_FILE
    if not law_path.exists():
        problems.append(f"falta {LAW_FILE}")
    else:
        law = law_path.read_text(encoding="utf-8")
        if GENERATED_MARK not in law:
            problems.append(
                f"{LAW_FILE}: no lleva la marca de generado. Un componente no debe editar su ley "
                "a mano (ADR-006, R4)"
            )
        if IDENTITY_SECTION not in law:
            problems.append(f"{LAW_FILE}: falta la sección §4")

    if provenance:
        declared = str(provenance.get("harness") or "")
        if not declared:
            problems.append(f"{PROVENANCE_FILE}: no declara la versión del harness")
        else:
            available = read_harness_version()
            if available and declared != available:
                print(
                    f"  ! instancia en harness {declared}; este árbol va por {available}. "
                    "¿Toca re-instanciar para recibir cambios del harness?"
                )

    for problem in problems:
        print(f"  ✘ {problem}")

    if problems:
        print(f"\n== INSTANCIA INCOHERENTE: {len(problems)} problema(s) ==")
        return 1

    version = (provenance or {}).get("harness", "?")
    print(f"  ✔ {LAW_FILE} generado, §4 presente y procedencia declarada (harness {version})")
    print("\n== INSTANCIA COHERENTE ==")
    return 0


def read_harness_version() -> str | None:
    """Versión del harness en ESTE árbol, si la declara."""
    path = ROOT / VERSION_FILE
    if not path.exists():
        return None
    match = re.search(r'^harness:\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def instantiate(name: str, target: Path) -> int:
    """Fabrica el componente: extrae, limpia, resuelve identidad y registra procedencia."""
    print(f"== Instanciando '{name}' en {target} ==")

    require_clean_tree()
    prov = read_provenance()
    print(f"  · harness {prov.harness} · commit {prov.commit[:12]}")

    extract(target)
    print("  ✔ extraído de git archive HEAD")

    removed = clean_inheritance(target)
    if removed:
        print(f"  ✔ herencia limpiada: {', '.join(removed)}")

    resolve_identity(target, name, "main")
    print(f"  ✔ identidad resuelta: name={name}, defaultBranch=main")

    generate_law(target, name, prov)
    print(f"  ✔ {LAW_FILE} generado (ley base + §4 del componente)")

    write_provenance(target, name, prov)
    write_readme(target, name, prov)

    init_repository(target, name)
    print("  ✔ repositorio inicializado con su propia historia")

    print(f"\n== INSTANCIA CREADA: {target} ==")
    print("Siguiente paso: abrir VS Code EN EL COMPONENTE y lanzar sdd-init en conversación nueva.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instancia el harness en un repositorio de componente (ADR-006, ADR-012).",
        epilog="Salida: 0 = OK · 1 = fallo · 2 = bloqueo",
    )
    parser.add_argument("--name", help="nombre del componente (identidad del repositorio)")
    parser.add_argument("--target", help="ruta destino del nuevo repositorio")
    parser.add_argument("--check", metavar="RUTA", help="comprueba una instancia existente")
    args = parser.parse_args()

    if args.check:
        return check_instance(Path(args.check).resolve())

    if not args.name or not args.target:
        parser.error("se requieren --name y --target (o --check RUTA)")

    if not re.match(r"^[a-z0-9][a-z0-9-]*$", args.name):
        die(f"el nombre '{args.name}' no es kebab-case (AGENTS.md §3)", 2)

    return instantiate(args.name, Path(args.target).resolve())


if __name__ == "__main__":
    sys.exit(main())
