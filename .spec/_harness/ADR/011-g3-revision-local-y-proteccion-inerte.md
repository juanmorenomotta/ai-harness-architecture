# ADR-011 — G3 es revisión humana local; la protección de rama queda inerte y declarada

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE** (opción E, separar identidades)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Tareas afectadas**: ninguna por ahora. Registra un hallazgo de ejecutabilidad de **G3**

## Contexto

R3 de la ley establece: *«Nunca auto-merge. El agente abre PR; un humano aprueba y mergea.»*
Y **G3** es la transición `verify.md` → merge del PR, aprobada por un revisor humano.

Al activar la protección de rama en GitHub tras crear el remoto (ADR-010), GitHub mostró esta alerta:

> «Tus reglas no se aplicarán en este repositorio privado hasta que migres a una cuenta de
> organización de GitHub Team.»

Al verificar la documentación oficial, se confirma y se **descubre un problema mayor** que el que
plantea la alerta.

### Hallazgo 1 — La protección de rama no existe en repos privados Free

| Plan | Repos privados | Protected branches |
| :--- | :--- | :--- |
| **Free (personal y organización)** | Ilimitados, con «limited feature set» | **No** |
| **Pro** (personal) · **Team** (organización) | Sí | Sí |
| GitHub Enterprise | Sí | Sí + rulesets de organización |

La regla creada **se guarda pero no se aplica**. Está **inerte**: aparenta proteger y no protege.

### Hallazgo 2 — Aunque se pagara, no haría R3 ejecutable

Este es el hallazgo de fondo, y es más serio que el plan:

1. **Los administradores se saltan las reglas por defecto.** La documentación lo dice expresamente:
   *«las restricciones de una regla de protección de rama no se aplican a las personas con permisos
   de administrador»*. El responsable del harness es admin del repositorio. Aplicarla a admins exige
   activar «Do not allow bypassing the above settings» — lo que **bloquearía al propio humano**.

2. **GitHub ve UNA sola identidad.** Los agentes ejecutan comandos en la terminal del humano, con su
   `git config` y sus credenciales. **Para GitHub, «el agente» y «el humano» son la misma persona.**

Evidencia de este mismo repositorio: el `git push origin main` de la sesión del 2026-09-27 pasó sin
ninguna barrera, con el repositorio privado y la regla ya creada.

> **Conclusión: R3 es hoy una regla de proceso, no un control técnico.** Y **no se arregla con
> dinero**: ningún plan de GitHub distingue al agente del humano si comparten credenciales.

## Decisión

**G3 se ejecuta como revisión humana LOCAL en el estado actual, y la protección de rama se conserva
como configuración inerte y declarada.**

Tres partes:

1. **Ejecución de G3 (ahora)**: el humano revisa `verify.md` y el diff **antes** de que los commits
   lleguen a `origin/main`. La trazabilidad de la aprobación vive en `verify.md` (con la salida
   literal del gate), **no en una PR protegida**. El flujo SDD se ejercita íntegro; lo único que no
   existe es el mecanismo técnico.

2. **La regla de protección se conserva.** Se activará sola si el proyecto migra a una organización
   **Team** o superior. Borrarla obligaría a recordar que hay que volver a crearla.

3. **Mitigación obligatoria de la inercia**: este ADR es la mitigación. **Una configuración que
   aparenta proteger y no protege es peor que su ausencia**, porque induce a confiar en ella. El
   hallazgo queda declarado por escrito —igual que el harness trata un `SKIP` como *no verificado*,
   nunca como `PASS`— y se registra en el documento de arranque.

### La solución real (trabajo futuro)

R3 solo se vuelve ejecutable **separando identidades**: dar a los agentes credenciales con **menos
permisos** que las del humano. Por ejemplo, un *fine-grained PAT* o una GitHub App cuyo alcance sea
«crear pull request» pero **no** «push a `main`» ni «mergear».

