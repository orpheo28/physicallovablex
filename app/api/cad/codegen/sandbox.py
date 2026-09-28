"""Safe execution of AI-written build123d programs (W19).

    check_code(code) -> list[str]                      # static AST policy; [] = allowed
    run_code(code, work_dir=None, timeout_s=25) -> dict  # {"ok", "error", "kind", "parts", "bbox_mm", "volume_mm3",
                                                          #  "files": {step, stl, glb}, "seconds", ...}

Layers (each one alone would stop the obvious attacks; together they are defence in depth):
1. AST whitelist: imports only `build123d` / `math`; no open/exec/eval/compile/__import__/getattr/setattr/globals/
   vars/…; no name or attribute starting with "_"; no build123d file I/O (export_*/import_*/Mesher/…), no
   str.format tricks. Must define `build()`.
2. Child process `python -I -B` (isolated: no PYTHON* env, no user site, no cwd on sys.path), clean environment
   (no secrets: only PATH/HOME/TMPDIR/LANG), cwd = a fresh temp dir, restricted builtins + import guard inside.
3. Resource limits: RLIMIT_AS (CODEGEN_MEM_MB, default 1280), RLIMIT_DATA (CODEGEN_DATA_MB, default 640),
   RLIMIT_CPU = timeout, RLIMIT_FSIZE 256 MB, no core dumps, single-threaded OpenBLAS; wall-clock timeout kills the
   whole process group.
4. macOS only, when /usr/bin/sandbox-exec exists: a Seatbelt profile denies network and writes outside the temp dir.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

RUNNER = Path(__file__).resolve().parent / "_runner.py"
ALLOWED_IMPORTS = {"build123d", "math"}
# C1: `from api.cad.stdparts import <name>, …` (standard parts + DFM helpers, pure build123d) — named imports of the
# listed helpers only; `import api…` / star imports / any other api module stay forbidden (the runner re-checks).
STDPARTS_MODULE = "api.cad.stdparts"
FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "delattr", "globals", "locals", "vars",
    "input", "breakpoint", "help", "exit", "quit", "memoryview", "type",
    "os", "sys", "subprocess", "socket", "pathlib", "importlib", "shutil", "builtins", "ctypes",
}
# build123d file I/O (we export for the program)
NAME_IO_RX = re.compile(r"^(export|import)_|^(Mesher|Export2D|ExportDXF|ExportSVG)$")
# attribute side: file I/O methods, str.format attribute walks, process/file-system calls
ATTR_IO_RX = re.compile(r"^(export|import|write|read|save|load|dump|to_file|from_file)|mesher|exporter|importer|"
                        r"^format(_map)?$|^(open|system|popen|spawn|fork|remove|unlink|rmdir|chdir|mkdir|environ|getenv|"
                        r"putenv|kill|modules|io|resource|signal|threading|tempfile|urllib|http|pickle|marshal|"
                        r"inspect|linecache|gc|runpy|pty|asyncio|codecs)$|^(exec|spawn|popen|system)",
                        re.IGNORECASE)
MAX_CODE_BYTES = 80_000


def check_code(code: str) -> list[str]:
    """Static policy check. Returns human-readable violations (fed back to the LLM), [] when the code is allowed."""
    if len(code.encode()) > MAX_CODE_BYTES:
        return [f"program too long ({len(code.encode())} bytes > {MAX_CODE_BYTES})"]
    try:
        tree = ast.parse(code, filename="model.py")
    except SyntaxError as e:
        return [f"SyntaxError: {e.msg} (line {e.lineno})"]
    errs: list[str] = []

    def bad(node: ast.AST, msg: str) -> None:
        errs.append(f"line {getattr(node, 'lineno', '?')}: {msg}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    bad(node, f"import {a.name!r} is not allowed (only build123d and math)")
        elif isinstance(node, ast.ImportFrom) and node.module == STDPARTS_MODULE and not node.level:
            from api.cad.stdparts import SANDBOX_NAMES

            for a in node.names:
                if a.name not in SANDBOX_NAMES:
                    bad(node, f"from api.cad.stdparts import {a.name!r} is not allowed (helpers: {', '.join(sorted(SANDBOX_NAMES))})")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                bad(node, f"from {node.module!r} import … is not allowed (only build123d and math)")
            for a in node.names:
                if a.name != "*" and (a.name.startswith("_") or NAME_IO_RX.search(a.name)):
                    bad(node, f"importing {a.name!r} is not allowed (file I/O / private)")
        elif isinstance(node, ast.Name):
            if node.id.startswith("__") or node.id in FORBIDDEN_NAMES:
                bad(node, f"name {node.id!r} is not allowed")
            elif NAME_IO_RX.search(node.id):
                bad(node, f"{node.id!r}: file I/O is not allowed — return the parts, we export them")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr in FORBIDDEN_NAMES:
                bad(node, f"attribute {node.attr!r} is not allowed (no private/dunder access)")
            elif ATTR_IO_RX.search(node.attr):
                bad(node, f"attribute {node.attr!r} is not allowed (file I/O / string formatting tricks)")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bad(node, "global/nonlocal is not allowed")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name.startswith("__"):
            bad(node, f"definition {node.name!r} is not allowed")
        elif isinstance(node, ast.AsyncFunctionDef | ast.Await | ast.AsyncFor | ast.AsyncWith):
            bad(node, "async code is not allowed")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "build" for n in tree.body):
        errs.append("the program must define a top-level function build() that returns the parts")
    return errs


def _limits(timeout_s: float):
    # W21, tuned in the Docker image under --memory=1g: OCP imports need ~1.1 GB of address space (900 MB segfaults
    # intermittently) but only ~400 MB of data segment once OpenBLAS is single-threaded; the data cap is what keeps a
    # runaway model from pushing the container over its memory limit (docs/DEPLOY.md).
    mem_mb = int(os.getenv("CODEGEN_MEM_MB", "1280"))
    data_mb = int(os.getenv("CODEGEN_DATA_MB", "640"))

    def apply() -> None:  # runs in the child between fork and exec
        import resource

        for lim, val in ((resource.RLIMIT_CPU, int(timeout_s) + 1), (resource.RLIMIT_FSIZE, 256 << 20),
                         (resource.RLIMIT_CORE, 0), (resource.RLIMIT_AS, mem_mb << 20),
                         (resource.RLIMIT_DATA, data_mb << 20)):
            try:
                resource.setrlimit(lim, (val, val))
            except (ValueError, OSError):
                pass  # macOS does not enforce RLIMIT_AS; the wall-clock timeout still applies
    return apply


def _seatbelt(work: Path) -> list[str]:
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").exists() or os.getenv("CODEGEN_NO_SEATBELT"):
        return []
    real = str(work.resolve())
    profile = ("(version 1)(allow default)(deny network*)"
               f'(deny file-write* (require-not (require-any (subpath "{real}") (literal "/dev/null"))))')
    return ["/usr/bin/sandbox-exec", "-p", profile]


def run_code(code: str, work_dir: Path | str | None = None, timeout_s: float = 25.0) -> dict[str, Any]:
    """Check + execute `code` in the sandbox. Never raises for bad code: returns {"ok": False, "kind", "error"}."""
    violations = check_code(code)
    if violations:
        return {"ok": False, "kind": "policy", "error": "Sandbox policy violation:\n" + "\n".join(violations[:12]),
                "violations": violations, "seconds": 0.0}
    own = work_dir is None
    work = Path(work_dir or tempfile.mkdtemp(prefix="cadgen_"))
    work.mkdir(parents=True, exist_ok=True)
    (work / "model.py").write_text(code, encoding="utf-8")
    env = {"PATH": "/usr/bin:/bin", "HOME": str(work), "TMPDIR": str(work), "LANG": "C.UTF-8",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MALLOC_ARENA_MAX": "2", "PYTHONHASHSEED": "0"}
    cmd = [*_seatbelt(work), sys.executable, "-I", "-B", str(RUNNER), "model.py", str(work)]
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, preexec_fn=_limits(timeout_s), start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        return {"ok": False, "kind": "timeout", "error": f"Timeout: the program ran longer than {timeout_s:.0f} s "
                "(infinite loop, or too many boolean operations / fillets)", "seconds": round(time.monotonic() - started, 2)}
    seconds = round(time.monotonic() - started, 2)
    res_path = work / "result.json"
    if not res_path.exists():
        tail = (stderr or b"").decode(errors="replace")[-1500:]
        kind = "crash"
        if proc.returncode in (-signal.SIGXCPU, -signal.SIGKILL) or "MemoryError" in tail:
            kind = "resource"
        return {"ok": False, "kind": kind, "error": f"The sandbox process died (exit {proc.returncode}): {tail}",
                "seconds": seconds}
    res = json.loads(res_path.read_text())
    res["seconds_total"] = seconds
    res["stdout"] = (stdout or b"").decode(errors="replace")[-2000:]
    if res.get("ok"):
        res["files"] = {k: work / f"model.{k}" for k in ("step", "stl", "glb")}
        missing = [k for k, f in res["files"].items() if not f.exists() or f.stat().st_size == 0]
        if missing:
            res.update(ok=False, kind="export", error=f"export produced no {', '.join(missing)} file")
    else:
        res["kind"] = "runtime"
        detail = res.get("user_traceback") or res.get("traceback") or ""
        res["error"] = f"{res.get('error')} (stage: {res.get('stage')})\n{detail}".strip()
    res["work_dir"] = work
    if own and not res.get("ok"):
        shutil.rmtree(work, ignore_errors=True)
    return res
