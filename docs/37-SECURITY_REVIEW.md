# 37. Security Review

## Permission Boundaries

| Level | Name | Auto-granted? | Examples |
|-------|------|---------------|----------|
| 0 | READ | ✅ Yes | file.read, file.list, file.search, system.info |
| 1 | SAFE | ✅ Yes | General safe operations |
| 2 | WORKSPACE | ⚠️ Session-based | file.write, workspace operations |
| 3 | SENSITIVE | ❌ No | command.execute |

**Assessment:** Permission levels are well-defined. Auto-granting for READ and SAFE is appropriate. Session-based approval for WORKSPACE is reasonable. SENSITIVE always requires explicit approval.

## Tool Authorization

All tool execution goes through `PermissionManager.check_permission()`. Tools declare their required permission level in their `ToolContract`. No tool can execute without permission check.

**Assessment:** ✅ Secure.

## API Validation

FastAPI provides automatic request validation through Pydantic models. All API endpoints use type-annotated parameters.

**Assessment:** ✅ Secure.

## Input Sanitization

- File paths are not sanitized in `_read_file`, `_write_file`, `_list_directory`, `_search_files`. Path traversal is possible.
- Command execution passes user input directly to `create_subprocess_shell`.

**Assessment:** ⚠️ Path traversal and command injection are possible. These tools require SENSITIVE permission level, which mitigates the risk, but input sanitization should be added.

## Plugin Isolation

PluginSandbox uses subprocess execution with timeout. No memory limits, no filesystem restrictions, no network restrictions.

**Assessment:** ⚠️ Plugin isolation is minimal. Should be enhanced with proper sandboxing (container, restricted user, or at minimum resource limits).

## Secure Defaults

- API binds to 127.0.0.1 (localhost only) — ✅ Secure
- Permission default level is 1 (SAFE) — ✅ Secure
- No API keys stored in code — ✅ Secure
- CORS is permissive (allow all origins) — ⚠️ Should be restricted in production

## Secrets Management

- AI API keys are stored in environment variables or .env file
- No secrets in code
- No secrets in database

**Assessment:** ✅ Secure.

## Privilege Escalation

**Risk:** Low
**Analysis:** All tool execution goes through PermissionManager. Tools declare their required permission level. The permission system is the gatekeeper. No path exists to bypass it.

## Recommendations

1. Add input validation to file tools (path traversal prevention)
2. Restrict CORS in production
3. Add plugin sandbox resource limits (memory, CPU, filesystem)
4. Add rate limiting to API endpoints (currently configured in settings but not enforced)
