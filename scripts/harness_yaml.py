"""Parser YAML mínimo, sin dependencias externas.

Existe para que el harness funcione en entornos donde PyYAML no está disponible
(CI restringida, imágenes mínimas, air-gapped). Cubre el subconjunto de YAML que
usan los archivos de `.harness/`: mapas anidados por indentación, listas de
escalares y escalares simples (comillas opcionales).

Si PyYAML está instalado, se usa como preferencia por robustez.
"""

from __future__ import annotations

import re
from typing import Any

try:  # pragma: no cover - depende del entorno
    import yaml as _pyyaml  # type: ignore
except ImportError:  # pragma: no cover
    _pyyaml = None

_BOOL_TRUE = {"true", "yes", "on", "sí", "si"}
_BOOL_FALSE = {"false", "no", "off"}


def _strip_inline_comment(value: str) -> str:
    r"""Elimina un comentario de final de línea, respetando comillas.

    Implementado con un recorrido lineal en lugar de una regex con backtracking
    (`\s+#` es superlineal en cadenas largas de espacios).
    """
    in_single = False
    in_double = False
    index = 0
    length = len(value)
    while index < length:
        char = value[index]
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index > 0 and value[index - 1].isspace():
                return value[:index].rstrip()
        index += 1
    return value


def _coerce(raw: str) -> Any:
    """Convierte un escalar de texto al tipo Python obvio."""
    value = raw.strip()

    # Quitar comentario de final de línea (fuera de comillas).
    if value and value[0] not in "\"'":
        value = _strip_inline_comment(value)

    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]

    lowered = value.lower()
    if lowered in _BOOL_TRUE:
        return True
    if lowered in _BOOL_FALSE:
        return False
    if lowered in {"null", "none", "~", ""}:
        return None

    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_coerce(part) for part in inner.split(",")]

    return value


def _preprocess(text: str) -> list[tuple[int, str]]:
    """Devuelve (indentación, contenido) por línea, sin comentarios ni vacías."""
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        stripped = raw.lstrip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("---"):
            continue
        indent = len(raw) - len(stripped)
        lines.append((indent, stripped.rstrip()))
    return lines


def _parse_inline_map(content: str) -> dict[str, Any]:
    """Parsea un elemento de lista que es un mapa en línea (`- clave: valor`)."""
    key, _, rest = content.partition(":")
    return {key.strip(): _coerce(rest)}


def _consume_sub_keys(
    lines: list[tuple[int, str]], start: int, parent_indent: int, mapping: dict[str, Any]
) -> int:
    """Absorbe las claves de continuación de un mapa en línea y devuelve el índice."""
    index = start
    while index < len(lines) and lines[index][0] > parent_indent:
        content = lines[index][1]
        sub_key, sep, sub_rest = content.partition(":")
        if sep:
            mapping.setdefault(sub_key.strip(), _coerce(sub_rest))
        index += 1
    return index


def _parse_list(items: list[Any], lines: list[tuple[int, str]], start: int, indent: int) -> tuple[list[Any], int]:
    """Parsea un bloque de lista de la misma indentación."""
    index = start
    while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
        content = lines[index][1][2:].strip()
        if ":" in content and not content.startswith(("\"", "'")):
            mapping = _parse_inline_map(content)
            index = _consume_sub_keys(lines, index + 1, indent, mapping)
            items.append(mapping)
        else:
            items.append(_coerce(content))
            index += 1
    return items, index


def _parse_map(mapping: dict[str, Any], lines: list[tuple[int, str]], start: int, indent: int) -> tuple[dict[str, Any], int]:
    """Parsea un bloque de mapa de la misma indentación."""
    index = start
    while index < len(lines) and lines[index][0] == indent:
        line_indent, content = lines[index]
        if content.startswith("- "):
            break
        key, sep, rest = content.partition(":")
        if not sep:
            index += 1
            continue

        key = key.strip()
        rest = rest.strip()
        if rest:
            mapping[key] = _coerce(rest)
            index += 1
        elif index + 1 < len(lines) and lines[index + 1][0] > line_indent:
            child, index = _parse_block(lines, index + 1, lines[index + 1][0])
            mapping[key] = child
        else:
            mapping[key] = None
            index += 1
    return mapping, index


def _parse_block(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[Any, int]:
    """Parsea recursivamente un bloque (mapa o lista) de la misma indentación."""
    if start < len(lines) and lines[start][1].startswith("- "):
        return _parse_list([], lines, start, indent)
    return _parse_map({}, lines, start, indent)


def load(path: str) -> dict[str, Any]:
    """Carga un archivo YAML y devuelve un dict. Lanza ValueError si no es un mapa."""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    if _pyyaml is not None:  # pragma: no cover
        data = _pyyaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: se esperaba un mapa en la raíz, no {type(data).__name__}")
        return data

    lines = _preprocess(text)
    if not lines:
        return {}
    data, _ = _parse_block(lines, 0, lines[0][0])
    if not isinstance(data, dict):
        raise ValueError(f"{path}: se esperaba un mapa en la raíz")
    return data


def backend() -> str:
    """Indica qué implementación se está usando (útil en diagnósticos)."""
    return "PyYAML" if _pyyaml is not None else "parser interno (sin dependencias)"
