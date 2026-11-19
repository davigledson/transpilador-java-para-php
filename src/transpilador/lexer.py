"""Analisador léxico para um subconjunto de Java, usando PLY (lex)."""

from __future__ import annotations

import ply.lex as lex

from .erros import TranspileError


def _skip_quoted(source: str, index: int) -> int:
    quote = source[index]
    i = index + 1
    length = len(source)
    while i < length:
        if source[i] == "\\":
            i += 2
            continue
        if source[i] == quote:
            return i + 1
        i += 1
    return length


def _skip_text_block(source: str, index: int) -> int:
    i = index + 3
    length = len(source)
    while i < length:
        if source.startswith('"""', i):
            return i + 3
        if source[i] == "\\":
            i += 2
        else:
            i += 1
    return length


def _find_annotation_args_end(source: str, open_index: int) -> int | None:
    depth = 0
    i = open_index
    length = len(source)
    while i < length:
        if source.startswith("//", i):
            newline = source.find("\n", i)
            i = length if newline < 0 else newline
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = length if end < 0 else end + 2
            continue
        if source.startswith('"""', i):
            i = _skip_text_block(source, i)
            continue
        char = source[i]
        if char in {'"', "'"}:
            i = _skip_quoted(source, i)
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def strip_annotation_arguments(source: str) -> str:
    """Remove os argumentos das anotações, preservando linhas/colunas.

    ``@Column(name = "x", length = 150)`` vira ``@Column`` seguido de espaços.
    As anotações continuam sendo lidas e ignoradas; apenas os argumentos não
    precisam entrar na gramática.
    """

    chars = list(source)
    i = 0
    length = len(source)
    while i < length:
        if source.startswith("//", i):
            newline = source.find("\n", i)
            i = length if newline < 0 else newline
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = length if end < 0 else end + 2
            continue
        if source.startswith('"""', i):
            i = _skip_text_block(source, i)
            continue
        char = source[i]
        if char in {'"', "'"}:
            i = _skip_quoted(source, i)
            continue
        if char == "@":
            j = i + 1
            while j < length and (source[j].isalnum() or source[j] == "_"):
                j += 1
            k = j
            while k < length and source[k] in " \t\r\n":
                k += 1
            if k < length and source[k] == "(":
                end = _find_annotation_args_end(source, k)
                if end is not None:
                    for index in range(k, end):
                        if chars[index] not in "\r\n":
                            chars[index] = " "
                    i = end
                    continue
            i = j
            continue
        i += 1
    return "".join(chars)


