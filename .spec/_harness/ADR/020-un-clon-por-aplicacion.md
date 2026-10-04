# ADR-020 — Un clon del harness por aplicación; el workspace es una carpeta sin versionar

- **Fecha**: 2026-10-04
- **Estado**: `aceptada` · **Implementación**: **HECHA** (documental: guía de arranque)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Completa**: el «manifiesto de workspace» que ADR-012 dejó como residuo sin concretar
- **Tareas afectadas**: `docs/inicio-harness-sdd.md` §7 (subsección de arranque)

## Contexto

ADR-012 estableció **un solo nivel de instanciación: el repositorio**. Al hacerlo, identificó un
«único residuo legítimo»: cuando un actor mantiene N componentes a la vez necesita saber **cuáles tiene
y en qué versión del harness van**. Lo llamó *manifiesto de workspace* y lo declaró **local, del actor,
no versionado**, pero **no concretó su forma**.

Al escribir la guía de arranque para un desarrollador nuevo quedaron dos preguntas sin responder:

1. **¿El harness se clona una vez, o una por aplicación?**
2. **¿Dónde vive el workspace: es una carpeta, un repositorio, o un archivo?**

Y una tercera, implícita: **¿cuánta libertad tiene el desarrollador para organizarse?**

## Decisión

**Se clona el harness una vez por aplicación. El workspace es una carpeta simple (sin `git init`) que
agrupa los componentes de UNA aplicación, y el desarrollador puede tener varios workspaces donde
quiera.**

```
A:\proyectos\facturacion\                    ← WORKSPACE 1 (carpeta sin git)
├── ai-harness-architecture\                 ← clon del harness (repo git)
├── api-service\                             ← componente (repo git)
├── web-portal\                              ← componente (repo git)
└── auth-service\                            ← componente (repo git)

D:\clientes\acme\inventario\                 ← WORKSPACE 2 (otra ruta, otra aplicación)
├── ai-harness-architecture\                 ← SU PROPIO clon del harness
├── stock-service\                           ← componente
└── admin-portal\                            ← componente
```

### 1. Un clon del harness por aplicación

| Consecuencia | Por qué es la opción elegida |
| :--- | :--- |
| Cada aplicación queda **autocontenida** | Se puede mover, copiar o archivar entera |
| Actualizar el harness es **una decisión por aplicación** | El `git pull` de un workspace no afecta a otro |
| Los componentes de una app ven **una sola versión** del harness | No hay que razonar sobre versiones cruzadas dentro de la app |
| Coste: N clones del repo del harness | Aceptado: el repo es pequeño (0.4 MB) y el aislamiento vale más |

### 2. El workspace es una carpeta, no un repositorio

