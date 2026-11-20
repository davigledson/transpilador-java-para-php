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
    assert "catch (MinhaExcecao $e)" in php
    assert "throw new MinhaExcecao(\"x\")" in php
    assert "->getMessage()" in php
    assert "} finally {" in php


def test_switch_codegen() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                int x = 1;
                switch (x) {
                    case 1:
                        System.out.println("um");
                        break;
                    default:
                        System.out.println("outro");
                }
            }
        }
        """
    )
    assert "switch (true)" in php
    assert "case ($__switch0 === 1):" in php
    assert "default:" in php
    assert "break;" in php


def test_enum_codegen() -> None:
    php = generate(
        """
        enum Status { ATIVO, BLOQUEADO }
        class A {
            public static void main(String[] args) {
                Status s = Status.ATIVO;
                switch (s) {
                    case ATIVO:
                        break;
                    default:
                        break;
                }
            }
        }
        """
    )
    assert "enum Status" in php
    assert "case ATIVO;" in php
    assert "case BLOQUEADO;" in php
    assert "Status::ATIVO" in php
    assert "case ($__switch0 === Status::ATIVO):" in php


def test_lambda_and_stream_codegen() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                List<String> nomes = new ArrayList<>();
                nomes.forEach(n -> System.out.println(n));
                List<String> maiusculos = nomes.stream()
                    .map(n -> n.toUpperCase())
                    .collect(Collectors.toList());
            }
        }
        """
    )
    assert "fn($n) => JSystem::println($n)" in php
    assert "->forEach(" in php
    assert "->stream()" in php
    assert "->map(fn($n) => strtoupper($n))" in php
    assert "->toList()" in php


def test_text_block_codegen() -> None:
    php = generate(
        '''
        class A {
            private String s = """
                a
                b
                """;
        }
        '''
    )
    assert 'private ?string $s = "a\\nb\\n";' in php


def test_cast_and_instanceof_codegen() -> None:
    php = generate(
        """
        class A {
            void m(A o) {
                int x = (int) 3.9;
                double d = (double) 3;
                char c = (char) 65;
                int codigo = (int) 'a';
                boolean b = o instanceof A;
                A a = (A) o;
            }
        }
        """
    )
    assert "((int) (3.9))" in php
    assert "((float) (3))" in php
    assert "chr((int) (65))" in php
    assert "ord(\"a\")" in php
    assert "($o instanceof A)" in php
    assert "JCast::to($o, A::class)" in php


def test_annotation_codegen() -> None:
    php = generate(
        """
        @interface MinhaAnotacao {
            String valor() default "";
            int prioridade() default 0;
        }

        @MinhaAnotacao(valor = "x")
        class Main {
            @MinhaAnotacao
            public static void main(String[] args) {
                System.out.println("ok");
            }
        }
        """
    )
    assert "interface MinhaAnotacao" in php
    assert "valor" not in php
    assert "prioridade" not in php
    assert "@MinhaAnotacao" not in php


def test_sealed_codegen() -> None:
    php = generate(
        """
        sealed interface Forma permits Circulo, Quadrado {
            double area();
        }
        final class Circulo implements Forma {
            public double area() { return 1.0; }
        }
        non-sealed class Quadrado implements Forma {
            public double area() { return 2.0; }
        }
        class Main {
            public static void main(String[] args) { }
        }
        """
    )
    assert "interface Forma" in php
    assert "class Circulo implements Forma" in php
    assert "class Quadrado implements Forma" in php
    assert "sealed" not in php
    assert "permits" not in php
    assert "non-sealed" not in php


