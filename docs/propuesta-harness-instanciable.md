# Propuesta — Harness instanciable

> **Estado**: propuesta en curso · **Fecha**: 2026-09-25 · **Decisor**: humano responsable del harness
> **Naturaleza**: documento de referencia. Registra las decisiones tomadas y las abiertas sobre cómo
> convertir este repositorio en un **framework de desarrollo reutilizable**. Forma parte de la
> historia de construcción del harness.

---

## 1. Objetivo

Convertir este repositorio en un **framework de SDLC agéntico** reutilizable en cualquier
desarrollo (backend, frontend, full stack, móvil) **sin depender de la tecnología** ni del modelo
de lenguaje.

El objetivo declarado por el humano responsable:

> Guardar la arquitectura del harness en un repositorio versionado; al iniciar un proyecto,
> instanciarla y crear los repositorios de cada componente a partir de **templates maduros**,
> y desarrollar con el ciclo SDD.

---

## 2. El problema del modelo inicial

El modelo mental original tenía **dos niveles**: el harness y el proyecto. Con esa topología, el
harness y el proyecto compiten por el mismo árbol de directorios, y aparecen tres conflictos:

| Conflicto | Evidencia |
| :--- | :--- |
| **Identidad heredada** | `harness.config.json` declara `"name": "deepseek-harness"`, que no es el nombre de este repositorio (`AI-Harness-Architecture`). Un proyecto instanciado hereda el nombre de otro |
| **Historia ajena** | `.spec/_harness/ADR/001..003` son decisiones de *este* harness. Un proyecto nuevo arrancaría con deuda y decisiones que no le pertenecen |
| **Colisión normativa** | R4 protege `AGENTS.md`, `.harness/**` y `.agents/**` contra escritura, pero un harness *debe* adaptarse al proyecto. Dos leyes compitiendo en el mismo árbol |

A esto se suma un cuarto problema, medido, no teórico:

| Artefacto con versión | Valor actual |
| :--- | :--- |
| `AGENTS.md` → "Versión del contrato" | `1.0.0` |
| `harness.config.json` → `version` | `1.0.0` |
| `.harness/models.yaml` → `version` | `1.2.0` |
| `.harness/providers.yaml` → `version` | `1.1.0` |
| `.harness/routing.yaml` → `version` | `1.0.0` |

**Cinco versiones independientes, sin coordinación y sin ninguna que represente al harness.** No
existe un identificador único que un proyecto pueda fijar. `scripts/validate_harness.py` **no
comprueba** la coherencia entre ellas.

> Consecuencia: hoy **no se puede fijar la versión del harness**. La primera decisión del humano
> —"debe mantenerse versionado para no perder enlace con los proyectos"— es, en el estado actual,
> **inejecutable**.

---

## 3. Modelo propuesto: tres niveles

| Nivel | Qué es | Responsable de | Cambia |
| :--- | :--- | :--- | :--- |
| **1. Harness** | **Cómo** se trabaja: roles, skills, políticas, ley, gates | Definición agnóstica de proyecto y de tecnología | Rara vez, con semver |
| **2. Proyecto** | **Qué** se construye: alcance, stack, contratos | El repo del proyecto | Por aplicación |
| **3. Componente** | **Con qué**: backend, frontend, móvil, datos | Templates maduros (**uno por componente**) | Por tecnología |

El nivel 1 se **instancia** en el nivel 2; el nivel 2 **materializa** el nivel 3.

### El patrón se aplica por tercera vez

Este modelo no es nuevo en el repositorio: es el **mismo patrón** que ya se aplicó dos veces, y
ambas están verificadas por comando (85 comprobaciones).

| Capa | Modelos (hecho) | Skills (hecho) | Harness (propuesto) |
| :--- | :--- | :--- | :--- |
| **Definición agnóstica** | Rol `.md` (sin modelo) | `SKILL.md` (sin modelo) | Harness base (sin proyecto) |
| **Selección por instancia** | `.harness/models.yaml` | `skills:` del rol | Instancia de proyecto |
| **Adaptador / artefacto** | `.github/agents/` | — | `apps/*/` clonados |

