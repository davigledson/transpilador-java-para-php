from transpilador.lexer import JavaLexer, collect_type_names


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
