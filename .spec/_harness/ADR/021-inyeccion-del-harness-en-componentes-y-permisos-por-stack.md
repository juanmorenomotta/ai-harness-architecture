# ADR-021 — Inyección del harness en componentes y permisos especializados por stack

- **Fecha**: 2026-11-14
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE** (plantillas de permisos entregadas en este PR)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Resuelve**: cómo un solo harness gobierna una aplicación **multi-componente** (backend + frontend)
  sin convertirse en el repositorio de sus artefactos, y cómo se especializan los permisos por
  arquitectura de carpetas sin perder la regla deny-first.
- **Tareas afectadas**:
  - `.agents/policies/templates/permissions.laravel.yaml` (nuevo, entregado)
  - `.agents/policies/templates/permissions.vue.yaml` (nuevo, entregado)
  - `.spec/_harness/ADR/README.md` (índice)
  - `scripts/instantiate_harness.py` (pendiente: excluir `harness-maintainer` y tratar
    `permissions.yaml` como plantilla, no como copia sellada)
  - `scripts/validate_harness.py` (pendiente: `EXPECTED_ROLES` por instancia sin maintainer)
  - `init.sh` + `harness.config.json` (pendiente: rama PHP y gate G4, ver ADR-013/ADR-017)

## Contexto

El harness está diseñado como **molde** (framework): los ADR-012 y ADR-020 fijan que el repositorio
es la unidad de mantenimiento y que cada aplicación recibe su propio clon/instancia. El escenario real
de uso es una aplicación con **dos componentes de aplicación** —`backend` (Laravel) y `frontend`
(Vue 3)— más el propio repositorio del harness.

Al aplicar el harness a este caso aparecen cuatro huecos que ningún ADR anterior cubre:

1. **El fan-out de una especificación a varios componentes no existe.** El ciclo SDD está definido
   *dentro* de un solo repositorio: `sdd-init` escribe `.spec/<feature>/` en **su** repo. No hay un
   mecanismo para que una única especificación de negocio (p. ej. «QR público») produzca un `scope.md`
   en el backend y otro en el frontend. El harness no tiene un rol «orquestador» (la skill
   `sdd-orchestrator` describe cómo *coordina el humano*; no es un agente).

2. **Los `writable_paths` del `sdd-developer` son genéricos** (`src/`, `tests/`, `lib/`, `app/`) y no
   cubren el árbol de una app Laravel (`routes/`, `database/`, `config/`, `resources/`, `public/`,
   `bootstrap/`) ni el de una app Vue (`public/`, y su `src/` con estructura propia). Con las rutas
   genéricas, el Developer **no puede** escribir los archivos que la tarea le pide.

3. **El rol `harness-maintainer` viaja al componente.** El instanciador copia `.agents/` completo, lo
   que incluye un rol cuyo `writable_paths` son `scripts/**`, `.harness/**`, `.agents/**`,
   `init.sh` y `harness.config.json`. En un componente, eso daría a un agente permiso para editar su
   **propia** política de permisos — exactamente lo que la regla de juez/parte prohíbe (R6, R7).

4. **El acoplamiento backend↔frontend no tiene contrato.** El frontend «muestra la respuesta del
   backend», pero sin un contrato versionado y un gate de compatibilidad, cada capa programa contra
   una suposición y la integración se rompe en silencio (el «vibe architecting» que se quiere evitar).

## Decisión

**El harness permanece como molde único y se inyecta en cada componente de aplicación. La
especialización por arquitectura de carpetas vive en el componente, no en el molde, y se introduce
exclusivamente por PR aprobado por humano. El rol `harness-maintainer` no se instancia en componentes.
El acoplamiento entre componentes se rige por contrato versionado y el gate G4.**

### 1. Topología: el harness es el molde, no el contenedor de artefactos

```
ai-harness-architecture/   ← molde/control (este repo). NO contiene .spec/ de componentes.
cochera-backend/           ← instancia: AGENTS.md + .agents/ + .harness/ + .spec/ propio
cochera-frontend/          ← instancia: AGENTS.md + .agents/ + .harness/ + .spec/ propio
```