Entonces el agente **no puede** mergear, con independencia de la configuración del repositorio y sin
depender de ningún plan.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Dejarlo como está, sin registrar el hallazgo** | Cero trabajo | La regla inerte **induce a confiar** en una protección que no existe. Es el patrón que este repositorio ya corrigió cuatro veces: un dato que aparenta ser control sin serlo | Deja una falsa garantía sin documentar |
| **B. Pagar GitHub Pro / Team** | Habilita la protección de rama | **No distingue agente de humano** (comparten credenciales) y el admin puede saltársela por defecto. Coste recurrente para un beneficio parcial | No resuelve el problema real; es gasto sin control |
| **C. Repositorio público** | Protección gratis (en públicos sí existe en Free) | Expone ley, políticas, decisiones y rutas de máquina (`.spec/_harness/diagnostic.md:94`). Contradice ADR-010 (privado) | Coste de confidencialidad desproporcionado |
| **D. Borrar la regla inerte** | Elimina la falsa apariencia de protección | Se pierde la configuración que se activaría al migrar de plan; hay que recordar recrearla | Preferible conservarla **y** declararla inerte (decisión del humano) |
| **E. Separar identidades** (PAT/App de menor privilegio para agentes) | **Gratis**; cierra el conflicto de raíz; el agente no *puede* mergear | Requiere configuración y gestión de credenciales (y **R9**: sin secretos en disco) | — (**la elegida como solución real**; implementación pendiente) |

## Consecuencias

**Positivas**
- El flujo SDD **no queda bloqueado**: G3 se ejecuta hoy como revisión humana local.
- El hallazgo queda declarado: nadie confiará en una protección que no opera.
- La solución real (opción E) es **gratuita** y se identifica sin ambigüedad.
- Coherente con **ADR-007**, donde el conflicto de interés se cerró porque el Developer **no tiene
  permiso** sobre `scripts/`, no porque se le pidiera no tocarlo.

**Negativas / deuda asumida**
- **R3 y G3 son reglas de proceso, no controles técnicos.** Un agente *podría* pushear a `main` y
  mergear. La barrera es la disciplina y la revisión humana, no el sistema. **Deuda registrada.**
- Hasta implementar la opción E, la garantía «un humano aprueba el merge» **depende de la
  honestidad del operador**, no de una capacidad ausente. Es una garantía débil.
- Hay una configuración en GitHub que no hace nada. Se acepta a cambio de tenerla lista para el futuro.

**Neutrales**
- La ley (`AGENTS.md`) **no cambia**: R3 sigue vigente como regla. Lo que cambia es el conocimiento
  de su **grado de ejecutabilidad**. Registrado conforme a §9 (*documentar el caso, no ignorar la regla*).
- ADR-010 (remoto privado) sigue válido: el remoto existe y sirve como respaldo y para ramas; lo que
  no aporta aún es la barrera de PR.

## Lección transversal

**Un límite es real cuando es capacidad ausente, no cuando es una instrucción.**

Es la quinta aparición del mismo patrón en este repositorio, y esta vez no es un dato duplicado sino
una **garantía aparente**:

| # | Patrón | Registro |
| :--- | :--- | :--- |
| 1 | Validar contra la fuente equivocada | ADR-001 |
| 2 | Confundir catálogo nativo con el de extensión | ADR-002 |
| 3 | Vínculo en prosa, sin check | ADR-003 |
| 4 | Cinco versiones sin coordinación | ADR-004 |
| 5 | **Un check en `SKIP` no es un `PASS`; una regla inerte no es una protección** | **ADR-011** |

## Cómo revertir esta decisión

Implementar la opción E (identidades separadas para agentes) y actualizar este ADR para reflejar que
la protección pasó a ser efectiva. Si además se migra a una organización Team, la regla de rama ya
está creada y empieza a aplicarse por sí sola.

## Cómo se verificará

1. **Estado actual**: `verify.md` contiene el veredicto y la aprobación humana registrada; el merge a
   `main` ocurre tras la revisión local. Evidencia: el registro de la revisión en `verify.md`.
2. **Estado final (opción E)**: un intento de push a `main` con las credenciales del agente **falla**
   por permisos. Ese es el criterio binario que demuestra que R3 es un control técnico.
3. **No confundir**: mientras la protección sea inerte, **no contarla como cumplimiento de R3** en
   `verify.md` (misma lógica que un check en `SKIP`).

## Referencias

- `AGENTS.md` §1 R3, §7 (gate G3), §9 (documentar en lugar de ignorar)
- ADR-010 de este directorio (remoto privado), ADR-007 (límite por capacidad ausente)
- Documentación oficial de GitHub: *About protected branches* y *GitHub's plans*
  (los planes Free no incluyen protected branches ni rulesets en repositorios **privados**)
