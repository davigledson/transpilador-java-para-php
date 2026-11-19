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


def test_inheritance_codegen() -> None:
    php = generate(
        """
        class A {
            A() { }
            String f() { return "a"; }
        }
        class B extends A {
            B() { super(); }
            String f() { return super.f(); }
        }
        """
    )
    assert "class B extends A" in php
    assert "parent::__construct();" in php
    assert "parent::f()" in php


def test_implicit_super_constructor() -> None:
    php = generate(
        """
        class A { A() { } }
        class B extends A { B() { } }
        """
    )
    assert "parent::__construct();" in php


def test_explicit_super_without_parent_constructor_is_skipped() -> None:
    php = generate(
        """
        class A { }
        class B extends A { B() { super(); } }
        """
    )
    assert "parent::__construct()" not in php


def test_interface_and_abstract_class_codegen() -> None:
    php = generate(
        """
        interface I { int f(); }
        abstract class A implements I {
            abstract int g();
        }
        class B extends A implements I {
            public int f() { return 1; }
            public int g() { return 2; }
        }
        """
    )
    assert "interface I" in php
    assert "public function f(): int;" in php
    assert "abstract class A implements I" in php
    assert "abstract public function g(): int;" in php
    assert "class B extends A implements I" in php


def test_arraylist_and_scanner_codegen() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                ArrayList<String> nomes = new ArrayList<>();
                nomes.add("Ana");
                Scanner sc = new Scanner(System.in);
                int n = sc.nextInt();
                System.out.println(nomes.get(0) + n);
            }
        }
        """
    )
    assert "new JArrayList()" in php
    assert "->add(\"Ana\")" in php
    assert "new JScanner()" in php
    assert "->nextInt()" in php


def test_static_class_call() -> None:
    php = generate(
        """
        class Util {
            static int soma(int a, int b) { return a + b; }
        }
        class A {
            public static void main(String[] args) {
                System.out.println(Util.soma(1, 2));
            }
        }
        """
    )
    assert "Util::soma(1, 2)" in php


def test_hashmap_and_hashset_codegen() -> None:
    php = generate(
        """
        class Conta { }
        class A {
            public static void main(String[] args) {
                Map<String, Conta> mapa = new HashMap<>();
                mapa.put("Ana", new Conta());
                Conta c = mapa.get("Ana");
                Set<String> nomes = new HashSet<>();
                nomes.add("Ana");
                System.out.println(nomes.size());
            }
        }
        """
    )
    assert "new JHashMap()" in php
    assert "->put(\"Ana\", new Conta())" in php
    assert "new JHashSet()" in php
    assert "->add(\"Ana\")" in php
    assert "->size()" in php


def test_exceptions_codegen() -> None:
    php = generate(
        """
        class MinhaExcecao extends RuntimeException {
            MinhaExcecao(String mensagem) { super(mensagem); }
        }
        class A {
            public static void main(String[] args) {
                try {
                    throw new MinhaExcecao("x");
                } catch (MinhaExcecao e) {
                    System.out.println(e.getMessage());
                } finally {
                    System.out.println("fim");
                }
            }
        }
        """
    )
    assert "class MinhaExcecao extends \\RuntimeException" in php
    assert "parent::__construct($mensagem)" in php
    assert "try {" in php
    assert "catch (\\MinhaExcecao $e)" in php
    assert "throw new MinhaExcecao(\"x\")" in php
    assert "->getMessage()" in php
    assert "} finally {" in php
