---
name: security-review
description: "Checklist de revisión de seguridad para el diff de una tarea: secretos, inyección, autorización, criptografía, dependencias y fuga de datos. Use when reviewing changes for security, auditing a diff, checking for leaked credentials, or validating auth logic."
argument-hint: "<rango de commits>"
---

# Security Review

Checklist orientada al **diff concreto**, no a una auditoría del repositorio completo.
Usada por el rol `sdd-security-reviewer` y por el check `secrets` de `init.sh`.

## Cuándo usar

Solo si el diff toca alguna de estas superficies:

- Entrada de usuario · autenticación/autorización · red · deserialización ·
  ejecución de comandos/plantillas/SQL · dependencias nuevas · secretos/PII.

Si no hay ninguna, responde `N/A`. **No inventes hallazgos** para justificar la revisión.

## 1. Secretos y credenciales (R9)

```bash
# Escaneo del árbol completo
gitleaks detect --no-banner --redact

# Solo el diff de la tarea
git diff <base>..<head> -U0 | grep -nE '(api[_-]?key|secret|token|password|passwd|private[_-]?key)\s*[:=]'
```

Comprueba además:

- [ ] Credenciales **hardcodeadas** (aunque sean "de prueba"). Siempre por variable de entorno.
- [ ] Credenciales en **URLs** (`https://user:pass@host`) — acaban en logs.
- [ ] Credenciales en **logs o mensajes de error**.
- [ ] `.env` versionado, o `.env` **añadido** a `.gitignore` que ya no se ignora.
- [ ] Claves en `verify.md`, en artefactos `.spec/` o en mensajes de commit.
- [ ] **En el informe**: reporta `archivo:línea` y el tipo, **nunca el valor**.

## 2. Inyección

- [ ] **SQL**: ninguna consulta construida por concatenación o f-string/plantilla con entrada
      del usuario. Solo consultas parametrizadas.
- [ ] **Comandos**: nada de `shell=True` / `child_process.exec` / `os.system` con entrada de
      usuario. Usar APIs sin shell (`execFile`, `shlex.quote`, `subprocess.run([...])`).
- [ ] **Plantillas/HTML**: escape por defecto (autoescape activo). Sin `innerHTML`,
      `dangerouslySetInnerHTML`, `| safe`, `mark_safe` con datos de usuario.
- [ ] **Path traversal**: rutas construidas con entrada de usuario validadas contra `..`
      y contra un directorio base permitido.
- [ ] **Deserialización**: nada de `pickle.loads`, `yaml.load` sin `SafeLoader`, `eval`,
      `Function()`, o JSON con clases arbitrarias sobre datos no confiables.
- [ ] **SSRF**: URLs construidas por el usuario con allowlist de destinos.
- [ ] **ReDoS**: regex con backtracking exponencial sobre entrada del usuario.

## 3. Autenticación y autorización

- [ ] Contraseñas comparadas con comparación de tiempo constante (`hmac.compare_digest`,
      `crypto.timingSafeEqual`), nunca `==`.
- [ ] Contraseñas hasheadas con algoritmo moderno (bcrypt/argon2/scrypt), nunca MD5/SHA1/SHA256 simple.
- [ ] **Todos** los endpoints nuevos tienen comprobación de autorización, no solo autenticación.
- [ ] La autorización se comprueba por **recurso** (IDOR), no solo por rol global.
- [ ] Tokens/sesiones con expiración; invalidación en logout implementada.
- [ ] Errores de login **no** revelan si el usuario existe (mensaje genérico).
- [ ] Rate limiting presente en login, registro y endpoints de recuperación.

## 4. Criptografía

- [ ] Sin algoritmos obsoletos (MD5, SHA1, DES, RC4, ECB).
- [ ] IVs/nonces **únicos** por operación y generados con CSPRNG.
- [ ] Sin claves derivadas de constantes, del nombre de usuario, o de la fecha.
- [ ] Sin `verify=False` / `rejectUnauthorized: false` / `--insecure`.

## 5. Dependencias

- [ ] Cada dependencia nueva está **justificada en `design.md`** (§2.6 de la ley).
- [ ] Sin versiones flotantes sin lockfile (`^0.x`, `latest`, `*`).
- [ ] Sin paquetes **typosquatting** (nombre sospechosamente parecido a uno popular).
- [ ] Sin paquetes abandonados (> 2 años sin release) para funciones de seguridad.
- [ ] Si se puede consultar: sin CVEs críticos conocidos para las versiones introducidas.

## 6. Fuga de datos

- [ ] Sin PII en logs, mensajes de error, trazas o métricas.
- [ ] Respuestas de API **sin** campos de más (nunca devolver el objeto de BD completo).
- [ ] Mensajes de error al cliente **sin** stack traces ni rutas internas.
- [ ] Datos sensibles **no** incluidos en `verify.md` ni en artefactos de `.spec/`.

## 7. Logging y observabilidad

- [ ] Sin datos de usuario o credenciales en logs (R9).
- [ ] Nivel de log adecuado (sin `INFO` con payloads completos).
- [ ] Los fallos de seguridad sí se registran (intentos fallidos, autorización denegada).

## Formato de hallazgo

```
[SEVERIDAD: crítica|alta|media|baja] <título>
Ubicación: <archivo>:<línea>
Vector: <cómo se explota, una frase>
Impacto: <qué consigue el atacante>
Remediación: <cambio concreto>
```

**Severidad**:

| Nivel | Criterio |
| :--- | :--- |
| **crítica** | Ejecución de código, bypass de autenticación, secreto expuesto en claro → fuerza `FAIL` |
| **alta** | Escalada de privilegios, inyección explotable, fuga de PII → fuerza `FAIL` |
| **media** | Requiere condiciones difíciles o impacto limitado → `PASS-CON-NOTAS` |
| **baja** | Endurecimiento, buena práctica sin vector real → `PASS-CON-NOTAS` |

## Ver también

- Rol [sdd-security-reviewer](../../agents/sdd-security-reviewer.md)
- Skill `verify-report` (sección 8)
- `AGENTS.md` §1 R9
