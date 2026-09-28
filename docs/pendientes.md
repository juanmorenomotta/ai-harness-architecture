# Pendientes — Ayuda memoria de traspaso

> **Documento de traspaso.** Escrito al cerrar la sesión del **2026-09-28** para retomar mañana sin
> pérdida de contexto. Complementa a [`inicio-harness-sdd.md`](./inicio-harness-sdd.md), que es el
> documento de arranque general; **este** es la lista concreta de lo que falta por hacer.
>
> **Para retomar**: leer `AGENTS.md` → leer `inicio-harness-sdd.md` → leer este archivo → verificar
> el estado real con los comandos de §1 (no fiarse de este texto: **caduca**).

---

## 1. Estado exacto al cerrar (verificado, no inferido)

| Comprobación | Resultado |
| :--- | :--- |
| Rama | `main` |
| Último commit local | `ba1954f docs: corregir guia (instanciar el componente antes del SDD)` |
| Remoto | `origin` → `github.com/juanmorenomotta/ai-harness-architecture` (privado). **1 commit por subir** |
| `python scripts/validate_harness.py` | **94 comprobaciones, COHERENTE** (exit 0) |
| `bash init.sh` | **PASS** (con `lint`/`format`/`typecheck`/`tests` en **SKIP**) |
| ADRs | **14** (001–014), todos `aceptada`; 004–014 con implementación **pendiente** |
| Sin commitear | `.spec/validator-runner/`, `docs/desacoplamiento-arquitectura-software.md` (previos, fuera a propósito) |
| Aplicaciones / componentes construidos | **NINGUNO** |

### Comandos de verificación obligatorios al retomar

```bash
git log --oneline -6
git status --porcelain
git rev-list --left-right --count HEAD...origin/main
python scripts/validate_harness.py
bash init.sh
```

---

## 2. La cadena de bloqueos (el hallazgo clave de hoy)

**NADA del flujo SDD es ejecutable todavía.** Los bloqueos están encadenados y el orden importa:

```mermaid
flowchart LR
  A["1. Rol harness-maintainer<br/>(ADR-007) NO existe"] --> B
  B["2. Sin rol, nadie implementa<br/>scripts/instanciar-harness.py"] --> C
  C["3. Sin instanciador no existe<br/>el repo del componente"] --> D
  D["4. Sin componente, sdd-init<br/>no tiene dónde escribir"] --> E
  E["5. Rama PHP del gate<br/>(solo para verificación real)"]
```

| # | Bloqueo | Evidencia verificada |
| :--- | :--- | :--- |
| 1 | **`harness-maintainer` no existe** | No hay `.agents/agents/harness-maintainer.md` ni entrada en `permissions.yaml` |
| 2 | **`instanciar-harness` no existe** | `scripts/` tiene solo 4 archivos: `diagnose_harness.py`, `harness_yaml.py`, `sync-adapters.sh`, `validate_harness.py` |
| 3 | **Sin instanciador no hay componente** | Y sin componente, `.spec/` no tiene dueño |
| 4 | **La rama PHP del gate** | `init.sh` detecta `composer.json` pero **no tiene rama PHP** en lint/format/typecheck/tests |

### El error que se corrigió hoy (no repetirlo)

La guía escribía `.spec/auth-service/` **dentro del repositorio del harness**, con
`git checkout -b spec/auth-service` en el harness. **Contradecía ADR-012** (el `.spec/` pertenece al
repositorio que lo contiene). Los artefactos habrían quedado en el repo del framework.

**Regla**: un artefacto de un componente **nunca** se escribe dentro de `ai-harness-architecture`.

```
a:\jmm\libros\AI-First\ai-harness-architecture\   ← EL HARNESS (el framework, el molde)
a:\proyectos\auth-service\                         ← EL COMPONENTE (repo nuevo a instanciar)
```

---

## 3. Los 4 pendientes, en orden de dependencia

### PENDIENTE 1 — Rol `harness-maintainer` (ADR-007)

