# ADR-014 — Contribución externa: `.spec/` propio en rama propia, y el caso «un humano en dos sombreros»

- **Fecha**: 2026-09-28
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Tareas afectadas**: `AGENTS.md` §3 (convención de ramas) y §7 (regla del mismo humano), gates G3/G4

## Contexto

El escenario: **un desarrollador necesita cambiar un componente cuyo owner es otro.**

> «Puede haber otro equipo que necesita hacer un cambio y puede instanciar el harness y clonar el
> repositorio con todo lo necesario para realizar el cambio generando su especificación y siguiendo el
> patrón del harness, y el agente puede enviar luego su Pull Request (PR) para la aprobación por parte
> del owner del componente, un humano.»

Con ADR-012 (un solo nivel: el repositorio), esto se resuelve de forma natural: **el contribuidor
trabaja en el repositorio del componente**, con su `.spec/`, en **una rama propia**, y su PR va contra
`main`.

Cómo se propuso antes —un subárbol `_component/` + `contrib/<change-id>/` dentro del repositorio del
owner— **se descarta**: duplicaría ámbitos dentro de un repositorio que ADR-012 declara plano, y
además el `.spec/` del contribuidor es **del cambio**, no una visión permanente del componente.

### Dos ambigüedades que la ley actual no resuelve

1. **R3 y G3 asumen un solo repo y un solo revisor.** G3 se define como `verify.md → merge`, aprobado
   por *«un revisor humano (nunca el mismo agente)»*. No contemplan que quien aprueba sea el **owner**
   de un componente y el contribuidor sea **otro actor**.
2. **El caso «un humano en dos sombreros» no está cubierto.** La ley prohíbe que **un agente** apruebe
   su propio gate, pero no dice nada de que **el mismo humano** sea owner y contribuidor a la vez.
   Con un desarrollador Full Stack manteniendo N componentes, ese caso es **la norma**, no la excepción.

Además, ADR-011 ya estableció que en repos privados de plan Free la protección de rama es **inerte**,
así que la aprobación del owner es hoy un gate de **proceso**.

## Decisión

**El contribuidor externo instancia el harness en el repositorio del componente, escribe su `.spec/`
del cambio en una rama propia, y abre la PR contra `main`. La aprobación del owner es el gate G4.**

### Flujo del contribuidor

```
1. Clonar el componente  →  apps/auth-service/
2. Instanciar el harness →  (o verificar que ya está instanciado y con qué versión)
3. Rama propia           →  contrib/<change-id>        (nunca main)
4. Su .spec/ del cambio  →  .spec/<feature>/scope.md, design.md, tasks/, verify.md
5. Ciclo SDD sobre su rama
6. PR contra main del componente  →  la aprueba el OWNER (G4)
```

Puntos clave:

- **Un `.spec/` por cambio**, no un ámbito separado. La feature describe *el cambio*, y el historial de
  cambios queda en la historia de git.
- **El contribuidor no necesita la `.spec/` completa del componente**: se integra por el **contrato**
  (ADR-012), no leyendo el repositorio entero.
- **La rama es `contrib/<change-id>`**, distinta de `task/<feature>/NNN` (que es para cambios del
  propio owner). La distinción deja el rastro de quién es dueño y quién contribuye.

### Gates aplicables

| Gate | Transición | Aprueba |
| :--- | :--- | :--- |
| **G1** | `scope.md` → `design.md` | Product Owner humano |
| **G2** | `design.md` + `tasks/` → implementación | Tech Lead humano |
| **G3** | `verify.md` → integración en la rama | Revisor humano |
| **G4** | PR → `main` del componente | **Owner del componente** (humano) |

### La regla del «mismo humano en dos sombreros»

**Regla**: *un humano puede ser owner y contribuidor, pero debe declararlo explícitamente en
`verify.md`.*

