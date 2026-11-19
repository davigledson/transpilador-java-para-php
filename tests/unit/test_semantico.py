import pytest

from transpilador import ast
from transpilador.erros import TranspileError
from transpilador.lexer import JavaLexer, collect_type_names
from transpilador.parser import JavaParser
from transpilador.semantico import SemanticAnalyzer


def analyze(source: str) -> tuple[ast.Program, SemanticAnalyzer]:
    lexer = JavaLexer(collect_type_names(source))
    program = JavaParser().parse(source, lexer)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    return program, analyzer


def test_valid_program_and_main() -> None:
    _program, analyzer = analyze(
        """
        public class A {
            private String nome;
            A(String nome) { this.nome = nome; }
            public static void main(String[] args) {
                A a = new A("x");
                System.out.println(a.nome);
            }
        }
        """
    )
    assert "A" in analyzer.classes
    assert analyzer.classes["A"].has_main
    assert analyzer.classes["A"].fields["nome"].type == ast.STRING


def test_undefined_variable() -> None:
    with pytest.raises(TranspileError, match="símbolo não encontrado"):
        analyze(
            """
            class A {
                void m() { x = 1; }
            }
            """
        )


def test_type_mismatch() -> None:
    with pytest.raises(TranspileError, match="inicializar"):
        analyze(
            """
            class A {
                void m() { String s = 1; }
            }
            """
        )


def test_invalid_main_signature() -> None:
    with pytest.raises(TranspileError, match="main"):
        analyze(
            """
            class A {
                public static void main() { }
            }
            """
        )


def test_instance_call_from_static_is_allowed_with_object() -> None:
    analyze(
        """
        class A {
            void m() { }
            public static void main(String[] args) {
                A a = new A();
                a.m();
            }
        }
        """
    )


def test_int_division_and_string_concat_types() -> None:
    program, _analyzer = analyze(
        """
        class A {
            public static void main(String[] args) {
                int x = 7 / 2;
                System.out.println("x=" + x);
            }
        }
        """
    )
    method = program.classes[0].members[0]
    division = method.body.stmts[0].init
    concat = method.body.stmts[1].expr.args[0]
    assert division.inferred_type == ast.INT
    assert concat.inferred_type == ast.STRING


def test_inheritance_subtype_and_super() -> None:
    analyze(
        """
        class A {
            protected String nome;
            A(String nome) { this.nome = nome; }
            String falar() { return nome; }
        }
        class B extends A {
            B(String nome) { super(nome); }
            @Override
            String falar() { return super.falar(); }
        }
        class Main {
            public static void main(String[] args) {
                A a = new B("x");
                System.out.println(a.falar());
            }
        }
        """
    )


def test_missing_super_constructor_is_error() -> None:
    with pytest.raises(TranspileError, match="super"):
        analyze(
            """
            class A { A(int x) { } }
            class B extends A { B() { } }
            """
        )


def test_incompatible_override_is_error() -> None:
    with pytest.raises(TranspileError, match="retorno incompatível"):
        analyze(
            """
            class A { int f() { return 1; } }
            class B extends A { String f() { return "x"; } }
            """
        )


def test_subclass_assignment_is_not_reverse_compatible() -> None:
    with pytest.raises(TranspileError, match="inicializar"):
        analyze(
            """
            class A { }
            class B extends A { }
            class Main {
                public static void main(String[] args) {
                    B b = new A();
                }
            }
            """
        )


def test_inheritance_cycle_is_error() -> None:
    with pytest.raises(TranspileError, match="ciclo|herança"):
        analyze(
            """
            class A extends B { }
            class B extends A { }
            """
        )


def test_interface_implementation_and_subtype() -> None:
    analyze(
        """
        interface I { int f(); }
        class A implements I {
            public int f() { return 1; }
        }
        class Main {
            public static void main(String[] args) {
                I i = new A();
                System.out.println(i.f());
            }
        }
        """
    )


def test_missing_interface_method_is_error() -> None:
    with pytest.raises(TranspileError, match="não implementa"):
        analyze(
            """
            interface I { int f(); }
            class A implements I { }
            """
        )


def test_interface_extends_interface() -> None:
    analyze(
        """
        interface A { int f(); }
        interface B extends A { }
        class C implements B {
            public int f() { return 1; }
        }
        """
    )