def test_record_codegen() -> None:
    php = generate(
        """
        record Ponto(int x, int y) {
            public static final int VERSAO = 1;
            public int soma() { return x + y; }
        }
        class Main {
            public static void main(String[] args) {
                Ponto p = new Ponto(1, 2);
                System.out.println(p.x());
                System.out.println(Ponto.VERSAO);
            }
        }
        """
    )
    assert "final class Ponto" in php
    assert "public readonly int $x;" in php
    assert "public readonly int $y;" in php
    assert "public function __construct(int $x, int $y)" in php
    assert "$this->x = $x;" in php
    assert "public function x(): int" in php
    assert "return $this->x;" in php
    assert "public static int $VERSAO = 1;" in php


def test_record_explicit_constructor_is_not_duplicated() -> None:
    php = generate(
        """
        record Produto(String nome) {
            public Produto(String nome) {
                this.nome = nome;
            }
        }
        class Main {
            public static void main(String[] args) {
                Produto p = new Produto("caneta");
                System.out.println(p.nome());
            }
        }
        """
    )
    assert php.count("function __construct") == 1
    assert "final class Produto" in php


def test_try_with_resources_and_multi_catch_codegen() -> None:
    php = generate(
        """
        class Recurso implements AutoCloseable {
            public void close() { }
        }
        class A {
            void m() {
                try (Recurso r = new Recurso(); Recurso s = new Recurso()) {
                    System.out.println(r);
                } catch (RuntimeException | Error e) {
                    System.out.println(e.getMessage());
                }
            }
        }
        """
    )
    assert "catch (\\RuntimeException | \\Error $e)" in php
    assert "$r = new Recurso();" in php
    assert "$s = new Recurso();" in php
    assert "if ($r !== null)" in php
    assert "if ($s !== null)" in php
    assert php.index("$s->close();") < php.index("$r->close();")
    assert php.index("$r->close();") < php.index("catch (")


def test_try_with_resources_without_handlers_codegen() -> None:
    php = generate(
        """
        class Recurso implements AutoCloseable {
            public void close() { }
        }
        class A {
            void m() {
                try (Recurso r = new Recurso()) {
                    System.out.println(r);
                }
            }
        }
        """
    )
    assert "$r = new Recurso();" in php
    assert "} finally {" in php
    assert "$r->close();" in php


def test_pattern_instanceof_codegen() -> None:
    php = generate(
        """
        class A {
            void m(A o) {
                if (o instanceof A a) {
                    System.out.println(a);
                }
                if (o instanceof A b && b != null) {
                    System.out.println(b);
                }
            }
        }
        """
    )
    assert "(($a = $o) instanceof A)" in php
    assert "(($b = $o) instanceof A)" in php


def test_class_literal_codegen() -> None:
    php = generate(
        """
        class Conta { }
        class A {
            public static void main(String[] args) {
                System.out.println(Conta.class.getSimpleName());
                System.out.println(int.class);
            }
        }
        """
    )
    assert "JClass::of(Conta::class)" in php
    assert "->getSimpleName()" in php
    assert 'JClass::of("int")' in php


def test_package_namespace_codegen() -> None:
    php = generate(
        """
        package app;
        class Main {
            public static void main(String[] args) {
                System.out.println("ok");
            }
        }
        """
    )
    assert "namespace app;" in php
    assert "use JSystem;" in php
    assert "Main::main(array_slice($argv, 1));" in php


def test_var_codegen() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                var x = 1;
                var nome = "Ana";
                System.out.println(nome + x);
            }
        }
        """
    )
    assert "$x = 1;" in php
    assert '$nome = "Ana";' in php
    assert "var $" not in php


def test_switch_arrow_and_expression_codegen() -> None:
    php = generate(
        """
        class A {
            public static void main(String[] args) {
                int x = 1;
                switch (x) {
                    case 1 -> System.out.println("um");
                    default -> System.out.println("outro");
                }
                String s = switch (x) {
                    case 1 -> "um";
                    default -> "outro";
                };
            }
        }
        """
    )
    assert "if ($__switch0 === 1)" in php
    assert "$__switchResult" in php
    assert 'case ($__switch1 === 1):' in php
    assert "$s = $__switchResult" in php
