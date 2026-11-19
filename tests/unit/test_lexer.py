from transpilador.lexer import (
    JavaLexer,
    collect_type_names,
    strip_annotation_arguments,
)


def kinds(source: str) -> list[str]:
    names = collect_type_names(source)
    return [token.type for token in JavaLexer(names).tokenize(source)]


def test_collect_type_names() -> None:
    source = "class A { } class B extends A { }"
    names = collect_type_names(source)
    assert {"A", "B"} <= names
    assert {"ArrayList", "List", "Scanner"} <= names


def test_keywords_literals_and_typeid() -> None:
    source = 'public class A { int x = 1; String s = "oi"; }'
    result = kinds(source)
    assert result[0] == "PUBLIC"
    assert "TYPEID" in result
    assert "INT_LIT" in result
    assert "STRING_LIT" in result


def test_comments_are_ignored() -> None:
    source = """
    // comentário
    class A {
        /* outro comentário */
        int x = 1;
    }
    """
    result = kinds(source)
    assert "INT_LIT" in result
    assert result.count("INT") == 1


def test_string_escapes() -> None:
    source = 'class A { String s = "linha\\n\\"x\\""; }'
    tokens = JavaLexer(collect_type_names(source)).tokenize(source)
    literal = next(token for token in tokens if token.type == "STRING_LIT")
    assert literal.value == 'linha\n"x"'


def test_text_block() -> None:
    source = 'class A { String s = """\n    linha 1\n    linha 2\n    """; }'
    tokens = JavaLexer(collect_type_names(source)).tokenize(source)
    literal = next(token for token in tokens if token.type == "STRING_LIT")
    assert literal.value == "linha 1\nlinha 2\n"


def test_strip_annotation_arguments_preserves_positions() -> None:
    source = '@Column(name = "x", length = 150)\nclass A { }'
    stripped = strip_annotation_arguments(source)
    assert "@Column" in stripped
    assert "name" not in stripped
    assert len(stripped) == len(source)
    assert stripped.count("\n") == source.count("\n")