`A:\proyectos\facturacion\` **no tiene `.git`**. Es una carpeta que agrupa repositorios git
independientes. **No se versiona**, no se clona y no se comparte.

Motivo: **no hay nada que versionar**. El contenido del workspace son los repositorios de cada
componente, que ya tienen su propia historia (ADR-012). Versionar el contenedor duplicaría la
información y crearía un repositorio cuyo único contenido son referencias a otros repositorios.

### 3. El desarrollador puede tener varios workspaces, donde quiera

**No hay una ruta canónica obligatoria.** El workspace vive donde al desarrollador le convenga:

- Varios workspaces en la misma carpeta padre: `A:\proyectos\facturacion\`, `A:\proyectos\inventario\`
- Workspaces dispersos: `A:\facturacion\`, `D:\clientes\acme\inventario\`
- Un workspace por cliente, o por producto, o por lo que el actor decida

**El harness no impone la organización del disco**, porque no depende de ella: cada componente es
autosuficiente (ADR-012) y su procedencia está registrada (ADR-019).

### 4. Lo que NO cambia

| Aspecto | Sigue igual |
| :--- | :--- |
| Un solo nivel de instanciación | El **repositorio** (ADR-012) |
| Cada componente, un repo independiente | Sí, con su propia historia |
| El contrato | Es del **proveedor**; el consumidor lo referencia con pin |
| La procedencia | `.harness/instanced.json` en cada componente (ADR-019) |
| Los componentes de un workspace | Son **de la misma aplicación** por definición del workspace |

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Un clon compartido del harness para todas las aplicaciones** | Un solo `git pull` actualiza todo | Dos aplicaciones de clientes distintos quedan acopladas por la versión del harness; actualizar el harness afecta a ambas a la vez. El workspace deja de significar «esta aplicación» | Rompe la independencia entre aplicaciones, que es lo que el workspace representa |
| **B. El workspace como repositorio git** (con submódulos o similar) | Versiona el conjunto; una sola operación para clonar todo | Los submódulos son frágiles y no aportan nada aquí: los componentes ya tienen su historia. Añade un repositorio cuyo contenido son punteros | Duplica la información y añade complejidad sin beneficio (ya descartado en ADR-012 para el nivel de `.spec/`) |
| **C. Una ruta canónica obligatoria** (`~/proyectos` siempre) | Uniformidad entre desarrolladores | Impone una organización que no todos quieren; y no aporta nada verificable | Contradice la flexibilidad que el modelo permite |
| **D. Un clon por aplicación + workspace como carpeta libre** | Cada app autocontenida; versión del harness clara por app; el desarrollador se organiza como quiera | N clones del harness; cada app requiere su propio `git pull` | — (la elegida) |

## Consecuencias

**Positivas**
- **La aplicación es la unidad de trabajo**: su carpeta agrupa todo lo que necesita (harness +
  componentes) y se puede mover o archivar completa.
- **La versión del harness es un hecho por aplicación**, no una variable global: dos apps pueden ir por
  versiones distintas sin interferirse.
- **El desarrollador no está atado a una estructura de disco**: puede tener varios workspaces en
  rutas distintas.
- Cierra la ambigüedad que ADR-012 dejó abierta sobre el manifiesto de workspace.

**Negativas / deuda asumida**
- **N clones del harness**: actualizar el harness en 5 aplicaciones son 5 `git pull`. Es el precio del
  aislamiento, y es explícito.
- **Un componente no puede pertenecer a dos aplicaciones.** Si surge la necesidad, ese componente es en
  realidad un **componente `cross`** (ADR-013): vive en su propio repo y lo consumen varias apps por
  contrato, no por compartir carpeta.
- El `workspace.yaml` que ADR-012 esbozó **no se implementa** por ahora: con varios componentes por
  aplicación se puede saber qué hay mirando la carpeta. Queda como idea si algún día hay muchos.

**Neutrales**
- No cambia ningún artefacto del harness, ni roles, ni skills, ni el gate.
- No afecta a la ley: el desarrollador organiza su disco como quiera, no cambia **qué** se escribe.

## Cómo revertir esta decisión

Adoptar un clon compartido del harness (alternativa A). Los componentes ya instanciados no cambian
—llevan su procedencia registrada—, pero las aplicaciones dejarían de ser independientes entre sí.

## Cómo se verificó

1. **La carpeta del workspace no es un repositorio**: verificado que `A:\proyectos\` **no** tiene
   `.git` (el propio caso del responsable).
2. **Nada en el harness depende de la ruta del workspace**: `instantiate_harness.py` resuelve su raíz
   con `Path(__file__).resolve().parent.parent`, así que funciona desde cualquier clon en cualquier
   ruta. Verificado en el código.
3. **El script acepta rutas relativas** (`--target ..\api-service`), de modo que el layout funciona
   desde cualquier ubicación.
4. La guía documenta el arranque con este layout, sin rutas absolutas de una máquina concreta.

## Referencias

- ADR-012 (un solo nivel: el repositorio; el «manifiesto de workspace» que este ADR concreta)
- ADR-013 (componentes `cross`: la vía correcta para lo que sirve a varias aplicaciones)
- ADR-019 (procedencia registrada: versión + commit del harness)
- `docs/inicio-harness-sdd.md` §7 (subsección «Arranque desde cero»)
