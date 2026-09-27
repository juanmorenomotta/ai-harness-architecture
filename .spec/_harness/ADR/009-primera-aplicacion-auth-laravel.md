# ADR-009 — Módulo de autenticación (Laravel 12 + Vue) como primera aplicación y template de referencia

- **Fecha**: 2026-09-27 · **Revisión**: 2026-09-27 (de 1 a **2 componentes**)
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE — requiere resolver un bloqueo previo**
- **Decisor**: Juan Moreno (Product Owner)
- **Feature**: `_harness` (decisión de alcance de la prueba del framework)
- **Cierra**: decisión abierta **A6** de `docs/propuesta-harness-instanciable.md`
- **Tareas afectadas**: `.spec/auth/` (nuevo), `scripts/` (soporte de PHP en el gate), `docs/`

> **Nota de revisión (2026-09-27)**: la decisión original de este ADR definía **un solo componente**
> (backend Laravel). El Product Owner precisó el alcance a **dos componentes**: backend Laravel 12 y
> frontend Vue. La decisión de fondo —auth como primera aplicación y template de referencia— no
> cambia; se amplía el alcance y aparecen dos consecuencias nuevas (el **contrato** y la **duplicación
> del ciclo SDD**).

## Contexto

El harness tiene **cero aplicaciones**. El flujo SDD nunca ha pasado de la fase init, el gate está
inerte y ninguna de las cuatro fases se ha ejercitado con código real.

La primera aplicación **no busca valor de negocio**: busca **estresar el flujo** y descubrir los huecos
que solo aparecen al ejecutarlo. Pero además se quiere que sirva de **template estándar** para iniciar
proyectos nuevos sobre el harness instanciable (nivel 3).

Se elige un **módulo de autenticación con correo y contraseña**, con **dos componentes** (backend
Laravel 12 / PHP 8.2 y frontend Vue), porque cubre las superficies que más estresan el harness:

| Superficie que ejercita | Por qué importa |
| :--- | :--- |
| Entrada de usuario (formularios, validación) | Activa el rol `sdd-security-reviewer` |
| Autorización, sesiones, tokens | Superficie de seguridad real |
| Migraciones de esquema (tabla de usuarios, tokens de activación) | Ejercita el componente **datos** |
| Contraseñas y hashing | Criptografía: punto de la checklist de seguridad |
| **Contrato entre dos componentes** | Ejercita el nivel 3 completo: dos repos que solo hablan por contrato |
| Dependencias nuevas (Composer y npm) | Ejercita §2.6 (dependencia justificada en `design.md`) |

## Decisión

**La primera aplicación de prueba es un módulo de autenticación (correo + contraseña) con DOS
componentes —backend Laravel 12 / PHP 8.2 y frontend Vue— y ambos pasan por el ciclo SDD completo**
(ADR-008).

Además, se adopta como **template de referencia**: tras pasar el ciclo completo y verificarse, se
publican como repositorios de template del nivel 3, con su `template.yaml` y su `agent_profile.md`.

Forma del primer corte:

| Parámetro | Valor |
| :--- | :--- |
| Componentes | **2**: `backend` (Laravel 12 · PHP 8.2 · Composer) y `frontend` (Vue 3 · Vite · npm) |
| Base de datos | SQLite (local, sin Docker) o MySQL de XAMPP |
| Modo | **Ciclo SDD completo**, por componente (ADR-008) |
| Funcionalidad | Registro con correo + contraseña + validación, **activación por enlace enviado por correo**, login, logout, recuperación de contraseña |
| Contrato | `.spec/auth/contracts/api.openapi.yaml` — **única costura** entre los dos componentes |
| Objetivo | Ejercitar las 4 fases y los 3 gates, no cubrir requisitos de producción |

### Qué cambia al tener dos componentes

1. **El ciclo SDD se duplica**: 2 componentes × (init → design → tasks → implement → verify) con sus
gates. Es el coste correcto según ADR-008 (sin umbral de tamaño).
2. **Aparece el contrato**, y es crítico: backend y frontend son **repos independientes**; ninguno
   importa código del otro. El contrato debe definirse en `design.md` **antes de materializar los
   componentes**, porque ambos dependen de él. Si se materializa el backend primero, el contrato se
   descubre tarde y el frontend queda desalineado.
3. **Se activa una decisión de seguridad**: para SPA (Vue) + API (Laravel), el patrón de auth es
   **token-based** (Sanctum) o **sesión con cookie + CSRF**. No son equivalentes en seguridad; se
   decide en `design.md` y es materia de `sdd-security-reviewer`.
4. **El enlace de activación** exige URL firmada con expiración y reenvío — tres criterios de
   aceptación verificables.

## Bloqueo previo detectado (medido, no teórico)

Al validar esta decisión contra el entorno y contra `init.sh`, aparece un bloqueo que **impide que el
gate verifique PHP**:

1. `init.sh` detecta el stack por manifiesto, y su lista **incluye `composer.json`**. Pero las ramas de
   **lint**, **format**, **typecheck** y **tests** solo contemplan `pyproject.toml`, `package.json` y
   `go.mod`. **No existe rama PHP.**