Si el patrón funcionó dos veces, es el patrón correcto para la tercera.

---

## 4. Diagrama del flujo propuesto

```mermaid
flowchart TD
  subgraph N1["NIVEL 1 — Harness (versionado)"]
    HB["harness-base<br/>roles · skills · políticas · ley<br/>SIN identidad de proyecto"]
    HP["perfiles de dominio<br/>(especialización)"]
    HB --> HP
  end

  P["Humano: prompt de proyecto"] --> INST
  HP --> INST["instanciar-harness<br/>fija versión · resuelve identidad<br/>limpia herencia"]

  INST --> N2

  subgraph N2["NIVEL 2 — Proyecto"]
    LAW["AGENTS.md del proyecto"]
    CFG["harness.config.json<br/>+ harness.version"]
    SPEC[".spec/&lt;feature&gt;/"]
    STACK["stack.md<br/>(selección de componentes)"]
    CTR["contracts/<br/>(OpenAPI · AsyncAPI · protobuf)"]
  end

  N2 --> MAT

  MAT["materializar-stack<br/>git clone --branch REF<br/>(refs inmutables)"] --> N3

  subgraph N3["NIVEL 3 — Componentes (repos independientes)"]
    BE["apps/backend<br/>template.yaml"]
    FE["apps/frontend<br/>template.yaml"]
    MO["apps/mobile<br/>template.yaml"]
    DB["apps/data<br/>template.yaml"]
  end

  N3 --> GATE

  GATE["init.sh raíz<br/>agrega el gate de cada componente<br/>lee template.yaml de cada uno"] --> SDD

  SDD["Ciclo SDD por componente<br/>init → design → tasks → implement → verify"]
  SDD --> G{"Gates humanos<br/>G1 · G2 · G3"}
  G -->|aprobado| DONE["Componente verificado"]
  G -->|rechazado| SDD
```

---

## 5. Decisiones tomadas

### D1 — El harness se **instancia** para iniciar un proyecto, y se mantiene versionado

**Decisión**: el harness se instancia (no se copia sin control) y conserva un enlace de versión con
los proyectos y componentes que origina, para poder actualizarlos a lo largo del tiempo.

**Consecuencia inmediata**: hace falta un **identificador único de versión del harness**. Las cinco
versiones actuales (§2) no sirven porque ninguna representa al conjunto, y pueden divergir sin que
nada lo detecte.

**Pendiente de decidir**: la forma del identificador. Opciones:

| Opción | Ventaja | Problema |
| :--- | :--- | :--- |
| Campo nuevo en `harness.config.json` (`harnessVersion`) | Un solo sitio, ya versionado | No agrega las 5 versiones existentes |
| `.harness/harness.version` + check de coherencia en el validador | Agrega las 5 y **falla si divergen** | Un archivo más |
| Tag semver del repositorio del harness | Es el mecanismo estándar de git | No captura cambios de configuración sin tag |

> Toca `.harness/**` y `harness.config.json` → **R4: PR separada con aprobación humana**.

### D2 — Un harness **por tipo de componente**, que madura con el tiempo

**Decisión**: existirán varios harness, especializados por tipo de componente/aplicación, para que
cada uno madure con la experiencia acumulada.

**Riesgo que introduce, y su mitigación.**

Multiplicar harness por dominio reproduce **exactamente el mismo riesgo de divergencia** que
"copiar el harness por proyecto" (§2). Si cada dominio es un repositorio independiente, en seis
meses hay cinco harness incompatibles y ninguna lección compartida.

Mitigación propuesta — **herencia explícita, no forks independientes**:

```
harness-base                    ← el núcleo: roles, skills, políticas, gates
├── dominio/backend-service     ← especializa: stack por defecto, skills extra, gate
├── dominio/web-frontend
└── dominio/mobile
```

Los perfiles de dominio **heredan** del base y solo declaran su **delta**. Un cambio en el base se
propaga; un cambio en un perfil es visible y acotado. Regla propuesta: *un perfil de dominio no
puede contradecir al base, solo añadir o restringir*.

