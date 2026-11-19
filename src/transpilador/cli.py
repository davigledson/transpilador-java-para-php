"""Interface de linha de comando do transpilador."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import ast
from .ast import annotate_source, ast_to_dict
from .codegen import PhpEmitter, php_name
from .erros import TranspileError
from .lexer import JavaLexer, collect_type_names
from .parser import JavaParser
from .semantico import SemanticAnalyzer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transpilar",
        description="Transpila um subconjunto de Java para PHP.",
    )
    parser.add_argument(
        "input",
        help="arquivo .java ou diretório com arquivos .java",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="build",
        help="diretório de saída (padrão: build)",
    )
    parser.add_argument(
        "--main",
        default=None,
        help="classe main no modo projeto (quando há mais de uma)",
    )
    parser.add_argument(
        "--dump-ast",
        action="store_true",
        help="imprime a AST em JSON e não gera PHP (apenas arquivo único)",
    )
    parser.add_argument(
        "--dump-php",
        action="store_true",
        help="imprime o PHP gerado no stdout (apenas arquivo único)",
    )
    return parser


def runtime_source() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime" / "php"


def copy_runtime(output_dir: Path) -> None:
    runtime_src = runtime_source()
    if runtime_src.is_dir():
        shutil.copytree(runtime_src, output_dir / "runtime", dirs_exist_ok=True)


def collect_types(source: str, filename: str) -> set[str]:
    try:
        return collect_type_names(source)
    except TranspileError as exc:
        if not exc.filename:
            exc.with_file(filename)
        raise


def parse_source(source: str, type_names: set[str], filename: str) -> ast.Program:
    lexer = JavaLexer(type_names)
    parser = JavaParser()
    try:
        program = parser.parse(source, lexer)
    except TranspileError as exc:
        if not exc.filename:
            exc.with_file(filename)
        raise
    annotate_source(program, filename)
    for cls in program.classes:
        cls.source_file = filename
    return program


def transpile_file(
    input_path: Path,
    output_dir: Path,
    dump_ast: bool = False,
    dump_php: bool = False,
) -> int:
    source = input_path.read_text(encoding="utf-8")
    program = parse_source(source, collect_types(source, str(input_path)), str(input_path))

    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)

    if dump_ast:
        print(json.dumps(ast_to_dict(program), indent=2, ensure_ascii=False))
        return 0

    emitter = PhpEmitter(analyzer.classes)
    php = emitter.emit(program)

    if dump_php:
        print(php)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    copy_runtime(output_dir)

    output_file = output_dir / (input_path.stem + ".php")
    output_file.write_text(php, encoding="utf-8")
    print(output_file)
    return 0


def choose_main(analyzer: SemanticAnalyzer, requested: str | None) -> str | None:
    mains = sorted(
        name for name, info in analyzer.classes.items() if info.has_main
    )

    if requested:
        if requested not in analyzer.classes:
            raise TranspileError(f"classe main '{requested}' não encontrada")
        if not analyzer.classes[requested].has_main:
            raise TranspileError(
                f"a classe '{requested}' não declara public static void main(String[] args)"
            )
        return requested

    if len(mains) > 1:
        raise TranspileError(
            "múltiplas classes com main: "
            + ", ".join(mains)
            + "; use --main NomeDaClasse"
        )
    return mains[0] if mains else None


def build_bootstrap(class_to_file: dict[str, str]) -> str:
    lines = [
        "<?php",
        "declare(strict_types=1);",
        "",
        "require_once __DIR__ . '/runtime/bootstrap.php';",
        "",
        "$classes = [",
    ]
    for name in sorted(class_to_file):
        relative = "/" + class_to_file[name]
        lines.append(f"    {name!r} => __DIR__ . {relative!r},")
    lines.extend(
        [
            "];",
            "",
            "spl_autoload_register(static function (string $class) use ($classes): void {",
            "    if (isset($classes[$class])) {",
            "        require_once $classes[$class];",
            "    }",
            "});",
            "",
        ]
    )
    return "\n".join(lines)


def transpile_project(
    input_dir: Path,
    output_dir: Path,
    main_name: str | None = None,
) -> int:
    java_files = sorted(input_dir.rglob("*.java"))
    if not java_files:
        raise TranspileError(f"nenhum arquivo .java encontrado em {input_dir}")

    sources: dict[Path, str] = {
        path: path.read_text(encoding="utf-8") for path in java_files
    }

    # O lexer precisa saber todos os nomes de tipos antes de parsear
    # qualquer arquivo, por causa de `Conta c` vindo de outro arquivo.
    type_names: set[str] = set()
    for path, source in sources.items():
        type_names |= collect_types(source, str(path))

    file_programs: dict[Path, ast.Program] = {}
    all_classes: list[ast.ClassDecl] = []
    for path, source in sources.items():
        program = parse_source(source, type_names, str(path))
        file_programs[path] = program
        all_classes.extend(program.classes)

    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast.Program(classes=all_classes))

    output_dir.mkdir(parents=True, exist_ok=True)
    copy_runtime(output_dir)

    emitter = PhpEmitter(analyzer.classes)
    class_to_file: dict[str, str] = {}
    generated: list[Path] = []

    for path, program in file_programs.items():
        relative = path.relative_to(input_dir).with_suffix(".php")
        output_file = output_dir / relative
        output_file.parent.mkdir(parents=True, exist_ok=True)

        parent_parts = relative.parent.parts
        depth = 0 if parent_parts == () else len(parent_parts)
        php = emitter.emit_module(program, bootstrap_depth=depth)
        output_file.write_text(php, encoding="utf-8")
        generated.append(output_file)

        relative_php = output_file.relative_to(output_dir).as_posix()
        for cls in program.classes:
            info = analyzer.classes[cls.name]
            class_to_file[php_name(info.qualified_name)] = relative_php

    bootstrap_file = output_dir / "bootstrap.php"
    bootstrap_file.write_text(build_bootstrap(class_to_file), encoding="utf-8")
    generated.append(bootstrap_file)

    main_class = choose_main(analyzer, main_name)
    if main_class is not None:
        main_fqn = php_name(analyzer.classes[main_class].qualified_name)
        run_file = output_dir / "run.php"
        run_file.write_text(
            "\n".join(
                [
                    "<?php",
                    "declare(strict_types=1);",
                    "",
                    "require_once __DIR__ . '/bootstrap.php';",
                    "",
                    f"\\{main_fqn}::main(array_slice($argv, 1));",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        generated.append(run_file)

    for path in generated:
        print(path)
    if main_class is None:
        print("aviso: nenhum main encontrado; apenas bootstrap.php foi gerado")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"erro: caminho não encontrado: {input_path}", file=sys.stderr)
        return 1

    try:
        if input_path.is_dir():
            if args.dump_ast or args.dump_php:
                print(
                    "erro: --dump-ast/--dump-php só funcionam com arquivo único",
                    file=sys.stderr,
                )
                return 1
            return transpile_project(input_path, Path(args.output), args.main)

        if args.main:
            print("erro: --main só é válido no modo projeto", file=sys.stderr)
            return 1

        return transpile_file(
            input_path,
            Path(args.output),
            dump_ast=args.dump_ast,
            dump_php=args.dump_php,
        )
    except TranspileError as exc:
        if not exc.filename:
            exc.with_file(str(input_path))
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