**Para qué**: hoy **ningún rol puede escribir en `scripts/`**. `sdd-developer` solo tiene
`src/`, `tests/`, `lib/`, `app/`. Sin este rol, el PENDIENTE 3 es imposible.

**Por qué no basta con abrir `scripts/` al Developer**: `scripts/` contiene `validate_harness.py` e
`init.sh`, las herramientas con las que el **Verifier** juzga. El Developer podría hacer que su propio
juez lo declare inocente. Misma lógica que R7 (no debilitar tests).

**Qué crear**:

| Archivo | Cambio |
| :--- | :--- |
| `.agents/agents/harness-maintainer.md` | **Nuevo.** Prompt del rol, agnóstico de modelo |
| `.agents/policies/permissions.yaml` | `writable_paths: ["scripts/**", ".harness/**", ".agents/**"]`, con `edit` en `allow` |
| `.harness/models.yaml` | Entrada del rol con modelo asignado |
| `scripts/validate_harness.py` | La constante `EXPECTED_ROLES` **fija los 5 roles**: hay que añadirlo |
| `.github/agents/`, `.claude/`, `.gemini/` | Regenerar con `sync-adapters.sh` |

**Límites duros del rol** (registrados en ADR-007):
1. **No** puede editar `AGENTS.md` (la ley es solo humana, §9)
2. **No** puede editar `.github/workflows/**`
3. Toda su salida va por PR con revisión humana
4. **Nunca se invoca en el contexto de una tarea de feature fallida** (esto preserva R4)

**Verificación**: `sync-adapters.sh` genera su adaptador; `validate_harness.py` lo reconoce.

---

### PENDIENTE 2 — Versión única del harness (ADR-004)

**Para qué**: el harness tiene **cinco versiones repartidas** y ninguna lo representa:

| Archivo | Versión |
| :--- | :--- |
| `AGENTS.md` → «Versión del contrato» | 1.0.0 |
| `harness.config.json` → `version` | 1.0.0 |
| `.harness/models.yaml` → `version` | 1.2.0 |
| `.harness/providers.yaml` → `version` | 1.1.0 |
| `.harness/routing.yaml` → `version` | 1.0.0 |

Sin versión única **no hay nada que fijar** al instanciar, así que el PENDIENTE 3 no puede saber qué
copiar.

**Qué crear**: `.harness/harness.version` agregando las cinco, **más un check que falle si divergen**:

```yaml
harness: "1.0.0"           # versión del conjunto (semver)
declared:
  agents_contract: "1.0.0"  # AGENTS.md
  config: "1.0.0"           # harness.config.json
  models: "1.2.0"
  providers: "1.1.0"
  routing: "1.0.0"
```

**Tres invariantes del check** (el tercero es el que aporta valor):
1. El archivo existe y `harness` es semver válido
2. Cada artefacto declara una versión presente en `declared`
3. **La versión REAL de cada artefacto coincide con la declarada** ← detecta cambiar un archivo sin registrarlo

**Política semver**: cambio en R1–R10 o en un gate → **major**; rol/skill/política nueva → **minor**;
ajuste de configuración → **patch**.

**Verificación obligatoria**: prueba negativa (modificar un artefacto sin actualizar el manifiesto y
confirmar que el validador falla con código 1). Lección de ADR-001: *un validador que nunca ha fallado
no ha demostrado nada.*

---

### PENDIENTE 3 — `scripts/instanciar-harness.py` (ADR-006)

**Para qué**: crear un repositorio de componente **autosuficiente** (ADR-012). Hacerlo a mano es error
garantizado: hay ~10 artefactos que copiar, **identidad que cambiar** (`harness.config.json` hoy dice
`"name": "deepseek-harness"`, el nombre de otro repo) y **herencia que limpiar**.

**Las cuatro operaciones** (ADR-006):
1. **Fijar la versión** del harness (semver o SHA), nunca «lo último»
2. **Resolver identidad**: nombre, remoto, ramas protegidas, idioma
3. **Limpiar herencia**: `.spec/` vacío, **sin** los ADR del framework, `README.md` propio, `name` correcto
4. **Dejar el enlace auditable**: registrar con qué versión del harness se construyó

