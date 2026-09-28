# ADR-013 — Componentes cross: clase de plataforma, ownership declarado y gates de compatibilidad

- **Fecha**: 2026-09-28
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Tareas afectadas**: esquema de `template.yaml` (campo `ownership`), `CODEOWNERS` (nuevo),
  `.agents/policies/permissions.yaml` (gates), `AGENTS.md` §7 (gate G4)

## Contexto

ADR-008 estableció dos modos de ciclo según la **naturaleza** del componente: completo (aplicación) y
ligero (infraestructura). El escenario real de uso revela una **tercera clase** que no encaja en
ninguna de las dos:

> «Podría desarrollar componentes basados en microservicios, por ejemplo un microservicio de envío de
> correos y mensajería, otro servicio de Gestión de Opciones de Menú, Perfiles de Usuarios para todas
> las aplicaciones de una empresa. Es decir, son componentes **CROSS**, que pueden ser utilizados por
> cualquier otra aplicación/componente. Un componente CROSS puede ser atendido por un único equipo:
> hay un **owner** del componente; sin embargo puede haber otro equipo que necesita hacer un cambio y
> puede instanciar el harness y clonar el repositorio para realizar el cambio, generando su
> especificación y siguiendo el patrón del harness, y enviar luego su Pull Request para la aprobación
> por parte del owner.»

Características que definen la clase:

| Característica | Consecuencia |
| :--- | :--- |
| **N consumidores desconocidos** | Un cambio puede romper a terceros que no controlas |
| **Owner único** | Hay una autoridad de aprobación distinta del contribuidor |
| **API como producto** | El contrato es un artefacto de primera clase, versionado |
| **Ciclo de vida largo** | Deprecación anunciada antes de romper |

Verificado en el repositorio (2026-09-28): **no existe mecanismo de ownership alguno**. No hay
`CODEOWNERS`, `harness.config.json` no declara dueño, y `permissions.yaml` solo menciona
`approver: "product-owner"` para G1. Es decir: en el escenario descrito, «PR aprobada por el owner»
sería una regla **sin artefacto** — la misma clase de hueco que ADR-011 documentó para G3.

## Decisión

**Se reconoce una tercera clase de componente —`cross`— con ownership declarado, contrato versionado y
un gate de compatibilidad propio (G4).**

### Clasificación (tres clases, por naturaleza)

| Clase | Ejemplo | Owner | Ciclo | Gate extra |
| :--- | :--- | :--- | :--- | :--- |
| **`app`** | El frontend de facturación | El equipo del producto | Completo (ADR-008) | — |
| **`infra`** | Base de datos, IaC | Plataforma | Ligero (ADR-008) | — |
| **`cross`** | Servicio de login, correos, perfiles, menús | **Un owner declarado** | Completo **+ gates de compatibilidad** | **G4** |

### Ownership declarado en el componente

```yaml
# apps/auth-service/template.yaml
component: auth-service
class: cross
ownership:
  owners: ["@juanmorenomotta"]        # responsable de la aprobación
  contact: "auth-team@example.com"
api:
  contract: "api/openapi.yaml"
  versioning: "semver"
  compatibility: "backward"            # backward | none
  breaking_change_policy: "major + deprecación anunciada"
  environments: ["dev"]                # dónde el consumidor puede probar
```

Esto resuelve el hueco de ownership y hace que la clase sea **auditable**: se declara, no se supone.

### Gate G4 — el contrato no rompe a los consumidores

El gate de un componente `cross` añade, sobre el ciclo completo:

| Comprobación | Qué detecta |
| :--- | :--- |
| **Compatibilidad del contrato** | Un cambio incompatible en la API sin incremento de major |
| **Versión declarada** | El artefacto de API no corresponde a la versión publicada |
| **Deprecación** | Se elimina algo sin el periodo de aviso declarado |
| **Ambiente publicado** | El consumidor no tendría dónde probar |

Y, en `harness.config.json`, G4 se declara junto a G1–G3:

```json
"requireHumanApprovalGates": ["G1", "G2", "G3", "G4"]
```

### El owner como gate humano

`CODEOWNERS` (nuevo, en cada repo `cross`) materializa la aprobación:

```
# .github/CODEOWNERS
*       @juanmorenomotta
```

Con rama protegida + «Require review from Code Owners», la PR de un contribuidor **exige** la
aprobación del owner. Con la salvedad de ADR-011: en repos privados de plan Free la protección es
**inerte**, así que la aprobación del owner es hoy un **gate de proceso**; se vuelve técnica al separar
identidades o al migrar de plan.

## Alternativas consideradas

| Alternativa | Pros | Contrato | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Tratar los cross como `app`** | Sin conceptos nuevos | Ciclo completo estándar | Un cambio de API puede romper a N consumidores **sin ninguna barrera**. El gate no lo detecta |
| **B. Tratar los cross como `infra` (ligero)** | Menos ceremonia | Ligero | Un componente consumido por terceros es **más** exigente que una app, no menos |
| **C. Un repo central de ownership** | Un solo sitio | — | El dueño natural de un componente es su repositorio; centralizar crea un punto de desincronización |
| **D. Clase `cross` con ownership declarado + G4** | La clase se declara y se audita; G4 detecta rupturas; CODEOWNERS materializa la aprobación | Backward compatible por defecto | — (la elegida) |

## Consecuencias

**Positivas**
- La tercera clase es **explícita y auditable** (`class: cross` en el componente).
- El ownership tiene **artefacto** (`ownership` + `CODEOWNERS`), no es una convención verbal.
- **G4 detecta la ruptura de contrato antes** de que llegue a los consumidores, que es el riesgo
  central de un componente compartido.
- Alinea el harness con el escenario real de una empresa con servicios compartidos.

**Negativas / deuda asumida**
- **Tercera clase y cuarto gate**: más conceptos que un agente debe interpretar en arranque en frío.
- La comprobación de compatibilidad de contrato requiere herramienta (comparador de OpenAPI); es
  trabajo de implementación, y hoy **el gate no verifica nada de esto**.
- En repos privados Free, la aprobación del owner es **de proceso** (ADR-011 aplica igual).
- La clasificación `cross` exige un juicio al declarar cada componente. Mitigación: el campo es
  obligatorio y explícito, y cambiarlo requiere decisión registrada.

**Neutrales**
- `auth` pasa a ser `cross` (ADR-009 revisado): es consumido por el frontend, y su API es su producto.

## Cómo revertir esta decisión

Eliminar la clase `cross` y clasificar esos componentes como `app`. Se pierde la detección de rupturas
de contrato. Barato de ejecutar; el riesgo asumido es alto.

## Cómo se verificará

1. Un componente `cross` declara `class: cross` y `ownership.owners` en su `template.yaml`.
2. Existe `.github/CODEOWNERS` y su dueño coincide con `ownership.owners`.
3. **Prueba negativa**: un cambio incompatible en el contrato **hace fallar G4** (o el check de
   compatibilidad) con código distinto de cero.
4. `harness.config.json` lista G4 entre los gates que requieren aprobación humana.

## Referencias

- ADR-008 (modo por naturaleza), ADR-011 (protección inerte), ADR-012 (un nivel: el repositorio),
  ADR-014 (contribución externa y G4 sobre PR a componente ajeno)
- `AGENTS.md` §1 R3, §7 (gates); `.agents/policies/permissions.yaml`
- `docs/desacoplamiento-arquitectura-software.md` (`template.yaml`)