2. Consecuencia: en un proyecto Laravel, el gate reportaría esos cuatro checks como **`SKIP`** y
   terminaría en **`PASS`** — exactamente el problema de «gate que dice PASS sin comprobar nada».
3. Como `init.sh` es **el único gate (R6)** y está en `protectedFiles`, **ningún agente puede
   extenderlo**: requiere PR separada con aprobación humana.

**El bloqueo no invalida la decisión**: el flujo SDD (fases, artefactos, gates humanos, trazabilidad)
se puede probar igual. Lo que **no** se puede aún es la verificación automática del gate, que es una de
las garantías centrales.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Stack ya soportado por el gate** (Python/Node) | Permite probar el gate **completo** desde el primer día, sin tocar `init.sh` | No produce el template PHP que se necesita; y Python/Node ya están sesgados por ser el lenguaje de los scripts | Se pierde el objetivo de template, y el sesgo ya existe |
| **B. Proyecto Laravel sin tocar el gate** | Arranca de inmediato; prueba el flujo SDD y los gates humanos | El gate queda en `SKIP`: no se verifica la promesa central. Se descubre el problema, pero no se resuelve | Aceptable como **primer paso**, insuficiente como estado final |
| **C. Laravel + extender `init.sh` con soporte PHP** | Verificación real; el template nace completo | Requiere **PR de harness con aprobación humana** (R4), antes de empezar | — (la elegida, como **segundo paso**) |
| **D. Esperar a que el nivel 3 provea el gate desde `template.yaml`** | Arquitectónicamente correcto: el componente declara sus comandos | Depende del materializador (paso 6), que depende de ADR-007. Bloquearía la prueba detrás de dos features | Correcto a largo plazo, inaceptable como precondición de la primera prueba |

## Consecuencias

**Positivas**
- Ejercita el flujo completo con una superficie de dominio real (auth + datos + seguridad).
- Activa un rol que hasta hoy no se ha usado: `sdd-security-reviewer`.
- Produce el **template PHP de referencia** que habilita el nivel 3 para ese stack.
- PHP 8.2.12, Composer, PHPUnit y el instalador de Laravel **ya están presentes** en el entorno
  (verificado), así que no hace falta instalar toolchain.

**Negativas / deuda asumida**
- **Dependencia de `init.sh` para verificar PHP** (bloqueo de arriba). Hasta resolverlo, este
  componente es "verificado" por un gate que reporta `SKIP` en lint/format/typecheck/tests.
  **Deuda registrada explícitamente**: debe cerrarse antes de declarar el template como estándar.
- Introduce el **primer stack fuera de la tríada** soportada hoy por el gate (Python/Node/Go), lo que
  revela que el gate tiene conocimiento de stack embebido. Es precisamente el acoplamiento que el
  nivel 3 viene a eliminar.
- Laravel 12 es un **framework con opiniones**: su estructura y convenciones condicionan el
  `agent_profile.md`. Mitigación: el perfil se extrae de la práctica, no se diseña por anticipado.

**Neutrales**
- Sin Docker: la base de datos será local (XAMPP/MySQL o SQLite).

## Cómo revertir esta decisión

Elegir otro stack para la primera aplicación (alternativa A). No hay nada construido sobre esta
decisión todavía; revertir es cambiar el registro y empezar con otro `scope.md`.

## Plan en dos fases

### Fase 1 — Probar el flujo SDD (desbloqueada hoy)

Ejercita las cuatro fases y los tres gates humanos. Los huecos del gate serán visibles y se registran.

### Fase 2 — Verificación real (requiere PR de harness)

1. **PR de harness** (aprobación humana, R4): extender `init.sh` con rama PHP
   (lint: `php -l` o Laravel Pint; format: Pint `--test`; typecheck: PHPStan/Larastan; tests: `phpunit`).
2. Re-ejecutar el ciclo de verificación: `verify.md` con la salida **literal** del gate.
3. Publicar el template de referencia con `template.yaml` + `agent_profile.md`.

## Cómo se verificará

1. `.spec/auth/` contiene `scope.md` (con `Aprobado por:` humano — G1), `design.md`, `tasks/` y
   `contracts/api.openapi.yaml`.
2. Cada tarea de `tasks/` tiene **un** commit `sdd: task NNN - ...` (R2).
3. `verify.md` con veredicto y, **tras la fase 2**, la salida literal de `./init.sh` con los checks
   PHP en PASS (no en `SKIP`).
4. `dependency justification` en `design.md` para cada paquete de Composer y de npm añadido (§2.6).
5. El frontend consume el API **según el contrato**, y el contrato no cambia sin actualizar ambos
   componentes.

## Referencias

- `docs/propuesta-harness-instanciable.md` §10 (paso 4), §11 A6, §13 Anexo B
- `docs/desacoplamiento-arquitectura-software.md` — `template.yaml`, `agent_profile.md`
- `init.sh` (detección de manifiesto y ramas de checks), `AGENTS.md` §2.6, R4, R6
- ADR-008 (ciclo completo), ADR-007 (`scripts/` y rol maintainer)