Los artefactos de un componente **nunca** se escriben en el repo del harness (ADR-012). La carpeta
`docs/` del *proyecto* (histórica, SPEC-001..N, planes, informes) se **migra** a `.spec/<feature>/` de
cada componente; la `docs/` **del harness** permanece: documenta el framework, no el componente.

### 2. Fan-out humano de la especificación (sin MCP/Jira como dependencia)

Una única especificación de negocio produce una feature **por componente afectado**, y el reparto lo
hace el **humano**:

```
humano: especificación de negocio
  ├─ sdd-init en cochera-backend   → .spec/<feature>/scope.md  (vista backend)
  └─ sdd-init en cochera-frontend  → .spec/<feature>/scope.md  (vista frontend)
```

- El humano lanza `sdd-init` **una vez por componente**, en **conversación nueva** (ADR-016), pasando
  en el prompt **a qué componente** va y la parte de la especificación que le corresponde.
- Una especificación puede afectar **solo** a un componente: así se declara en el prompt y solo se
  lanza `sdd-init` ahí.
- **No** se introduce un MCP de Jira ni un orquestador agente. La fuente de la spec es el prompt del
  humano, y R10 se cumple porque `sdd-init` escribe el alcance en `scope.md` (el artefacto en disco es
  la fuente de verdad, no el chat).

### 3. `permissions.yaml` se especializa por componente y solo la cambia un humano

La arquitectura de carpetas es **parámetro del componente**, no del método. Por tanto:

| Capa | Ubicación | Contenido | Quién la mantiene |
| :--- | :--- | :--- | :--- |
| **Plantilla del molde** | `.agents/policies/permissions.yaml` | defaults genéricos y seguros | `harness-maintainer` (PR humano) |
| **Plantillas por stack** | `.agents/policies/templates/permissions.{laravel,vue}.yaml` | `writable_paths` del Developer según el stack | `harness-maintainer` (PR humano) |
| **Instancia especializada** | `<componente>/.agents/policies/permissions.yaml` | la política real del componente | **Humano** (tech-lead), vía PR |

Reglas que preservan el principio deny-first:

- `permissions.yaml`, `AGENTS.md` y `.harness/**` son `protected_paths` para **todos** los roles en el
  componente. Ningún agente edita su propia allowlist (R4, R6, R7).
- Añadir o quitar rutas del `writable_paths` del Developer es **PR aprobado por humano**. Los
  manifiestos de dependencias (`composer.json`, `package.json`, `vite.config.js`) quedan **fuera** por
  defecto y se añaden caso a caso por esa misma vía.

### 4. `harness-maintainer` no se instancia en componentes

El instanciador copia los **5 roles SDD** (`sdd-init`, `sdd-tech-lead`, `sdd-developer`,
`sdd-verifier`, `sdd-security-reviewer`) y **excluye** `harness-maintainer`, que es un rol del molde.
Un componente no mantiene su propio harness; lo recibe y lo actualiza re-instanciando.

### 5. Contrato versionado + gate G4 para backend↔frontend

El backend es un componente **`cross`** (ADR-013): expone un contrato versionado
(`api/openapi.yaml`) y es el **dueño** del mismo. El frontend es su **consumidor** y lo referencia con
pin. El **gate G4** verifica compatibilidad de contrato; su implementación (rama PHP + comparador
OpenAPI) queda como trabajo pendiente ya desbloqueado por ADR-013/ADR-017.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Fan-out por un agente orquestador** | El reparto es automático | Requiere un rol nuevo que escribe `.spec/` en repos ajenos, rompiendo ADR-012 (el artefacto es de su repo) y el arranque en frío | El fan-out humano es explícito, auditable y no inventa un orquestador que el harness deliberadamente no tiene |
| **B. MCP de Jira como entrada de `sdd-init`** | Ingreso directo del ticket | Acopla el harness a un proveedor externo y pierde el agnosticismo; añade una dependencia de red | El prompt del humano es suficiente y preserva el principio de fuente en disco |
| **C. Permisos genéricos únicos** | Cero especialización | El Developer no puede escribir las rutas reales de Laravel/Vue; o bien se le abren demasiadas rutas | La especialización por stack es el punto exacto, y la aprueba un humano |
| **D. Inyectar `harness-maintainer` al componente** | El componente se «auto-mantiene» | Un agente podría editar su propia política; viola juez/parte | El molde se mantiene en el molde; el componente solo lo consume |
| **E. Sin contrato entre componentes** | Menos artefactos | La integración backend↔frontend queda sin verificar | ADR-013 ya resuelve la clase `cross`; aquí se aplica al par backend/frontend |

