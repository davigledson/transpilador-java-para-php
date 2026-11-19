from transpilador import ast
from transpilador.codegen import PhpEmitter
from transpilador.lexer import JavaLexer, collect_type_names
from transpilador.parser import JavaParser
from transpilador.semantico import SemanticAnalyzer


def generate(source: str) -> str:
    lexer = JavaLexer(collect_type_names(source))
    program = JavaParser().parse(source, lexer)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    return PhpEmitter(analyzer.classes).emit(program)


def test_hello_program() -> None:
    php = generate(
        """
        public class Hello {
            public static void main(String[] args) {
                System.out.println("oi");
            }
        }
        """
    )
    assert "class Hello" in php
    assert "JSystem::println" in php
    assert "Hello::main(array_slice($argv, 1));" in php
    assert php.startswith("<?php")


def test_intdiv_and_string_concat() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                int x = 7 / 2;
                System.out.println("x=" + x);
            }
        }
        """
    )
    assert "intdiv(7, 2)" in php
    assert "JString::concat" in php


def test_array_default_and_length() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                int[] a = new int[3];
                System.out.println(a.length);
            }
        }
        """
    )
    assert "array_fill(0, 3, 0)" in php
    assert "count($a)" in php


def test_nullable_reference_types() -> None:
    php = generate(
        """
        class A {
            private String nome;
            private B b;
        }
        class B { }
        """
    )
    assert "private ?string $nome = null;" in php
    assert "private ?B $b = null;" in php


def test_builtin_static_calls() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                String s = String.valueOf(42);
                int n = Integer.parseInt("7");
                double d = Math.sqrt(81.0);
                int r = Math.round(3.6);
                System.out.println(s + n + d);
            }
        }
        """
    )
    assert "JString::valueOf(42)" in php
    assert "(int) (\"7\")" in php
    assert "sqrt(81.0)" in php
    assert "(int) round(3.6)" in php