**Pendiente de decidir**: el mecanismo de herencia (referencia a versión del base + parche de
delta, o copia generada con sello de versión).

### D3 — Ciclo completo para aplicaciones, modo ligero para infraestructura

**Decisión**: los componentes de **infraestructura** usan un modo ligero; los componentes de
**aplicación** pasan por el ciclo SDD completo.

| Aspecto | Aplicación | Infraestructura (ligero) |
| :--- | :--- | :--- |
| Fases SDD | `init → design → tasks → implement → verify` | `init → design → implement` |
| `design.md` | Completo (interfaces, alternativas, riesgos) | Mínimo (qué, por qué, cómo se verifica) |
| `tasks/` | Una tarea por archivo, 1 commit cada una | Sin descomposición formal |
| Gates humanos | G1 + G2 + G3 | G1 (alcance) + revisión del diff |
| Verificación | `verify.md` con trazabilidad AC↔código | Gate del componente + revisión |
| Adaptadores de agente | Todos | Subconjunto |

> El modo ligero **no** relaja la ley: aplican R1 (nada de código sin spec), R6 (`init.sh` como
> único gate), R7 (no se debilitan tests) y R9 (sin secretos). Lo que se ajusta es la **ceremonia**,
> no las garantías.

---

## 6. Topologías de consumo del harness

| Opción | Ventaja | Problema | Veredicto |
| :--- | :--- | :--- | :--- |
| **A. Clonar y commitear dentro del proyecto** | Un solo repo, simple | Divergencia garantizada: cada proyecto forkea y el upgrade se vuelve merge manual que nadie hace | Aceptable solo para una prueba única |
| **B. Submódulo git** | Referencia por versión explícita | Submódulos frágiles; herramientas y CLIs no leen bien `.agents/` y `AGENTS.md` en submódulo | Descartado |
| **C. Instanciar una versión fijada** | Proyecto autónomo; **sabes de qué versión viene**; upgrade como comando explícito | Requiere mantener el script de instanciación y la noción plantilla/instancia | **Recomendado** |

**Nota sobre GitHub**: el mecanismo correcto es **template repository**, no *fork*. Un template
genera un repositorio **sin historia compartida**; un fork la comparte, y lo que se busca es
independencia.

### Qué debe hacer `instanciar-harness`

1. **Fijar la versión** del harness (semver o SHA), nunca "lo último".
2. **Resolver identidad**: nombre del proyecto, remoto, ramas protegidas, idioma de la ley.
3. **Limpiar herencia**: `.spec/` vacío, sin ADRs del harness, `README.md` propio, `name` correcto.
4. **Dejar el enlace auditable**: registrar la versión del harness en el proyecto.

---

## 7. El eje de stack encaja como nivel 3

Lo diseñado en `docs/desacoplamiento-arquitectura-software.md` **es el mecanismo del nivel 3**:

```
.spec/<feature>/stack.md    →  declara: backend en Go, web en React, datos en Postgres,
                               con repository + ref inmutable por componente
apps/                       →  materializado por git clone
apps/*/template.yaml        →  cada componente se describe a sí mismo:
                               comandos del gate, rutas escribibles, perfil del agente
```

Con esto, `init.sh` deja de **adivinar** el stack (`if [ -f package.json ] … elif [ -f go.mod ]`)
y pasa a **leer** lo que cada componente declara. Es la diferencia entre inferir y verificar.

---

## 8. Riesgos del nuevo flujo

| Riesgo | Por qué duele | Mitigación |
| :--- | :--- | :--- |
| **Deriva de versión del harness** | 5 proyectos con 5 versiones divergentes | D1: versión única + check; D2: herencia en vez de fork |
| **Templates que se pudren** | Runtimes EOL, CVEs acumuladas | Suite de conformidad antes de admitir un template |
| **Clonar código de terceros ejecuta código** | `postinstall`, hooks de git = ejecución remota | Allowlist de hosts + prohibición de scripts de instalación (coherente con la prohibición de `curl \| sh` ya vigente) |
| **N identidades de gate** | Cada componente con su `init.sh` | Agregación jerárquica; el gate raíz es el **único** veredicto |
| **Coste multi-repo** | 4 componentes × 5 fases = 20 ciclos | D3: modo ligero para infraestructura |
| **Ambigüedad de "harness por dominio"** | Puede derivar en N harness incompatibles | D2: perfiles que heredan del base |

