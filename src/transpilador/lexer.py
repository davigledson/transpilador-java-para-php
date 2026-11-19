"""Analisador léxico para um subconjunto de Java, usando PLY (lex)."""

from __future__ import annotations

import ply.lex as lex

from .erros import TranspileError


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
        "RETURN",
        "BREAK",
        "CONTINUE",
        "NEW",
        "THIS",
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
        "NOT",
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
        "return": "RETURN",
        "break": "BREAK",
        "continue": "CONTINUE",
        "new": "NEW",
        "this": "THIS",
        "true": "TRUE",
        "false": "FALSE",
        "null": "NULL",
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
        "\\": "\\",
        '"': '"',
        "'": "'",
    }

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
        self.lexer.input(source)
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
        if token.type == "CLASS" and tokens[index + 1].type == "ID":
            names.add(tokens[index + 1].value)
    return names