def test_cannot_instantiate_interface_or_abstract_class() -> None:
    with pytest.raises(TranspileError, match="instanciar a interface"):
        analyze(
            """
            interface I { int f(); }
            class Main {
                public static void main(String[] args) {
                    I i = new I();
                }
            }
            """
        )

    with pytest.raises(TranspileError, match="instanciar a classe abstrata"):
        analyze(
            """
            abstract class A { }
            class Main {
                public static void main(String[] args) {
                    A a = new A();
                }
            }
            """
        )


def test_abstract_method_in_concrete_class_is_error() -> None:
    with pytest.raises(TranspileError, match="não abstrata"):
        analyze(
            """
            class A {
                abstract int f();
            }
            """
        )


def test_arraylist_and_scanner_types() -> None:
    analyze(
        """
        import java.util.ArrayList;
        import java.util.Scanner;
        class Main {
            public static void main(String[] args) {
                ArrayList<String> nomes = new ArrayList<>();
                nomes.add("Ana");
                String s = nomes.get(0);
                int n = nomes.size();
                Scanner sc = new Scanner(System.in);
                int x = sc.nextInt();
                System.out.println(s + n + x);
            }
        }
        """
    )


def test_arraylist_element_type_is_checked() -> None:
    with pytest.raises(TranspileError, match="espera String"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    ArrayList<String> nomes = new ArrayList<>();
                    nomes.add(1);
                }
            }
            """
        )


def test_list_variable_accepts_arraylist() -> None:
    analyze(
        """
        import java.util.ArrayList;
        import java.util.List;
        class Main {
            public static void main(String[] args) {
                List<String> nomes = new ArrayList<>();
                nomes.add("Ana");
                for (String nome : nomes) {
                    System.out.println(nome);
                }
            }
        }
        """
    )


def test_scanner_requires_system_in() -> None:
    with pytest.raises(TranspileError, match="System.in"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    Scanner sc = new Scanner(1);
                }
            }
            """
        )


def test_generic_primitive_is_error() -> None:
    with pytest.raises(TranspileError, match="primitivo"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    ArrayList<int> valores = new ArrayList<>();
                }
            }
            """
        )


def test_hashmap_and_hashset_types() -> None:
    analyze(
        """
        class Conta {
            Conta(String nome) { }
        }
        class Main {
            public static void main(String[] args) {
                Map<String, Conta> mapa = new HashMap<>();
                mapa.put("Ana", new Conta("Ana"));
                Conta c = mapa.get("Ana");
                System.out.println(mapa.size());
                System.out.println(c != null);

                Set<String> nomes = new HashSet<>();
                nomes.add("Ana");
                for (String nome : nomes) {
                    System.out.println(nome);
                }
            }
        }
        """
    )


def test_hashmap_key_type_is_checked() -> None:
    with pytest.raises(TranspileError, match="espera String"):
        analyze(
            """
            class Conta { }
            class Main {
                public static void main(String[] args) {
                    Map<String, Conta> mapa = new HashMap<>();
                    mapa.put(1, new Conta());
                }
            }
            """
        )


def test_hashset_element_type_is_checked() -> None:
    with pytest.raises(TranspileError, match="espera String"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    Set<String> nomes = new HashSet<>();
                    nomes.add(1);
                }
            }
            """
        )


def test_try_catch_finally_and_get_message() -> None:
    analyze(
        """
        class Main {
            public static void main(String[] args) {
                try {
                    throw new RuntimeException("falhou");
                } catch (RuntimeException e) {
                    System.out.println(e.getMessage());
                } finally {
                    System.out.println("fim");
                }
            }
        }
        """
    )


def test_custom_exception_extends_runtime_exception() -> None:
    analyze(
        """
        class MinhaExcecao extends RuntimeException {
            MinhaExcecao(String mensagem) {
                super(mensagem);
            }
        }
        class Main {
            public static void main(String[] args) {
                throw new MinhaExcecao("erro");
            }
        }
        """
    )


def test_catch_requires_exception_type() -> None:
    with pytest.raises(TranspileError, match="tipo de exceção"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    try { } catch (String e) { }
                }
            }
            """
        )


def test_throw_requires_exception() -> None:
    with pytest.raises(TranspileError, match="throw espera"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    throw 1;
                }
            }
            """
        )
