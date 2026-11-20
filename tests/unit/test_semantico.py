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


def test_switch_pattern_statement_and_expression() -> None:
    analyze(
        """
        interface Forma { }
        class Circulo implements Forma {
            double raio() { return 1.0; }
        }
        class Quadrado implements Forma { }
        class Main {
            public static void main(String[] args) {
                Forma f = new Circulo();
                switch (f) {
                    case Circulo c when c.raio() > 1 -> System.out.println("grande");
                    case Circulo c -> System.out.println(c.raio());
                    case Quadrado q -> System.out.println("quadrado");
                    case null -> System.out.println("nulo");
                    default -> System.out.println("outro");
                }
                String nome = switch (f) {
                    case Circulo c -> "C";
                    case null -> "N";
                    default -> "?";
                };
                System.out.println(nome);
            }
        }
        """
    )


def test_switch_pattern_must_be_compatible() -> None:
    with pytest.raises(TranspileError, match="compatível"):
        analyze(
            """
            interface Forma { }
            class Circulo implements Forma { }
            class Main {
                public static void main(String[] args) {
                    Circulo c = new Circulo();
                    switch (c) {
                        case String s -> System.out.println(s);
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )


def test_switch_pattern_rejects_primitive_selector() -> None:
    with pytest.raises(TranspileError, match="referência"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    int x = 1;
                    switch (x) {
                        case String s -> System.out.println(s);
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )


def test_switch_pattern_rejects_duplicate_unguarded() -> None:
    with pytest.raises(TranspileError, match="duplicado"):
        analyze(
            """
            interface Forma { }
            class Circulo implements Forma { }
            class Main {
                public static void main(String[] args) {
                    Forma f = new Circulo();
                    switch (f) {
                        case Circulo a -> System.out.println("a");
                        case Circulo b -> System.out.println("b");
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )


def test_switch_pattern_guard_must_be_boolean() -> None:
    with pytest.raises(TranspileError, match="boolean"):
        analyze(
            """
            interface Forma { }
            class Circulo implements Forma { }
            class Main {
                public static void main(String[] args) {
                    Forma f = new Circulo();
                    switch (f) {
                        case Circulo c when 1 -> System.out.println("a");
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )


def test_switch_pattern_rejects_classic_colon() -> None:
    with pytest.raises(TranspileError, match="->"):
        analyze(
            """
            interface Forma { }
            class Circulo implements Forma { }
            class Main {
                public static void main(String[] args) {
                    Forma f = new Circulo();
                    switch (f) {
                        case Circulo c:
                            break;
                        default:
                            break;
                    }
                }
            }
            """
        )


def test_switch_null_requires_reference_selector() -> None:
    with pytest.raises(TranspileError, match="referência"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    int x = 1;
                    switch (x) {
                        case null -> System.out.println("nulo");
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )


def test_switch_guard_requires_pattern() -> None:
    with pytest.raises(TranspileError, match="when"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    int x = 1;
                    switch (x) {
                        case 1 when x > 0 -> System.out.println("a");
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )


def test_annotation_registration_and_usage() -> None:
    program, analyzer = analyze(
        """
        public @interface MinhaAnotacao {
            String valor() default "";
            int prioridade() default 0;
        }

        @MinhaAnotacao(valor = "x")
        class Main {
            @MinhaAnotacao
            private String nome;

            @MinhaAnotacao
            public static void main(String[] args) {
                System.out.println("ok");
            }
        }
        """
    )
    info = analyzer.classes["MinhaAnotacao"]
    assert info.is_annotation
    assert info.is_interface
    assert [element.name for element in info.annotation_elements] == [
        "valor",
        "prioridade",
    ]


def test_annotation_rejects_duplicate_element() -> None:
    with pytest.raises(TranspileError, match="duplicado"):
        analyze(
            """
            @interface MinhaAnotacao {
                String valor() default "";
                int valor() default 0;
            }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_annotation_rejects_invalid_element_type() -> None:
    with pytest.raises(TranspileError, match="válido"):
        analyze(
            """
            @interface MinhaAnotacao {
                void valor();
            }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_annotation_rejects_invalid_modifier() -> None:
    with pytest.raises(TranspileError, match="modificador"):
        analyze(
            """
            final @interface MinhaAnotacao { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_sealed_hierarchy() -> None:
    analyze(
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
        sealed abstract class Animal permits Cachorro {
            abstract String som();
        }
        final class Cachorro extends Animal {
            String som() { return "latido"; }
        }
        class Main {
            public static void main(String[] args) {
                Forma f = new Circulo();
                System.out.println(f.area());
            }
        }
        """
    )


def test_sealed_allows_record_as_permitted_subtype() -> None:
    analyze(
        """
        sealed interface Forma permits Ponto { }
        record Ponto(int x) implements Forma { }
        class Main {
            public static void main(String[] args) { }
        }
        """
    )


def test_sealed_infers_permits() -> None:
    analyze(
        """
        sealed interface Forma { }
        final class Circulo implements Forma { }
        class Main {
            public static void main(String[] args) { }
        }
        """
    )


def test_sealed_subtype_must_be_permitted() -> None:
    with pytest.raises(TranspileError, match="permitido"):
        analyze(
            """
            sealed interface Forma permits Circulo { }
            final class Circulo implements Forma { }
            final class Quadrado implements Forma { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_sealed_permitted_type_must_be_final_sealed_or_non_sealed() -> None:
    with pytest.raises(TranspileError, match="final, sealed ou non-sealed"):
        analyze(
            """
            sealed interface Forma permits Circulo { }
            class Circulo implements Forma { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_sealed_permitted_type_must_be_direct_subtype() -> None:
    with pytest.raises(TranspileError, match="subtipo direto"):
        analyze(
            """
            sealed interface Forma permits Circulo { }
            final class Base implements Forma { }
            final class Circulo extends Base { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_permits_requires_sealed() -> None:
    with pytest.raises(TranspileError, match="permits"):
        analyze(
            """
            class Forma permits Circulo { }
            class Circulo extends Forma { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_non_sealed_requires_sealed_supertype() -> None:
    with pytest.raises(TranspileError, match="non-sealed"):
        analyze(
            """
            non-sealed class A { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_sealed_cannot_be_final() -> None:
    with pytest.raises(TranspileError, match="final"):
        analyze(
            """
            sealed final class A permits B { }
            final class B extends A { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_record_cannot_be_sealed() -> None:
    with pytest.raises(TranspileError, match="sealed"):
        analyze(
            """
            sealed record Ponto(int x) { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_record_components_accessors_and_constructor() -> None:
    program, _analyzer = analyze(
        """
        record Ponto(int x, int y) {
            public int soma() { return x + y; }
        }
        class Main {
            public static void main(String[] args) {
                Ponto p = new Ponto(1, 2);
                int a = p.x();
                int b = p.soma();
                System.out.println(a + b);
            }
        }
        """
    )
    record = program.classes[0]
    assert record.is_record
    stmts = program.classes[1].members[0].body.stmts
    assert stmts[1].init.inferred_type == ast.INT
    assert stmts[2].init.inferred_type == ast.INT


def test_record_rejects_instance_field() -> None:
    with pytest.raises(TranspileError, match="campos de instância"):
        analyze(
            """
            record Ponto(int x) {
                private int y;
            }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_record_rejects_non_canonical_constructor() -> None:
    with pytest.raises(TranspileError, match="construtor"):
        analyze(
            """
            record Ponto(int x) {
                public Ponto(String x) { }
            }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_record_rejects_duplicate_component() -> None:
    with pytest.raises(TranspileError, match="duplicado"):
        analyze(
            """
            record Ponto(int x, int x) { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_record_rejects_abstract() -> None:
    with pytest.raises(TranspileError, match="abstract"):
        analyze(
            """
            abstract record Ponto(int x) { }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_record_accessor_return_type_is_checked() -> None:
    with pytest.raises(TranspileError, match="acessador"):
        analyze(
            """
            record Ponto(int x) {
                public String x() { return "x"; }
            }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_try_with_resources_and_multi_catch() -> None:
    analyze(
        """
        class Recurso implements AutoCloseable {
            public void close() { System.out.println("fecha"); }
        }
        class OutroRecurso implements Closeable {
            public void close() { }
        }
        class Main {
            public static void main(String[] args) {
                try (Recurso r = new Recurso();
                     var s = new OutroRecurso()) {
                    System.out.println(r);
                    System.out.println(s);
                } catch (RuntimeException | Error e) {
                    System.out.println(e.getMessage());
                } finally {
                    System.out.println("fim");
                }
            }
        }
        """
    )


def test_resource_must_be_closeable() -> None:
    with pytest.raises(TranspileError, match="AutoCloseable"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    try (String s = "x") { }
                }
            }
            """
        )


def test_resource_requires_initializer() -> None:
    with pytest.raises(TranspileError, match="inicializador"):
        analyze(
            """
            class Recurso implements AutoCloseable {
                public void close() { }
            }
            class Main {
                public static void main(String[] args) {
                    try (Recurso r) { }
                }
            }
            """
        )


def test_autocloseable_requires_close_method() -> None:
    with pytest.raises(TranspileError, match="close"):
        analyze(
            """
            class Recurso implements AutoCloseable {
            }
            class Main {
                public static void main(String[] args) { }
            }
            """
        )


def test_multi_catch_rejects_related_types() -> None:
    with pytest.raises(TranspileError, match="relacionados"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    try {
                        System.out.println("x");
                    } catch (RuntimeException | IllegalStateException e) {
                        System.out.println(e.getMessage());
                    }
                }
            }
            """
        )


def test_resource_is_out_of_scope_in_catch() -> None:
    with pytest.raises(TranspileError, match="r"):
        analyze(
            """
            class Recurso implements AutoCloseable {
                public void close() { }
            }
            class Main {
                public static void main(String[] args) {
                    try (Recurso r = new Recurso()) {
                        System.out.println(r);
                    } catch (RuntimeException e) {
                        System.out.println(r);
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


def test_switch_allows_break() -> None:
    analyze(
        """
        class Main {
            public static void main(String[] args) {
                int x = 2;
                switch (x) {
                    case 1:
                        System.out.println("um");
                        break;
                    default:
                        break;
                }
            }
        }
        """
    )


def test_switch_type_is_checked() -> None:
    with pytest.raises(TranspileError, match="switch espera"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    double x = 1.0;
                    switch (x) {
                        case 1.0:
                            break;
                    }
                }
            }
            """
        )


def test_switch_duplicate_default_is_error() -> None:
    with pytest.raises(TranspileError, match="mais de um default"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    int x = 1;
                    switch (x) {
                        default:
                            break;
                        default:
                            break;
                    }
                }
            }
            """
        )


def test_continue_inside_switch_is_error() -> None:
    with pytest.raises(TranspileError, match="continue dentro de switch"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    for (int i = 0; i < 3; i++) {
                        switch (i) {
                            case 1:
                                continue;
                            default:
                                break;
                        }
                    }
                }
            }
            """
        )


def test_enum_type_switch_and_equality() -> None:
    analyze(
        """
        enum Status { ATIVO, BLOQUEADO }
        class Main {
            public static void main(String[] args) {
                Status s = Status.ATIVO;
                boolean ativo = s == Status.ATIVO;
                switch (s) {
                    case ATIVO:
                        System.out.println("ativo");
                        break;
                    case BLOQUEADO:
                        System.out.println("bloqueado");
                        break;
                    default:
                        break;
                }
            }
        }
        """
    )


def test_enum_invalid_constant_is_error() -> None:
    with pytest.raises(TranspileError, match="não é constante"):
        analyze(
            """
            enum Status { ATIVO }
            class Main {
                public static void main(String[] args) {
                    Status s = Status.INVALIDO;
                }
            }
            """
        )


def test_enum_cannot_be_instantiated() -> None:
    with pytest.raises(TranspileError, match="instanciar o enum"):
        analyze(
            """
            enum Status { ATIVO }
            class Main {
                public static void main(String[] args) {
                    Status s = new Status();
                }
            }
            """
        )


def test_duplicate_enum_constant_is_error() -> None:
    with pytest.raises(TranspileError, match="duplicada"):
        analyze(
            """
            enum Status { ATIVO, ATIVO }
            """
        )


def test_lambdas_and_streams() -> None:
    analyze(
        """
        class Main {
            public static void main(String[] args) {
                List<String> nomes = new ArrayList<>();
                nomes.add("Ana");
                nomes.add("Bia");
                nomes.forEach(n -> System.out.println(n));
                List<String> longos = nomes.stream()
                    .filter(n -> n.length() > 3)
                    .collect(Collectors.toList());
                List<String> maiusculos = nomes.stream()
                    .map(n -> n.toUpperCase())
                    .collect(Collectors.toList());
                int total = nomes.stream().count();
                boolean tem = nomes.stream().anyMatch(n -> n.equals("Ana"));
                nomes.removeIf(n -> n.startsWith("B"));
            }
        }
        """
    )


def test_lambda_requires_context() -> None:
    with pytest.raises(TranspileError, match="lambda só pode"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    String x = n -> n;
                }
            }
            """
        )


def test_lambda_arity_is_checked() -> None:
    with pytest.raises(TranspileError, match="lambda espera 1"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    List<String> nomes = new ArrayList<>();
                    nomes.forEach((a, b) -> a);
                }
            }
            """
        )


def test_block_lambda_is_error() -> None:
    with pytest.raises(TranspileError, match="lambda com bloco"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    List<String> nomes = new ArrayList<>();
                    nomes.forEach(n -> { System.out.println(n); });
                }
            }
            """
        )


def test_casts_and_instanceof() -> None:
    analyze(
        """
        class Animal {
            protected String nome;
            Animal(String nome) { this.nome = nome; }
            String falar() { return nome; }
        }
        class Cachorro extends Animal {
            Cachorro(String nome) { super(nome); }
        }
        class Main {
            public static void main(String[] args) {
                int i = (int) 3.9;
                double d = (double) 3;
                char c = (char) 65;
                int codigo = (int) 'a';
                Animal a = new Cachorro("Rex");
                boolean b = a instanceof Cachorro;
                Cachorro c2 = (Cachorro) a;
                System.out.println(c2.falar());
            }
        }
        """
    )


def test_invalid_cast_is_error() -> None:
    with pytest.raises(TranspileError, match="cast"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    String s = (String) 1;
                }
            }
            """
        )


def test_instanceof_requires_reference() -> None:
    with pytest.raises(TranspileError, match="instanceof"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    boolean b = 1 instanceof Main;
                }
            }
            """
        )


def test_pattern_instanceof_binding_scope() -> None:
    analyze(
        """
        class A {
            int valor;
        }
        class Main {
            public static void main(String[] args) {
                A a = new A();
                if (a instanceof A x) {
                    System.out.println(x.valor);
                }
                if (a instanceof A y && y.valor > 0) {
                    System.out.println(y.valor);
                }
                while (a instanceof A z) {
                    break;
                }
            }
        }
        """
    )


def test_pattern_instanceof_binding_outside_scope_is_error() -> None:
    with pytest.raises(TranspileError, match="x"):
        analyze(
            """
            class A { }
            class Main {
                public static void main(String[] args) {
                    A a = new A();
                    if (a instanceof A x) {
                        System.out.println(x);
                    } else {
                        System.out.println(x);
                    }
                }
            }
            """
        )


def test_class_literals_and_methods() -> None:
    analyze(
        """
        class Conta { }
        class Main {
            public static void main(String[] args) {
                Class c = Conta.class;
                System.out.println(c);
                System.out.println(c.getSimpleName());
                System.out.println(c.getName());
                Conta conta = new Conta();
                System.out.println(c.isInstance(conta));
            }
        }
        """
    )


def test_package_qualified_name() -> None:
    _program, analyzer = analyze(
        """
        package app;
        class Main {
            public static void main(String[] args) { }
        }
        """
    )
    info = analyzer.classes["Main"]
    assert info.package == "app"
    assert info.qualified_name == "app.Main"


def test_var_type_inference() -> None:
    program, _analyzer = analyze(
        """
        class Main {
            public static void main(String[] args) {
                var x = 1;
                var nome = "Ana";
                var lista = new ArrayList<String>();
                lista.add("Bia");
                for (var n : lista) {
                    System.out.println(n);
                }
            }
        }
        """
    )
    stmts = program.classes[0].members[0].body.stmts
    assert stmts[0].inferred_type == ast.INT
    assert stmts[1].inferred_type == ast.STRING
    assert stmts[2].inferred_type.name == "ArrayList"
    assert stmts[2].inferred_type.args == (ast.STRING,)
    assert stmts[4].type is None
    assert stmts[4].inferred_type == ast.STRING


def test_var_cannot_be_null() -> None:
    with pytest.raises(TranspileError, match="null"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    var x = null;
                }
            }
            """
        )


def test_switch_expression_semantics() -> None:
    analyze(
        """
        class Main {
            public static void main(String[] args) {
                int x = 2;
                String s = switch (x) {
                    case 1 -> "um";
                    default -> "outro";
                };
                String t = switch (x) {
                    case 1 -> {
                        yield "um";
                    }
                    default -> "outro";
                };
            }
        }
        """
    )


def test_switch_expression_requires_default() -> None:
    with pytest.raises(TranspileError, match="default"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    int x = 1;
                    String s = switch (x) {
                        case 1 -> "um";
                    };
                }
            }
            """
        )


def test_yield_outside_switch_expression_is_error() -> None:
    with pytest.raises(TranspileError, match="yield"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    yield 1;
                }
            }
            """
        )


def test_switch_mixing_arrow_and_colon_is_error() -> None:
    with pytest.raises(TranspileError, match="misture"):
        analyze(
            """
            class Main {
                public static void main(String[] args) {
                    int x = 1;
                    switch (x) {
                        case 1:
                            break;
                        default -> System.out.println("x");
                    }
                }
            }
            """
        )