## Consecuencias

**Positivas**
- El harness gobierna una aplicación **multi-componente** sin volverse contenedor de sus artefactos.
- El fan-out es **explícito y humano**: cada `scope.md` declara su componente y su porción del alcance.
- La especialización de permisos es **auditable**: una plantilla por stack + instancia aprobada por humano.
- Se cierra el hueco de juez/parte: `harness-maintainer` no existe en el componente.
- El acoplamiento backend↔frontend queda cubierto por contrato + G4.

**Negativas / deuda asumida**
- **Implementación pendiente** en el instanciador y el validador: hoy las plantillas son manuales y el
  instanciador aún copia `.agents/` completo (incluido `harness-maintainer`). Hasta implementarlo, la
  exclusión del rol y la selección de plantilla por stack son **operación manual** del humano.
- El fan-out humano exige **dos lanzamientos** de `sdd-init` y coherencia de `feature-slug` entre ambos.
- Añadir rutas de escritura es **más lento** (PR humano) a cambio de ser seguro. Es deliberado.
- La migración de la `docs/` histórica del proyecto a `.spec/` es un trabajo **fuera del harness**,
  uno por componente, con su propia trazabilidad.

**Neutrales**
- No cambia la ley base (`AGENTS.md`): el instanciador la lee y la regenera, no la edita.
- El catálogo de modelos y los adaptadores no se tocan.

## Cómo revertir esta decisión

Volver a un solo `permissions.yaml` genérico y permitir que el instanciador copie `.agents/` completo
(incluido `harness-maintainer`). Se pierde la especialización por stack y se reabre el hueco de
juez/parte. Barato de ejecutar; el riesgo asumido es alto.

## Cómo se verificará

1. `scripts/instantiate_harness.py --name cochera-backend --target <ruta>` produce un componente **sin**
   el rol `harness-maintainer` en `.agents/` y **sin** su adaptador en `.github/agents/`.
2. El componente instanciado lleva `.agents/policies/permissions.yaml` con los `writable_paths`
   **Laravel** (desde la plantilla), y `validate_harness.py` del componente da **COHERENTE**.
3. Ídem para `cochera-frontend` con los `writable_paths` **Vue**.
4. **Prueba negativa**: un `sdd-developer` intenta escribir `composer.json` → **bloqueado** (fuera de
   `writable_paths`); intenta escribir `.spec/**/verify.md` → **bloqueado** por `protected_paths`.
5. Un cambio incompatible en el contrato OpenAPI del backend **hace fallar G4** (cuando la rama del
   gate esté implementada, ADR-013/ADR-017).

## Referencias

- ADR-012 (un nivel: el repositorio), ADR-020 (un clon por aplicación)
- ADR-013 (`cross`, contrato versionado, G4), ADR-017 (el maintainer amplía el gate, no lo vacía)
- ADR-006/ADR-019 (el `AGENTS.md` se genera; el instanciador extrae del propio árbol)
- ADR-007 (rol `harness-maintainer`), ADR-016 (arranque en frío por conversación nueva)
- `.agents/policies/permissions.yaml`, `.agents/policies/templates/permissions.{laravel,vue}.yaml`
- `scripts/instantiate_harness.py`, `scripts/validate_harness.py` (`EXPECTED_ROLES`)
