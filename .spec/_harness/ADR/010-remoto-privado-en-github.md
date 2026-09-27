# ADR-010 — Remoto privado en GitHub para que R3 sea ejecutable

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **A7** de `docs/propuesta-harness-instanciable.md`
- **Tareas afectadas**: configuración de git del repositorio (nada versionado)

## Contexto

**R3** de la ley establece:

> **Nunca auto-merge.** El agente abre PR; un humano aprueba y mergea.

Y el gate **G3** es la transición `verify.md → merge del PR`, aprobada por un revisor humano.

Verificado el 2026-09-27: **el repositorio no tiene ningún remoto configurado** (`git remote -v` está
vacío). Sin remoto no hay PR, así que **R3 y G3 no son ejecutables**. El flujo podría llegar hasta
`verify.md`, pero el último tramo —el que garantiza la revisión humana antes de integrar— no tiene
artefacto.

Esto importa ahora porque se va a **instanciar el primer proyecto** (ADR-009) y se quieren ejecutar los
tres gates completos.

## Decisión

**Se crea un repositorio remoto privado en GitHub, y se documenta el protocolo de PR + revisión humana
que materializa R3 y G3.**

Forma de la decisión:

| Aspecto | Valor |
| :--- | :--- |
| Proveedor | **GitHub** |
| Visibilidad | **Privado** |
| Rama principal | `main`, protegida |
| Ramas de trabajo | `spec/<feature>`, `task/<feature>/NNN`, `verify/<feature>` (AGENTS.md §3) |
| Merge | **Solo por PR con aprobación humana.** Nunca auto-merge (R3) |
| Autor del merge | Debe ser **distinto** del agente autor (G3) |

### Protocolo que instaura

1. El agente trabaja en `task/<feature-slug>/NNN` y hace **un commit** por tarea (R2).
2. El agente **abre la PR**, con el mensaje que referencia `task NNN`.
3. Un **humano** revisa y mergea (G3). Ningún agente mergea, y ningún agente aprueba su propio gate.
4. La PR es el artefacto que cierra el ciclo: queda el rastro de quién revisó y cuándo.

### Sobre el mecanismo de creación

No se requiere `gh` (GitHub CLI) ni token en el entorno: **`gh` no está instalado** (verificado) y
crear el repositorio es una operación **humana de una sola vez**. El canal normal para el agente es
trabajar con un remoto ya configurado.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Sin remoto** (estado actual) | Cero configuración | **R3 y G3 inejecutables**. El último gate humano se vuelve una convención verbal sin artefacto | Deja sin ejecutar el gate que garantiza la revisión humana |
| **B. Remoto privado en GitHub** | Estándar; PRs con revisión; gratis para repos privados; ramas protegidas | Requiere alta manual una vez | — (la elegida) |
| **C. Remoto en GitLab / Bitbucket** | Preferencia de organización | Equivalente funcionalmente; la elección entre ellos es indiferente al harness | No hay razón que incline la balanza; se documenta la elección |
| **D. Remoto local (`file://` o bare repo)** | Sin dependencia externa | Sin interfaz de PR: no hay revisión ni aprobación registrable | No materializa R3 |

## Consecuencias

**Positivas**
- **R3 y G3 pasan a ser ejecutables**: hay PR, hay revisión, hay rastro de quién aprobó.
- Habilita el trabajo en ramas (R2: una tarea = un commit en su propia rama).
- Backup remoto y trazabilidad de la historia del harness.
- Coherente con **D1** (ADR-004): un proyecto instanciado puede fijar la versión del harness contra un
  remoto real.

**Negativas / deuda asumida**
- Alta manual inicial (operación humana, una vez).
- **Elegir la visibilidad es un juicio de seguridad**: el repositorio se declara privado para no
  exponer decisiones internas. Si en el futuro se decide publicar (por ejemplo, como framework open
  source), habrá que **auditar que no haya secretos ni rutas locales en la historia** — el
  `diagnostic.md` ya contiene una ruta absoluta de máquina, y eso sería material a limpiar.
- Sin `gh`, las operaciones de PR se hacen por la interfaz web o instalando la CLI. Es fricción, no un
  bloqueo.

**Neutrales**
- No cambia ningún archivo versionado: la configuración del remoto vive en `.git/config`, que no se
  versiona.
- Los adaptadores y `.harness/` no se ven afectados.

## Cómo revertir esta decisión

`git remote remove origin`. Se vuelve al estado actual y R3/G3 quedan de nuevo como convención. Barato
de ejecutar.

## Cómo se verificará

1. `git remote -v` → muestra `origin` apuntando a GitHub.
2. Rama `main` protegida en GitHub (sin push directo, sin force push).
3. **Prueba de extremo a extremo**: una PR de prueba desde `task/<feature>/NNN` que un humano revisa y
   mergea. El registro de la PR es la evidencia de que R3 y G3 son ejecutables.
4. `bash init.sh` → `guardrails` en PASS (el cambio del remoto no toca archivos protegidos).

## Referencias

- `docs/propuesta-harness-instanciable.md` §9 (estado medido), §11 A7
- `AGENTS.md` §1 R3 (nunca auto-merge), §3 (convenciones de ramas y commits), §7 (gate G3)
- ADR-009 (la primera aplicación que se verá afectada), ADR-004 (versión fijable)
