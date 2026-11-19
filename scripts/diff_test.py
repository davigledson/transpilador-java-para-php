#!/usr/bin/env python3
"""Teste diferencial: executa o mesmo programa em Java e no PHP gerado.

Para cada arquivo .java:
  1. compila e executa com javac/java;
  2. transpila para PHP;
  3. valida com php -l;
  4. executa o PHP e compara a saída com a do Java.

Uso:
    python scripts/diff_test.py
    python scripts/diff_test.py examples/Banco.java
"""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(
    cmd: list[str],
    *,
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
        cwd=ROOT,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="arquivos .java (padrão: examples + corpus)")
    parser.add_argument("--keep", action="store_true", help="mantém os artefatos em build/diff")
    args = parser.parse_args(argv)

    if args.paths:
        files = [Path(p) for p in args.paths]
    else:
        files = sorted((ROOT / "examples").glob("*.java"))
        files += sorted((ROOT / "tests" / "corpus" / "java").glob("*.java"))
        # evita rodar o mesmo exemplo duas vezes (examples + corpus)
        seen: set[str] = set()
        unique: list[Path] = []
        for path in files:
            key = path.stem
            if key not in seen:
                seen.add(key)
                unique.append(path)
        files = unique

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

    failures = 0
    for path in files:
        path = path if path.is_absolute() else (ROOT / path)
        name = path.stem
        work = ROOT / "build" / "diff" / name

        print(f"[{name}]")
        if not path.exists():
            fail(f"arquivo não encontrado: {path}")
            failures += 1
            continue

        shutil.rmtree(work, ignore_errors=True)
        (work / "java").mkdir(parents=True)
        (work / "php").mkdir(parents=True)

        compiled = run(["javac", "-d", str(work / "java"), str(path)])
        if compiled.returncode != 0:
            fail("falha ao compilar com javac", compiled)
            failures += 1
            continue

        stdin_path = path.with_suffix(".in")
        stdin_text = stdin_path.read_text(encoding="utf-8") if stdin_path.exists() else None

        java_run = run(["java", "-cp", str(work / "java"), name], input_text=stdin_text)
        if java_run.returncode != 0:
            fail("falha ao executar o Java", java_run)
            failures += 1
            continue

        transpiled = run(
            [sys.executable, "-m", "transpilador", str(path), "-o", str(work / "php")],
            env=env,
        )
        if transpiled.returncode != 0:
            fail("falha ao transpilar", transpiled)
            failures += 1
            continue

        php_file = work / "php" / f"{name}.php"
        lint = run(["php", "-l", str(php_file)])
        if lint.returncode != 0:
            fail("PHP gerado não passou no php -l", lint)
            failures += 1
            continue

        php_run = run(
            [
                "php",
                "-d",
                "error_reporting=E_ALL",
                "-d",
                "display_errors=1",
                str(php_file),
            ],
            input_text=stdin_text,
        )
        if php_run.returncode != 0:
            fail("falha ao executar o PHP", php_run)
            failures += 1
            continue
        if php_run.stderr.strip():
            fail("o PHP gerou warnings/erros no stderr", php_run)
            failures += 1
            continue

        if java_run.stdout != php_run.stdout:
            diff = "\n".join(
                difflib.unified_diff(
                    java_run.stdout.splitlines(),
                    php_run.stdout.splitlines(),
                    fromfile=f"{name}.java",
                    tofile=f"{name}.php",
                    lineterm="",
                )
            )
            fail("saídas diferentes")
            print("\n".join("    " + line for line in diff.splitlines()))
            failures += 1
            continue

        print("  OK")

    if not args.keep:
        for path in files:
            work = ROOT / "build" / "diff" / path.stem
            shutil.rmtree(work, ignore_errors=True)

    total = len(files)
    print()
    print(f"{total - failures}/{total} caso(s) OK")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