---

## 9. Estado actual medido

Verificado el 2026-09-25, no inferido:

| Comprobación | Resultado |
| :--- | :--- |
| `design.md`, `tasks/`, `verify.md` en cualquier feature | **Ninguno** |
| Directorios `src/`, `lib/`, `app/`, `tests/` | **Ninguno existe** |
| `.venv`, `pyproject.toml` | **No existen** |
| `ruff`, `mypy`, `pytest` | **Ausentes** |
| Remoto git | **Vacío** (R3 no es ejecutable) |
| `scripts/**` en `writable_paths` de algún rol | **No** (bloquea `validator-runner` y el materializador) |
| Checks de `init.sh` (`lint`, `format`, `typecheck`, `tests`) | **`SKIP`** → el gate dice PASS sin comprobar nada |

**El flujo SDD nunca ha pasado de la fase init.** La arquitectura está definida y verificada en su
capa de definición, pero **nunca se ha ejercitado** con código real.

---

## 10. Orden de implementación propuesto

| Paso | Qué | Por qué aquí |
| :--- | :--- | :--- |
| **0** | Reclasificar `validator-runner` como chore del harness | Es una automatización de `scripts/`, no una feature de dominio. Su ceremonia de 5 supuestos abiertos no le corresponde |
| **1** | **Activar el gate**: `.venv`, manifiesto, herramientas, remoto | Sin esto, nada de lo demás es verificable: el gate daría PASS sin comprobar |
| **2** | **Versión única del harness** (D1) | Hace el harness instanciable de verdad |
| **3** | **`instanciar-harness`** | Convierte el harness en reutilizable |
| **4** | **Primera aplicación real**, un solo componente, ciclo completo | Prueba las 4 fases end-to-end |
| **5** | **Perfiles de dominio** (D2) + **modo ligero** (D3) | Especialización, ya sobre un flujo ejercitado |
| **6** | **Materializador de stack** (nivel 3) + templates | Multi-componente |

> El paso 4 es el que aporta la información que **no se puede obtener leyendo**: los huecos que solo
> aparecen cuando el flujo se ejecuta. Los pasos 5 y 6 deberían llegar **después**, para no
> hornear supuestos en `AGENTS.md`, que es el sitio más caro de cambiar.

---

## 11. Decisiones abiertas

| # | Decisión | Responsable |
| :--- | :--- | :--- |
| A1 | Forma del identificador único de versión del harness (§5, D1) | Humano responsable |
| A2 | Mecanismo de herencia base → perfil de dominio (§5, D2) | Humano responsable |
| A3 | ¿`AGENTS.md` del proyecto es específico (con drift) o referencia al harness base? | Humano responsable |
| A4 | ¿`scripts/**` es superficie escribible por el Developer, y con qué límites? | Humano responsable + Tech Lead |
| A5 | ¿Todo componente de aplicación merece ciclo completo, o hay umbral por tamaño? | Product Owner humano |
| A6 | Primera aplicación de prueba y su stack | Humano responsable |
| A7 | ¿Se crea remoto git para que R3 (PR) sea ejecutable? | Humano responsable |

---

## 12. Documentos relacionados

- [`docs/desacoplamiento-arquitectura-software.md`](./desacoplamiento-arquitectura-software.md) — diseño del eje declarativo de stack (nivel 3)
- [`AGENTS.md`](../AGENTS.md) — ley del repositorio (R1–R10, gates G1–G3)
- [`.spec/_harness/ADR/`](../.spec/_harness/ADR/README.md) — decisiones ya registradas (ADR-001 a 003)
- [`README.md`](../README.md) — estado del harness y diagnóstico
