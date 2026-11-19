#!/usr/bin/env python3
"""Teste de integração do modo projeto (vários .java → bootstrap/run.php)."""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "tests" / "project" / "src"
WORK = ROOT / "build" / "project"
MAIN = "Main"


def run(
    cmd: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {}
    if input_text is None:
        kwargs["stdin"] = subprocess.DEVNULL
    else:
        kwargs["input"] = input_text
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        env=env,
        **kwargs,
    )


def fail(message: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    print(f"  {message}")
    if result is not None:
        if result.stdout.strip():
            print("  stdout:")
            print("\n".join("    " + line for line in result.stdout.splitlines()))
        if result.stderr.strip():
            print("  stderr:")
            print("\n".join("    " + line for line in result.stderr.splitlines()))


def main() -> int:
    if not PROJECT.is_dir():
        print(f"projeto não encontrado: {PROJECT}")
        return 1

    shutil.rmtree(WORK, ignore_errors=True)
    java_dir = WORK / "java"
    php_dir = WORK / "php"
    java_dir.mkdir(parents=True)

    java_files = sorted(str(path) for path in PROJECT.rglob("*.java"))
    compiled = run(["javac", "--release", "21", "-d", str(java_dir), *java_files])
    if compiled.returncode != 0:
        fail("falha ao compilar o projeto com javac", compiled)
        return 1

    java_run = run(["java", "-cp", str(java_dir), "app.Main"])
    if java_run.returncode != 0:
        fail("falha ao executar o projeto em Java", java_run)
        return 1

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    transpiled = run(
        [
            sys.executable,
            "-m",
            "transpilador",
            str(PROJECT),
            "-o",
            str(php_dir),
            "--main",
            MAIN,
        ],
        env=env,
    )
    if transpiled.returncode != 0:
        fail("falha ao transpilar o projeto", transpiled)
        return 1

    run_file = php_dir / "run.php"
    if not run_file.is_file():
        fail(f"run.php não foi gerado em {php_dir}")
        return 1

    for php_file in sorted(php_dir.rglob("*.php")):
        lint = run(["php", "-l", str(php_file)])
        if lint.returncode != 0:
            fail(f"php -l falhou em {php_file}", lint)
            return 1

    php_run = run(
        [
            "php",
            "-d",
            "error_reporting=E_ALL",
            "-d",
            "display_errors=1",
            str(run_file),
        ]
    )
    if php_run.returncode != 0:
        fail("falha ao executar o run.php gerado", php_run)
        return 1
    if php_run.stderr.strip():
        fail("o projeto PHP gerou warnings/erros", php_run)
        return 1

    if java_run.stdout != php_run.stdout:
        diff = "\n".join(
            difflib.unified_diff(
                java_run.stdout.splitlines(),
                php_run.stdout.splitlines(),
                fromfile="Java",
                tofile="PHP",
                lineterm="",
            )
        )
        fail("saídas diferentes")
        print("\n".join("    " + line for line in diff.splitlines()))
        return 1

    print("[projeto] OK")
    print(f"  saída: {java_run.stdout.strip()}")
    print(f"  php: {php_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