```
Verificación y aprobación
- Contribuidor: Juan Moreno
- Owner que aprueba: Juan Moreno
- Nota: mismo actor en ambos roles (declarado conforme a la regla de ADR-014).
  La separación funcional la garantizan las fases (cada una arranca en frío contra disco)
  y el gate del repositorio; NO la separación de personas.
```

Justificación: la ley prohíbe que **un agente** valide su propio trabajo porque el error es
**correlacionado**. Con un mismo humano, el error también es correlacionado, pero **no es evitable**
—el owner del componente es quien tiene la autoridad—. La mitigación real es:

1. **Arranque en frío**: cada fase lee artefactos en disco, no memoria de la conversación.
2. **Evidencia del gate**: la salida literal de `./init.sh` en `verify.md`, no la afirmación del autor.
3. **La declaración explícita**: hacer visible el doble rol en lugar de ocultarlo.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Subárbol `_component/` + `contrib/<id>/` en el repo del owner** | Separa la visión del componente y la del contribuidor | **Duplica ámbitos** dentro de un repositorio que ADR-012 declara plano. Y el `.spec/` del cambio no es permanente: es del cambio | Contradice ADR-012 y complica el arranque en frío |
| **B. El contribuidor trabaja en su fork** | Aislamiento total | El fork no tiene el harness instanciado ni la versión declarada; reproduce el problema de identidad de ADR-006 | Fricción sin beneficio con ADR-012 |
| **C. Prohibir contribuciones externas** | Sin complejidad | Contradice el escenario central del harness | Inaceptable |
| **D. Rama propia con `.spec/` del cambio + G4 del owner** | Aprovecha el modelo de un nivel; deja rastro de ownership en la rama; sin ámbitos duplicados | Requiere distinguir `contrib/` de `task/` en la convención | — (la elegida) |

## Consecuencias

**Positivas**
- El contribuidor **no necesita** el contexto completo del componente: se integra por contrato, con
  `.spec/` para **su** cambio.
- El doble rol del desarrollador Full Stack queda **legítimo y visible**, en lugar de ser una laguna
  que cada agente interpretara a su manera.
- La distinción `task/` vs `contrib/` deja claro quién es dueño y quién contribuye, en el propio
  nombre de la rama.
- G4 tiene un aprobador identificable (el owner declarado en `template.yaml`, ADR-013).

**Negativas / deuda asumida**
- **El error correlacionado es real** cuando un humano es autor y aprobador. No se elimina; se mitiga
  con arranque en frío y evidencia del gate. **Deuda registrada.**
- El contribuidor necesita que el componente **publique un ambiente** para probar su integración
  (ADR-012). Sin ambiente, su `verify.md` no puede demostrar integración.
- En repos privados Free, G4 es un gate de **proceso** (ADR-011).
- Un `change-id` requiere convención (`kebab-case`, 2–4 palabras) para no colisionar en ramas.

**Neutrales**
- No cambia los roles ni las skills: el contribuidor usa los mismos.
- No añade carpetas nuevas al repositorio.

## Cómo revertir esta decisión

Volver a exigir aprobadores distintos del autor. Implicaría que el owner **no pueda** cambiar su propio
componente, lo que es inviable para un desarrollador único.

## Cómo se verificará

1. Una contribución externa usa una rama `contrib/<change-id>` y su PR es contra `main` del componente.
2. La PR es aprobada por el `ownership.owners` declarado en el `template.yaml` (G4).
3. Si el autor y el aprobador son **el mismo humano**, `verify.md` contiene la declaración explícita
   del doble rol.
4. `AGENTS.md` §7 documenta la regla del mismo humano (→ **PR de harness**, R4).

## Referencias

- ADR-012 (un nivel: el repositorio), ADR-013 (`cross`, ownership, G4), ADR-011 (protección inerte)
- `AGENTS.md` §1 R3, §3 (convenciones de ramas), §7 (gates y «un agente nunca aprueba su propio gate»)
- `docs/propuesta-harness-instanciable.md` (escenario de uso)
