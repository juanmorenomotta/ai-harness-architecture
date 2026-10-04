# ADR-018 — La identidad del repositorio se declara y se verifica

- **Fecha**: 2026-10-04
- **Estado**: `aceptada` · **Implementación**: **HECHA** (pendiente de revisión humana)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: pendiente **11** de `docs/pendientes.md`
- **Tareas afectadas**: `harness.config.json`, `scripts/validate_harness.py`

## Contexto

`harness.config.json` declaraba:

```json
"repository": {
  "name": "deepseek-harness"
}
```

`deepseek-harness` es **el nombre de otro repositorio**. El de este es `ai-harness-architecture`. El
error llevaba ahí desde el primer commit, y se había registrado como hallazgo en
`docs/propuesta-harness-instanciable.md` §2 sin corregirse.

### Por qué no era cosmético

ADR-006 decide que **el `AGENTS.md` de cada repositorio instanciado se genera** desde (ley base +
parámetros). Y ADR-012 establece que el instanciador **lee la identidad de aquí**.

Por tanto, el campo es la **fuente de identidad de cada componente nuevo**. Con el valor equivocado,
todo componente instanciado habría nacido con el nombre de otro repositorio, y su `AGENTS.md` generado
habría heredado el error. Era **precondición del pendiente 3** (`scripts/instantiate_harness.py`).

### Un segundo defecto, encontrado en el mismo sitio

```json
"$schema": "./.harness/harness.config.schema.json"
```

El archivo **no existe**. El `$schema` apunta a un esquema que nunca se creó: una referencia colgante
que aparenta validación inexistente.

## Decisión

**La identidad del repositorio se declara en `repository.name` y se verifica con dos controles de
severidad distinta.**

### 1. El valor corregido

```json
"repository": {
  "name": "ai-harness-architecture"
}
```

### 2. Dos controles, porque son dos riesgos distintos

| Caso | Cuándo ocurre | Severidad | Por qué |
| :--- | :--- | :--- | :--- |
| **A.** El harness tiene el nombre de otro repositorio | Lo que se acaba de corregir | **aviso** | El harness funciona igual; el campo solo hace daño al instanciar |
| **B.** Un componente instanciado conserva el nombre del harness | El generador no reescribe la identidad | **error** | **Cada componente nuevo nacería con el nombre del harness** y su `AGENTS.md` heredaría el error |

Separarlos es deliberado: en A el árbol es sano y solo conviene avisar; en B hay un defecto que
propagará a todos los componentes futuros.

**Detección del caso B**: no hay forma directa de saber si un árbol es un componente instanciado. Se usa
una **señal indirecta**, declarada como tal en el código:

```
artefactos del harness presentes (AGENTS.md, harness.config.json, init.sh, .harness/harness.version)
  Y ausencia de .spec/_harness/
  => el árbol es un componente instanciado, no el harness
```

El razonamiento: el harness contiene sus propios ADR en `.spec/_harness/`; un componente instanciado no
los lleva (ADR-006 los excluye al limpiar la herencia).

### 3. La referencia colgante del `$schema`

Se registra como **advertencia**, no como error: no rompe nada hoy (ningún script lee `$schema`), pero
aparenta una validación que no existe. Las dos salidas —crear el esquema o quitar la línea— son una
decisión pendiente y no bloquean nada.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Solo cambiar el valor, sin check** | Cambio de una línea | Nada impediría que un componente instanciado conservara el nombre del harness, que es el fallo que importa | Es el caso B, el que propaga el error a todos |
| **B. Un check único, sin distinguir severidad** | Más simple | O avisa de un caso sano, o bloquea por un caso cosmético. Ninguna de las dos es correcta | Las dos situaciones tienen consecuencias muy distintas |
| **C. Derivar el nombre del directorio** (sin declararlo) | Sin campo que mantener | `harness.config.json` es un artefacto **generado** al instanciar: el generador necesita un valor que reescribir, no una derivación | Rompe ADR-006 (generado desde ley + parámetros) |
| **D. Dos controles por severidad + señal indirecta para el caso B** | Detecta el fallo que propaga; no molesta por el cosmético; la heurística queda declarada | La heurística del caso B puede dar un falso error si alguien renombra `.spec/_harness/` | — (la elegida) |

## Consecuencias

**Positivas**
- El instanciador (pendiente 3) lee ahora la identidad correcta: **se desbloquea su precondición**.
- El caso B se detecta **antes** de que un componente se cree con el nombre equivocado — el momento en
  que el error sería más caro de deshacer.
- La referencia colgante del `$schema` deja de ser invisible.

**Negativas / deuda asumida**
- La detección del caso B es **una heurística**, no una certeza: se apoya en la ausencia de
  `.spec/_harness/`. Si un componente instanciado creara ese directorio por cualquier motivo, el check
  dejaría de avisar. Queda declarado en el código.
- El `$schema` sigue sin existir. Es deuda registrada, con dos salidas posibles.
- Cambiar el nombre del repositorio exige ahora actualizar **dos** sitios (el directorio y
  `repository.name`), y un tercero si el nombre aparece en la documentación.

**Neutrales**
- Ningún script leía el campo antes de este cambio; se verificó con una búsqueda en `scripts/`, `*.sh`
  y `*.json`.
- No afecta a los roles, las skills ni los adaptadores.

## Cómo revertir esta decisión

Devolver `"name": "deepseek-harness"` y retirar el check. Se recupera el estado anterior: un harness que
se identifica con el nombre de otro repositorio.

## Cómo se verificó

1. **Búsqueda previa** de todos los usos de `repository.name`: `harness.config.json` era el único sitio.
2. `python scripts/validate_harness.py` → **136 comprobaciones, COHERENTE** (eran 132), con una
   advertencia por el `$schema` colgante.
3. **Dos pruebas negativas**, con el fixture revertido:
   - Nombre de otro repo en el harness → **aviso** (`¿Nombre heredado de otro repo?`), código de salida 0
   - Componente que conserva el nombre del harness (renombrando `.spec/_harness`) → **error**, código
     **1**: `el generador no reescribio la identidad, y su AGENTS.md heredaria el nombre equivocado`
4. Verificado que `.spec/` quedó intacto tras las pruebas: **17 ADR** y `.spec/validator-runner/`.

## Referencias

- ADR-006 (el `AGENTS.md` del repositorio instanciado se genera), ADR-012 (un nivel: el repositorio)
- ADR-015 y ADR-017 (verificar el efecto, no la intención)
- `docs/pendientes.md` (pendiente 11, precondición del 3)
- `docs/propuesta-harness-instanciable.md` §2 (el hallazgo original, sin corregir hasta hoy)