**Salida esperada**:
```
a:\proyectos\auth-service\
  AGENTS.md              ← GENERADO: ley base + parámetros. "NO EDITAR A MANO"
  harness.config.json    ← con name: auth-service
  init.sh                ← su gate
  .harness/  .agents/  .github/agents/
  .gitignore
  .spec/                 ← VACÍO: aquí van SUS artefactos
  .git/                  ← SU propia historia
  ✗ sin .spec/_harness/  ← no arrastra los ADR del framework
```

**Interfaz propuesta**:
```bash
python scripts/instanciar-harness.py \
    --name auth-service \
    --target a:\proyectos\auth-service \
    --harness-version 1.0.0
```

**Modo `--check`** (ADR-006): falla si el `AGENTS.md` de un componente instanciado diverge de su
versión declarada. Misma forma que `sync-adapters.sh --check`.

### ⚠️ DECISIÓN ABIERTA que bloquea este pendiente

**¿De dónde toma el harness base?**

| Opción | Cómo | Problema |
| :--- | :--- | :--- |
| **A. Copia local** | Del harness clonado al lado | Arrastra cambios locales sin commitear |
| **B. Clonar del remoto** | `git clone --branch <tag> --depth 1` | Requiere que **existan tags** |
| **C. `git archive` de una ref** | De una versión concreta | Igual que B |

**B y C son las correctas** (fijar versión era la decisión D1 del responsable), pero **dependen del
PENDIENTE 2**: sin versión no hay tag que clonar. **Decidir A, B o C antes de implementar.**

---

### PENDIENTE 4 — Instanciar `auth-service`

**Para qué**: crear el repositorio del primer componente. **No es desarrollo**: es ejecutar un comando
del PENDIENTE 3.

**Y aquí —solo aquí— se puede lanzar `sdd-init`.** Porque entonces existe un repo con su `AGENTS.md`
donde escribir `.spec/auth-core/scope.md`.

**Alcance ya decidido del componente** (A6, ADR-009 revisado):

| Parámetro | Valor |
| :--- | :--- |
| Repos | **2**: `auth-service` (clase **`cross`**, Laravel 12 · PHP 8.2) y un **consumidor** frontend (Vue 3 · Vite) |
| Feature del primer corte | **`auth-core`** (nombre distinto del repo para evitar ruta redundante) |
| Base de datos | SQLite local (no hay Docker) o MySQL de XAMPP |
| Modo | Ciclo SDD **completo** (ADR-008) |
| Funcionalidad | Registro con correo + contraseña + **validación**, **activación por enlace enviado por correo**, reenvío, login, logout, recuperación |
| Contrato | **Propiedad de `auth-service`** (`api/openapi.yaml`), versionado. El consumidor lo referencia **con pin** |
| Implementación | **Desde cero** — sin Breeze ni Jetstream |
| Objetivo | Ejercitar las **4 fases y los 4 gates (G1–G4)**, no cubrir requisitos de producción |

**Por qué auth es buen primer caso**: ejercita entrada de usuario, autorización/sesiones, migraciones
de esquema, contraseñas y hashing, dependencias nuevas de Composer **y npm**, **el contrato entre dos
repos** y el gate **G4** de compatibilidad. Activa `sdd-security-reviewer`, **que nunca se ha usado**.

---

## 4. Lo demás que queda pendiente (no bloquea el arranque)

