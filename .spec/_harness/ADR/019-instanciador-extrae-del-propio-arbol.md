# ADR-019 — El instanciador extrae del propio árbol y verifica la instancia

- **Fecha**: 2026-10-04
- **Estado**: `aceptada` · **Implementación**: **HECHA** (pendiente de revisión humana)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: pendiente **3** de `docs/pendientes.md` (ADR-006)
- **Resuelve**: decisión **D-1** en su forma definitiva (opción D)
- **Tareas afectadas**: `scripts/instantiate_harness.py` (nuevo)

## Contexto

ADR-006 decidió que **el `AGENTS.md` de cada repositorio instanciado se genera** desde (ley base +
parámetros), y que el drift se controla con un modo `--check`. Pero no fijó **de dónde
toma el harness base**, y esa era la decisión abierta **D-1**.

### Por qué no vale clonar

La recomendación inicial fue clonar por tag (opción B). Al verificarla se descartó por dos hechos:

| Hecho verificado | Consecuencia |
| :--- | :--- |
| **No existía ningún tag**, ni local ni remoto | La opción B no era ejecutable en ese momento |
| **El repositorio es privado** | Clonar sin intervención exige credenciales. **R9 prohíbe secretos en disco**, y depender del *credential manager* haría la operación **no determinista**: funciona en una máquina y falla en otra |

### El nombre del script

`docs/pendientes.md` y los ADR anteriores lo llamaban `instanciar-harness.py` (español). `AGENTS.md` §3
exige identificadores en **inglés**, y los scripts existentes lo cumplen (`validate_harness.py`,
`sync-adapters.sh`, `diagnose_harness.py`). Se adopta **`instantiate_harness.py`** y se corrigen las
referencias **operativas** de todos los documentos. Las menciones que describen el nombre antiguo se
conservan: documentan la divergencia corregida, que es información útil.

## Decisión

**El instanciador vive dentro del harness y extrae del propio árbol con `git archive HEAD`, exigiendo
árbol limpio en archivos rastreados. Fabrica un componente autosuficiente y ofrece un modo `--check`
que verifica la instancia.**

### 1. Origen: el propio árbol, no un clon

```bash
git archive --format=tar HEAD | tar -x -f - -C <destino>
```

| Ventaja | Por qué |
| :--- | :--- |
| **Determinista** | `archive` toma **el commit**, no el árbol de trabajo |
| **Sin red ni credenciales** | No se clona el repo privado → R9 intacto |
| **Autoverificable** | El script comprueba su propia procedencia antes de extraer |
| **Simple** | `git` y `tar` ya presentes (verificados) |

**Precondición**: no puede haber cambios **rastreados** sin commitear. Si el commit no los incluye, lo
extraído no sería lo que el usuario ve.

> **Nota de diseño**: la comprobación mira solo archivos **rastreados**. Los no rastreados (`??`) no
> importan, porque `git archive HEAD` **nunca los incluiría**. La primera versión los contaba como
> suciedad y habría impedido instanciar en cualquier repositorio con archivos locales ignorados a
> propósito — que es el caso de este harness.

### 2. Las cuatro operaciones (ADR-006)

| Operación | Implementación |
| :--- | :--- |
| **Fijar la versión** | Lee `.harness/harness.version` (ADR-004) y el commit exacto; **ambos** se registran |
| **Resolver identidad** | Reescribe `repository.name` y `defaultBranch` en `harness.config.json` |
| **Limpiar herencia** | Elimina del componente lo que es del framework: `.spec/_harness/`, `.spec/validator-runner/`, `docs/` |
| **Dejar el enlace auditable** | `.harness/instanced.json` con `{component, harness, commit}` |

Además **regenera el `AGENTS.md`** con dos cambios respecto a la ley base:

- Sustituye **§4** por una versión del componente, porque ADR-006 establece que §4 deja de ser ley y
  pasa a ser parámetro: en un componente las rutas dependen de él, no del método.
- Añade una cabecera **«NO EDITAR A MANO»** con la procedencia, y ajusta la línea de «Versión del
  contrato» para apuntar al harness del que nace.

Y escribe un **`README.md` propio**, porque el del harness describía el framework.

### 3. Verificación de la instancia: el modo `--check`

Comprueba tres cosas, sin regenerar nada (misma forma que `sync-adapters.sh --check`):

1. **La ley lleva la marca de generado.** Si no, alguien la editó a mano — y un componente no debe
   editar su ley (ADR-006, R4).
2. **§4 está presente** (la sección del componente).
3. **La procedencia existe** y declara la versión del harness.

Y **avisa** (no falla) si la instancia va por una versión anterior del harness disponible: eso es la
señal de que toca re-instanciar para recibir cambios del harness.

### 4. Historia propia

