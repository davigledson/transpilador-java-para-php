"""Interface de linha de comando do transpilador."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .ast import ast_to_dict
from .codegen import PhpEmitter
from .erros import TranspileError
from .lexer import JavaLexer, collect_type_names
from .parser import JavaParser
from .semantico import SemanticAnalyzer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transpilar",
        description="Transpila um subconjunto de Java para PHP.",
    )
    parser.add_argument("input", help="arquivo .java de entrada")
    parser.add_argument(
        "-o",
        "--output",
        default="build",
        help="diretório de saída (padrão: build)",
    )
    parser.add_argument(
        "--dump-ast",
        action="store_true",
        help="imprime a AST em JSON e não gera PHP",
    )
    parser.add_argument(
        "--dump-php",
        action="store_true",
        help="imprime o PHP gerado no stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    input_path = Path(args.input)

    try:
        source = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"erro: não foi possível ler {input_path}: {exc}", file=sys.stderr)
        return 1

    try:
        lexer = JavaLexer(collect_type_names(source))
        parser = JavaParser()
        program = parser.parse(source, lexer)

        analyzer = SemanticAnalyzer()
        analyzer.analyze(program)

        if args.dump_ast:
            print(json.dumps(ast_to_dict(program), indent=2, ensure_ascii=False))
            return 0

        emitter = PhpEmitter(analyzer.classes)
        php = emitter.emit(program)

        if args.dump_php:
            print(php)
            return 0

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        runtime_src = Path(__file__).resolve().parents[2] / "runtime" / "php"
        runtime_dst = output_dir / "runtime"
        if runtime_src.is_dir():
            shutil.copytree(runtime_src, runtime_dst, dirs_exist_ok=True)

        output_file = output_dir / (input_path.stem + ".php")
        output_file.write_text(php, encoding="utf-8")
        print(output_file)
        return 0
    except TranspileError as exc:
        exc.with_file(str(input_path))
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