| # | Pendiente | ADR | Por qué |
| :--- | :--- | :--- | :--- |
| 5 | **Rama PHP en `init.sh`** (Pint, PHPStan/Larastan, `vendor/bin/phpunit`) | 009 | Sin ella el gate dice **PASS sin comprobar PHP**. Hacerlo **cuando exista** el proyecto Laravel real (no especular) |
| 6 | **`validator-runner`**: reclasificar como **chore**, no feature | — | Es una automatización de `scripts/`, no una feature de dominio. Su `scope.md` tiene **5 supuestos ABIERTOS** que bloquean su G1 |
| 7 | **Separar identidades** agente/humano (PAT o GitHub App de menor privilegio) | 011 | Hoy **R3 no es control técnico**: GitHub ve una sola identidad. No se arregla pagando |
| 8 | **`CODEOWNERS` + campo `ownership`** en el `template.yaml` | 013 | Sin esto, «PR aprobada por el owner» es una regla **sin artefacto** |
| 9 | **Gate G4** en `harness.config.json` | 013 | Añadir a `requireHumanApprovalGates` |
| 10 | **Extender `validate_harness.py`** con: coherencia de versiones (ADR-004), sincronización del `AGENTS.md` generado (ADR-006) | 004, 006 | Los checks que hacen reales esas decisiones |
| 11 | **`harness.config.json`: `"name": "deepseek-harness"`** → identidad real | 006 | En un componente instanciado genera el `AGENTS.md` con **nombre equivocado** |
| 12 | **Suite de conformidad de templates** | 013 | Antes de admitir un template: gate verde, licencia, sin CVEs, runtime no EOL |
| 13 | **Limpiar `.spec/_harness/diagnostic.md:94`** | 010 | Contiene una ruta absoluta de máquina. Irrelevante en repo privado; limpiar si se publica |

---

## 5. Decisiones que esperan al responsable

| # | Decisión | Bloquea | Opciones |
| :--- | :--- | :--- | :--- |
| **D-1** | **Origen del harness base** para el instanciador | PENDIENTE 3 | A (copia local) · **B (clonar del remoto)** · C (`git archive`) |
| **D-2** | ¿`auth-service` se especifica como **`cross` completo** o con alcance reducido? | PENDIENTE 4 | Recomendado: **`cross`**, porque ejercita contrato + G4 |
| **D-3** | ¿Se **reclasifica `validator-runner`** como chore y se archiva su `scope.md`? | PENDIENTE 6 | — |

---

## 6. Qué hacer mañana, paso a paso

```
1. git push origin main                       ← subir ba1954f (1 commit pendiente)
2. Verificar: python scripts/validate_harness.py  → COHERENTE (94)
3. Decidir D-1 (origen del harness base)
4. Implementar PENDIENTE 1 (harness-maintainer)  ← el más pequeño y autónomo
5. Implementar PENDIENTE 2 (versión única)        ← independiente del 1, se puede en paralelo
6. Implementar PENDIENTE 3 (instanciar-harness)   ← necesita 1 y 2
7. PENDIENTE 4: instanciar auth-service
8. Ahora sí: lanzar `sdd-init` (guía completa en inicio-harness-sdd.md §7)
```

**Los pendientes 1, 2 y 3 son PRs de harness (R4) y los aprueba el humano. Ningún agente los hace solo.**

---

## 7. Trampas conocidas (no repetirlas)

### Del entorno (verificado)

- **`phpunit` global de XAMPP está ROTO** (warning PEAR) → usar siempre `vendor/bin/phpunit`
- **Laravel Installer global es 3.0.1** (antiguo) → usar `composer create-project laravel/laravel:^12.0`
- **Faltan `ruff`, `mypy`, `pytest`** → el gate reporta SKIP en esos checks
- **No hay `docker`, `gh`, `java`** → sin contenedor para la BD; PR por la web
- **Comandos multilínea en PowerShell pierden salida** → encadenar con `;` en una sola línea

### Del harness (verificado)

- **Añadir campos al frontmatter de `SKILL.md` es peligroso**: VS Code solo admite cinco (`name`,
  `description`, `argument-hint`, `user-invocable`, `disable-model-invocation`) y un campo desconocido
  produce **fallo silencioso de descubrimiento**
- **`edit` es la tool de escritura, no «editar código»**. Acotar con `writable_paths`, nunca con
  `deny: edit`. Este error dejó **3 roles incapaces de escribir su artefacto** (fases init, design y
  verify inejecutables). Corregido y con check (`check_role_tools_consistency`)