class JavaLexer:
    tokens = (
        "CLASS",
        "EXTENDS",
        "IMPLEMENTS",
        "INTERFACE",
        "ENUM",
        "PACKAGE",
        "IMPORT",
        "PUBLIC",
        "PRIVATE",
        "PROTECTED",
        "STATIC",
        "FINAL",
        "ABSTRACT",
        "VOID",
        "INT",
        "DOUBLE",
        "BOOLEAN",
        "CHAR",
        "STRING",
        "LONG",
        "FLOAT",
        "BYTE",
        "SHORT",
        "IF",
        "ELSE",
        "WHILE",
        "FOR",
        "DO",
        "TRY",
        "CATCH",
        "FINALLY",
        "THROW",
        "THROWS",
        "SWITCH",
        "CASE",
        "DEFAULT",
        "RECORD",
        "SEALED",
        "VAR",
        "YIELD",
        "RETURN",
        "BREAK",
        "CONTINUE",
        "NEW",
        "THIS",
        "SUPER",
        "TRUE",
        "FALSE",
        "NULL",
        "ID",
        "TYPEID",
        "INT_LIT",
        "DOUBLE_LIT",
        "STRING_LIT",
        "CHAR_LIT",
        "PLUS",
        "MINUS",
        "TIMES",
        "DIV",
        "MOD",
        "ASSIGN",
        "EQ",
        "NE",
        "LT",
        "LE",
        "GT",
        "GE",
        "AND",
        "OR",
        "BITOR",
        "NOT",
        "INSTANCEOF",
        "INC",
        "DEC",
        "PLUS_ASSIGN",
        "MINUS_ASSIGN",
        "TIMES_ASSIGN",
        "DIV_ASSIGN",
        "DOT",
        "COMMA",
        "SEMI",
        "LPAREN",
        "RPAREN",
        "LBRACE",
        "RBRACE",
        "LBRACKET",
        "RBRACKET",
        "COLON",
        "QUESTION",
        "AT",
        "ARROW",
    )

    reserved = {
        "class": "CLASS",
        "extends": "EXTENDS",
        "implements": "IMPLEMENTS",
        "interface": "INTERFACE",
        "enum": "ENUM",
        "package": "PACKAGE",
        "import": "IMPORT",
        "public": "PUBLIC",
        "private": "PRIVATE",
        "protected": "PROTECTED",
        "static": "STATIC",
        "final": "FINAL",
        "abstract": "ABSTRACT",
        "void": "VOID",
        "int": "INT",
        "double": "DOUBLE",
        "boolean": "BOOLEAN",
        "char": "CHAR",
        "String": "STRING",
        "long": "LONG",
        "float": "FLOAT",
        "byte": "BYTE",
        "short": "SHORT",
        "if": "IF",
        "else": "ELSE",
        "while": "WHILE",
        "for": "FOR",
        "do": "DO",
        "try": "TRY",
        "catch": "CATCH",
        "finally": "FINALLY",
        "throw": "THROW",
        "throws": "THROWS",
        "switch": "SWITCH",
        "case": "CASE",
        "default": "DEFAULT",
        "record": "RECORD",
        "sealed": "SEALED",
        "var": "VAR",
        "yield": "YIELD",
        "return": "RETURN",
        "break": "BREAK",
        "continue": "CONTINUE",
        "new": "NEW",
        "this": "THIS",
        "super": "SUPER",
        "true": "TRUE",
        "false": "FALSE",
        "null": "NULL",
        "instanceof": "INSTANCEOF",
    }

    t_ignore = " \t\r\f"

    # ------------------------------------------------------------------
    # Comentários e espaços
    # ------------------------------------------------------------------

    def t_BLOCK_COMMENT(self, t):
        r"/\*([^*]|\*+[^*/])*\*+/"
        t.lexer.lineno += t.value.count("\n")
        # não retorna => token descartado

    def t_LINE_COMMENT(self, t):
        r"//[^\n]*"
        # não retorna => token descartado

    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)
        # não retorna => token descartado

    # ------------------------------------------------------------------
    # Literais
    # ------------------------------------------------------------------

    def t_DOUBLE_LIT(self, t):
        r"((\d+\.\d*|\.\d+)([eE][+-]?\d+)?|\d+[eE][+-]?\d+)"
        t.value = float(t.value)
        t.col = self._column(t)
        return t

    def t_INT_LIT(self, t):
        r"\d+"
        t.value = int(t.value)
        t.col = self._column(t)
        return t

    def t_TEXT_BLOCK(self, t):
        r'"""[\s\S]*?"""'
        raw = t.value
        t.value = self._decode_text_block(raw)
        t.col = self._column(t)
        t.lexer.lineno += raw.count("\n")
        t.type = "STRING_LIT"
        return t

    def t_STRING_LIT(self, t):
        r'"([^"\\\n]|\\.)*"'
        t.value = self._decode_escapes(t.value[1:-1])
        t.col = self._column(t)
        return t

    def t_CHAR_LIT(self, t):
        r"'([^'\\\n]|\\.)*'"
        t.value = self._decode_escapes(t.value[1:-1])
        t.col = self._column(t)
        return t

    # ------------------------------------------------------------------
    # Identificadores e palavras reservadas
    # ------------------------------------------------------------------

    def t_ID(self, t):
        r"[A-Za-z_][A-Za-z0-9_]*"
        if t.value in self.reserved:
            t.type = self.reserved[t.value]
        elif t.value in self.type_names:
            t.type = "TYPEID"
        else:
            t.type = "ID"
        t.col = self._column(t)
        return t

    # ------------------------------------------------------------------
    # Operadores de dois/três caracteres (funções vêm antes dos strings)
    # ------------------------------------------------------------------

    def t_PLUS_ASSIGN(self, t):
        r"\+="
        return t

    def t_MINUS_ASSIGN(self, t):
        r"-="
        return t

    def t_TIMES_ASSIGN(self, t):
        r"\*="
        return t

    def t_DIV_ASSIGN(self, t):
        r"/="
        return t

    def t_INC(self, t):
        r"\+\+"
        return t

    def t_DEC(self, t):
        r"--"
        return t

    def t_EQ(self, t):
        r"=="
        return t

    def t_NE(self, t):
        r"!="
        return t

    def t_LE(self, t):
        r"<="
        return t

    def t_GE(self, t):
        r">="
        return t

    def t_AND(self, t):
        r"&&"
        return t

    def t_OR(self, t):
        r"\|\|"
        return t

    t_BITOR = r"\|"

    def t_ARROW(self, t):
        r"->"
        return t

    # ------------------------------------------------------------------
    # Operadores e pontuação de um caractere
    # ------------------------------------------------------------------

    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIV = r"/"
    t_MOD = r"%"
    t_ASSIGN = r"="
    t_LT = r"<"
    t_GT = r">"
    t_NOT = r"!"
    t_DOT = r"\."
    t_COMMA = r","
    t_SEMI = r";"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACE = r"\{"
    t_RBRACE = r"\}"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"
    t_COLON = r":"
    t_QUESTION = r"\?"
    t_AT = r"@"

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------

    _ESCAPES = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        "b": "\b",
        "f": "\f",
        "0": "\0",
        "s": " ",
        "\\": "\\",
        '"': '"',
        "'": "'",
    }

    def _decode_text_block(self, raw: str) -> str:
        content = raw[3:-3].replace("\r\n", "\n").replace("\r", "\n")
        if "\n" in content:
            first, rest = content.split("\n", 1)
            if first.strip(" \t") == "":
                content = rest

        lines = content.split("\n")
        indents = [
            len(line) - len(line.lstrip(" \t"))
            for line in lines
            if line.strip(" \t") != ""
        ]
        indent = min(indents) if indents else 0

        stripped: list[str] = []
        for line in lines:
            if line.strip(" \t") == "":
                stripped.append("")
            else:
                stripped.append(line[indent:].rstrip(" \t"))
        return self._decode_escapes("\n".join(stripped))

    def _column(self, t) -> int:
        data = t.lexer.lexdata
        last_nl = data.rfind("\n", 0, t.lexpos)
        return t.lexpos - last_nl

    def _decode_escapes(self, raw: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(raw):
            char = raw[i]
            if char != "\\":
                out.append(char)
                i += 1
                continue
            i += 1
            if i >= len(raw):
                out.append("\\")
                break
            esc = raw[i]
            if esc == "\n":
                # Continuação de linha em text block: remove a quebra.
                i += 1
                continue
            if esc == "u":
                hex_part = raw[i + 1 : i + 5]
                if len(hex_part) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex_part):
                    out.append(chr(int(hex_part, 16)))
                    i += 5
                    continue
                out.append("\\u")
                i += 1
                continue
            out.append(self._ESCAPES.get(esc, esc))
            i += 1
        return "".join(out)

    def t_error(self, t):
        raise TranspileError(
            f"caractere inesperado {t.value[0]!r}",
            t.lineno,
            self._column(t),
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def __init__(self, type_names: set[str] | None = None) -> None:
        self.type_names = set(type_names or set())
        self.lexer = lex.lex(module=self)

    def tokenize(self, source: str) -> list[lex.LexToken]:
        self.lexer.lineno = 1
        self.lexer.input(strip_annotation_arguments(source))
        return list(iter(self.lexer.token, None))


def collect_type_names(source: str) -> set[str]:
    """Faz uma primeira passada só para descobrir os nomes de classes.

    Isso permite diferenciar ``Conta c`` (declaração) de ``conta[i]``
    (acesso a array) sem depender de análise semântica durante o parsing.
    """

    lexer = JavaLexer()
    tokens = lexer.tokenize(source)
    names: set[str] = set()
    for index, token in enumerate(tokens[:-1]):
        if token.type in {"CLASS", "INTERFACE", "ENUM"} and tokens[index + 1].type == "ID":
            names.add(tokens[index + 1].value)
    # Tipos de biblioteca que o transpilador conhece e traduz para o runtime.
    names.update(
        {
            "ArrayList",
            "List",
            "Scanner",
            "HashMap",
            "Map",
            "HashSet",
            "Set",
            "Stream",
            "Class",
            "Throwable",
            "Error",
            "Exception",
            "RuntimeException",
            "IllegalArgumentException",
            "IllegalStateException",
            "ArithmeticException",
            "NullPointerException",
            "IndexOutOfBoundsException",
            "IOException",
            "AutoCloseable",
            "Closeable",
        }
    )
    return names
