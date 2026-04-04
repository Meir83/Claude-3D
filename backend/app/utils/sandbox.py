"""
Static analysis of generated CadQuery scripts before execution.

The goal is to reject obviously dangerous code before it ever touches the
subprocess layer. This is defence-in-depth: the subprocess also runs with
restricted permissions and resource limits.
"""
import ast
import re
from pathlib import Path

# Modules that the generated script is allowed to import
ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "cadquery",
        "cq",
        "math",
        "numpy",
        "os.path",
        "pathlib",
        "typing",
        "dataclasses",
    }
)

# Any top-level names that are outright forbidden (checked by regex first,
# before AST parsing, so we catch obfuscated variants too)
FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"__import__",
        r"importlib",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\bcompile\s*\(",
        r"\bgetattr\s*\(",
        r"\bsetattr\s*\(",
        r"\bdelattr\s*\(",
        r"\bglobals\s*\(",
        r"\blocals\s*\(",
        r"\bvars\s*\(",
        r"\bopen\s*\(",          # file I/O — output is via cq.exporters only
        r"\bsubprocess",
        r"\bos\.system",
        r"\bos\.popen",
        r"\bos\.execv",
        r"\bos\.fork",
        r"\bshutil",
        r"\bsocket",
        r"\burllib",
        r"\brequests",
        r"\bhttpx",
        r"\bpickle",
        r"\bctypes",
        r"\bcffi",
        r"\\x[0-9a-f]{2}",      # hex escape sequences
        r"\\u[0-9a-f]{4}",      # unicode escapes used for obfuscation
        r"chr\s*\(",
        r"bytes\s*\(",
    ]
]


class SandboxViolation(ValueError):
    """Raised when a script fails static validation."""


def validate_script(script: str, max_bytes: int = 51200) -> None:
    """
    Validate a CadQuery script for safety.

    Raises SandboxViolation with a descriptive message if any check fails.
    """
    # 1. Size check
    if len(script.encode()) > max_bytes:
        raise SandboxViolation(
            f"Script exceeds maximum size ({len(script.encode())} > {max_bytes} bytes)"
        )

    # 2. Forbidden pattern check (fast regex scan before AST)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(script):
            raise SandboxViolation(
                f"Script contains forbidden pattern: {pattern.pattern!r}"
            )

    # 3. AST parse
    try:
        tree = ast.parse(script, mode="exec")
    except SyntaxError as exc:
        raise SandboxViolation(f"Script has syntax errors: {exc}") from exc

    # 4. Walk AST for import violations
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_import(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            _check_import(module)

    # 5. Ensure at least one cadquery import exists (basic sanity)
    has_cq = any(
        (isinstance(n, ast.Import) and any(a.name in ("cadquery", "cq") for a in n.names))
        or (isinstance(n, ast.ImportFrom) and (n.module or "").startswith("cadquery"))
        for n in ast.walk(tree)
    )
    if not has_cq:
        raise SandboxViolation("Script must import cadquery")


def _check_import(module_name: str) -> None:
    top_level = module_name.split(".")[0]
    if top_level not in ALLOWED_IMPORTS and module_name not in ALLOWED_IMPORTS:
        raise SandboxViolation(
            f"Import of '{module_name}' is not allowed. "
            f"Allowed modules: {sorted(ALLOWED_IMPORTS)}"
        )


def safe_job_path(base: Path, job_id: str) -> Path:
    """
    Return the job directory path, validating that job_id is a UUID4 and
    that the resolved path stays within base (path-traversal prevention).
    """
    import re as _re
    UUID4_RE = _re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    if not UUID4_RE.match(job_id):
        raise ValueError(f"Invalid job_id: {job_id!r}")
    job_path = (base / job_id).resolve()
    if not str(job_path).startswith(str(base.resolve())):
        raise ValueError("Path traversal detected")
    return job_path