- **Un check en `SKIP` no es un `PASS`.** No contarlo como cumplimiento en `verify.md`
- **La protección de rama está INERTE** (repo privado + plan Free). No contarla como R3 cumplida
- **`.agents/policies/permissions.yaml` cambió fuera de mis ediciones** en una ocasión: **leer siempre
  el archivo antes de editarlo**, no asumir su contenido

### De método (aprendido en esta sesión)

- **Dos reemplazos de archivo fallaron silenciosamente** y se detectaron **verificando el archivo**, no
  confiando en que se habían aplicado. **Verificar tras editar.**
- **Un documento de estado caduca.** El documento daba el remoto por pendiente cuando ya existía.
  **Comprobar la realidad con comandos antes de actuar sobre lo que dice un documento.**

---

## 8. Patrón transversal del repositorio (5 ocurrencias)

**Un dato crítico en copias que pueden divergir en silencio.** Es el hilo conductor de casi todos los ADR:

| # | Caso | ADR |
| :--- | :--- | :--- |
| 1 | Validar nombres de modelo contra la **fuente equivocada** (docs de API vs catálogo del runtime) | 001 |
| 2 | Confundir **catálogo nativo** con el aportado por una **extensión** | 002 |
| 3 | Vínculos **agente ↔ skill** en prosa, sin check (3 de 8 incompletos) | 003 |
| 4 | **Cinco versiones** del harness sin coordinación | 004 |
| 5 | **Garantía aparente**: protección de rama inerte; un `SKIP` contado como `PASS` | 011 |

**Dos lecciones transversales**:
- *Un validador que nunca ha fallado no ha demostrado nada.* → probar todo check con un fixture que
  deba fallar, y confirmar el código 1.
- *Un límite es real cuando es **capacidad ausente**, no cuando es una instrucción.* → es lo que
  justifica `harness-maintainer` (ADR-007) y la separación de identidades (ADR-011).

---

## 9. Documentos de referencia

| Documento | Contenido |
| :--- | :--- |
| [`AGENTS.md`](../AGENTS.md) | **La ley.** R1–R10, gates G1–G3, estándares, Definition of Done |
| [`docs/inicio-harness-sdd.md`](./inicio-harness-sdd.md) | Arranque general + **guía paso a paso** de las fases 0–7 |
| [`docs/propuesta-harness-instanciable.md`](./propuesta-harness-instanciable.md) | Modelo de instanciación, decisiones D1–D3, abiertas A1–A7, anexos A3/A4 |
| [`docs/desacoplamiento-arquitectura-software.md`](./desacoplamiento-arquitectura-software.md) | Diseño del eje de stack: `stack.md`, `template.yaml`, `agent_profile.md` |
| [`.spec/_harness/ADR/README.md`](../.spec/_harness/ADR/README.md) | **Índice de los 14 ADR** |
| `.spec/validator-runner/scope.md` | Feature **varada** con 5 supuestos abiertos (ver PENDIENTE 6) |

---

## 10. Glosario mínimo (para retomar en frío)

| Término | Significado |
| :--- | :--- |
| **Harness** | El framework: roles, skills, políticas, ley, gates. **Es el molde** |
| **Componente** | Un repositorio autosuficiente creado **instanciando** el harness |
| **Instanciar** | Fabricar un repo de componente desde el harness, con identidad y versión propias |
| **`cross`** | Clase de componente consumido por terceros: owner + contrato versionado + **G4** |
| **G1/G2/G3/G4** | Gates humanos: alcance · plan · verificación · aprobación del owner (solo `cross`) |
| **R1–R10** | Las reglas de oro de `AGENTS.md` §1 |
| **`.spec/`** | Artefactos SDD. **Pertenece al repositorio que lo contiene** (ADR-012) |
| **Contrato** | La API del componente **proveedor**. El consumidor la usa **con pin**, nunca copiada |
| **Arranque en frío** | Cada fase lee artefactos en disco; no hereda contexto de la conversación |