El componente se inicializa con **su propio** `git init` y un commit inicial. No comparte la historia
del harness (ADR-012): son repositorios independientes.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Copia local del árbol de trabajo** | Trivial de implementar | Arrastra cambios sin commitear; no hay garantía de qué versión se copió | Extraería algo distinto de lo que se ve |
| **B. `git clone` por tag** | Mecanismo estándar de git | **Repo privado → credenciales** (R9) y comportamiento **no determinista** según la máquina. Requería crear tags | Es la opción que se descartó al verificar los hechos |
| **C. `git archive` de una ref remota** | Igual que B pero sin historial | Sigue necesitando red y credenciales | Mismo problema que B |
| **D. `git archive HEAD` del propio árbol + `--check`** | Sin red ni credenciales; determinista; autoverificable; sin tags | Requiere árbol limpio; el instanciador debe ejecutarse **desde dentro** del harness | — (la elegida) |

## Consecuencias

**Positivas**
- **Desbloquea el pendiente 4**: existe una forma reproducible de crear el repositorio de un componente.
- **El componente es autosuficiente.** Verificado: su `validate_harness.py` da **COHERENTE (136
  comprobaciones)** y su `init.sh` da **PASS (exit 0)**, sin consultar el harness.
- El **drift es detectable**: `--check` falla si la ley se editó a mano o falta la procedencia.
- La procedencia registra **versión y commit**: un tag se puede mover, un SHA no.

**Negativas / deuda asumida**
- **El instanciador exige árbol limpio en archivos rastreados.** Si estás a mitad de un cambio, no
  puedes instanciar. Es deliberado: garantiza que lo extraído es lo que se ve.
- El `--check` **no detecta** si la ley diverge por un cambio del harness subyacente: solo sabe avisar
  de que la versión es distinta. La comparación exhaustiva exigiría regenerar y comparar, que es
  trabajo futuro.
- El componente hereda el `$schema` colgante de `harness.config.json` (pendiente 16). Es un aviso en su
  propio validador, no un fallo.
- **El nombre del script difiere de la documentación previa** (`instanciar-harness.py`). Se corrigen
  las referencias, pero el apunte queda porque es el tipo de divergencia que el repositorio persigue.

**Neutrales**
- No toca ningún rol, skill ni adaptador. `harness.config.json` del harness no cambia.
- La ley base **no se modifica**: el instanciador la lee, no la edita (el `AGENTS.md` generado es del
  componente, no del harness).

## Cómo revertir esta decisión

Eliminar `scripts/instantiate_harness.py` y volver a crear componentes a mano. El harness queda intacto;
se pierde la reproducibilidad y el enlace de procedencia.

## Cómo se verificó

1. **Prueba real**: `python scripts/instantiate_harness.py --name auth-service --target
   a:\proyectos\auth-service` → **exit 0**, componente creado.
2. **Autosuficiencia del componente**:
   - `python scripts/validate_harness.py` → **136 comprobaciones, COHERENTE, exit 0**
   - `bash init.sh` → **PASS, exit 0**
3. **Aislamiento de la herencia**: `.spec/_harness/`, `.spec/validator-runner/` y `docs/` **no** están
   en el componente; `.spec/` arranca vacío con solo `.gitkeep`.
4. **Identidad**: `repository.name` es `auth-service`; la ley lleva la cabecera de generado con
   `Componente: auth-service · harness 1.0.0`; hay historia git propia (1 commit).
5. **Cuatro pruebas negativas**, cada una con código de salida **no cero** y el fixture revertido:
   - Árbol con cambios **rastreados** → **bloqueo (exit 2)**, listando los archivos
   - Ley editada a mano (sin la marca de generado) → **exit 1**
   - Instancia sin `.harness/instanced.json` → **exit 1**
   - Tras revertir los fixtures → **INSTANCIA COHERENTE (exit 0)**
6. **El harness original queda intacto**: 136 comprobaciones, adaptadores sincronizados, 18 ADR.

### Defectos encontrados durante la implementación

Los tres se corrigieron y se probaron, y ninguno se habría detectado sin ejecutar de verdad:

| Defecto | Causa |
| :--- | :--- |
| `git archive` capturado como texto | Produce un **tar binario**; `capture_output` + `text=True` rompía la decodificación |
| `tar` no leía de stdin | En Windows necesita **`-f -`** explícito; sin él intentaba abrir `\\.\tape0` |
| `UnicodeEncodeError` al imprimir las marcas | `✔`/`✘` no existen en **cp1252**. Se reutilizó la degradación a ASCII de `validate_harness.py` (§2.3) |

## Referencias

- ADR-006 (el `AGENTS.md` se genera), ADR-012 (un nivel: el repositorio), ADR-004 (versión única)
- ADR-013 (`cross`: el contrato es del componente), ADR-016 (arranque en frío por conversación nueva)
- `docs/pendientes.md` (pendientes 3 y 4; decisión D-1)
- `scripts/instantiate_harness.py`, `scripts/validate_harness.py` (degradación a ASCII reutilizada)
