"""Analisador sintático (PLY/yacc) para um subconjunto de Java."""

from __future__ import annotations

import ply.yacc as yacc

from . import ast
from .erros import TranspileError
from .lexer import JavaLexer, strip_annotation_arguments


class JavaParser:
    tokens = JavaLexer.tokens
    start = "program"

    # Usado para o "else" pendente e para o menos unário.
    precedence = (
        ("right", "ELSE"),
        ("right", "UMINUS"),
    )

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.parser = yacc.yacc(
            module=self,
            start=self.start,
            debug=False,
            write_tables=False,
        )

    def _pos(self, p, index: int = 1) -> tuple[int, int]:
        line = p.lineno(index) or 0
        lexpos = p.lexpos(index)
        col = 0
        if lexpos is not None and getattr(p, "lexer", None) is not None:
            data = p.lexer.lexdata
            last_nl = data.rfind("\n", 0, lexpos)
            col = lexpos - last_nl
        return line, col

    def _column(self, tok) -> int:
        data = tok.lexer.lexdata
        last_nl = data.rfind("\n", 0, tok.lexpos)
        return tok.lexpos - last_nl

    def parse(self, source: str, lexer: JavaLexer) -> ast.Program:
        self._validate_unsupported(source, lexer)
        lexer.lexer.lineno = 1
        result = self.parser.parse(
            strip_annotation_arguments(source),
            lexer=lexer.lexer,
            tracking=True,
        )
        if result is None:
            raise TranspileError("não foi possível gerar a AST")
        return result

    def _validate_unsupported(self, source: str, lexer: JavaLexer) -> None:
        tokens = lexer.tokenize(source)
        data = strip_annotation_arguments(source)
        for index, token in enumerate(tokens):
            if token.type == "RECORD":
                raise TranspileError(
                    "record ainda não é suportado; use uma classe comum",
                    token.lineno,
                    self._token_column(data, token.lexpos),
                )
            if (
                token.type == "AT"
                and index + 1 < len(tokens)
                and tokens[index + 1].type == "INTERFACE"
            ):
                raise TranspileError(
                    "@interface (declaração de anotação) ainda não é suportado",
                    token.lineno,
                    self._token_column(data, token.lexpos),
                )

    def _token_column(self, data: str, lexpos: int) -> int:
        last_nl = data.rfind("\n", 0, lexpos)
        return lexpos - last_nl

    # ------------------------------------------------------------------
    # Estrutura geral
    # ------------------------------------------------------------------

    def p_program(self, p):
        "program : package_opt imports_opt class_list"
        line, col = self._pos(p, 3)
        for cls in p[3]:
            cls.package = p[1]
            cls.imports = list(p[2])
        p[0] = ast.Program(
            classes=p[3],
            package=p[1],
            imports=list(p[2]),
            line=line,
            col=col,
        )

    def p_package_opt(self, p):
        "package_opt : PACKAGE dotted_name SEMI"
        p[0] = p[2]

    def p_package_empty(self, p):
        "package_opt : empty"
        p[0] = None

    def p_imports_opt_many(self, p):
        "imports_opt : imports_opt IMPORT dotted_name SEMI"
        p[0] = p[1] + [p[3]]

    def p_imports_opt_empty(self, p):
        "imports_opt : empty"
        p[0] = []

    def p_dotted_name_one(self, p):
        "dotted_name : dotted_part"
        p[0] = p[1]

    def p_dotted_name_many(self, p):
        "dotted_name : dotted_name DOT dotted_part"
        p[0] = p[1] + "." + p[3]

    def p_dotted_part(self, p):
        """dotted_part : ID
                       | TYPEID"""
        p[0] = p[1]

    def p_class_list_many(self, p):
        "class_list : class_list top_decl"
        p[0] = p[1] + [p[2]]

    def p_class_list_one(self, p):
        "class_list : top_decl"
        p[0] = [p[1]]

    def p_top_decl_class(self, p):
        "top_decl : class_decl"
        p[0] = p[1]

    def p_top_decl_interface(self, p):
        "top_decl : interface_decl"
        p[0] = p[1]

    def p_top_decl_enum(self, p):
        "top_decl : enum_decl"
        p[0] = p[1]

    def p_top_decl_record(self, p):
        "top_decl : modifiers RECORD"
        line, col = self._pos(p, 2)
        raise TranspileError(
            "record ainda não é suportado; use uma classe comum",
            line,
            col,
        )

    def p_top_decl_interface_annotation(self, p):
        "top_decl : modifiers AT INTERFACE"
        line, col = self._pos(p, 2)
        raise TranspileError(
            "@interface (declaração de anotação) ainda não é suportado",
            line,
            col,
        )

    # ------------------------------------------------------------------
    # Classes e interfaces
    # ------------------------------------------------------------------

    def p_class_decl(self, p):
        "class_decl : modifiers CLASS TYPEID extends_opt implements_opt LBRACE class_body RBRACE"
        line, col = self._pos(p, 2)
        p[0] = ast.ClassDecl(
            name=p[3],
            extends=p[4],
            members=p[7],
            implements=p[5],
            modifiers=p[1],
            is_interface=False,
            line=line,
            col=col,
        )

    def p_interface_decl(self, p):
        "interface_decl : modifiers INTERFACE TYPEID extends_opt LBRACE interface_body RBRACE"
        line, col = self._pos(p, 2)
        p[0] = ast.ClassDecl(
            name=p[3],
            extends=p[4],
            members=p[6],
            implements=[],
            modifiers=p[1],
            is_interface=True,
            line=line,
            col=col,
        )

    def p_interface_body_many(self, p):
        "interface_body : interface_body interface_member"
        p[0] = p[1] + [p[2]]

    def p_interface_body_empty(self, p):
        "interface_body : empty"
        p[0] = []

    def p_interface_member(self, p):
        "interface_member : modifiers type ID LPAREN params_opt RPAREN throws_opt SEMI"
        line, col = self._pos(p, 2)
        p[0] = ast.MethodDecl(
            name=p[3],
            return_type=p[2],
            params=p[5],
            body=None,
            modifiers=p[1],
            line=line,
            col=col,
        )

    def p_throws_opt(self, p):
        "throws_opt : THROWS name_list"
        p[0] = p[2]

    def p_throws_empty(self, p):
        "throws_opt : empty"
        p[0] = []

    def p_enum_decl(self, p):
        "enum_decl : modifiers ENUM TYPEID LBRACE enum_constants_opt RBRACE"
        line, col = self._pos(p, 2)
        p[0] = ast.ClassDecl(
            name=p[3],
            extends=None,
            members=[],
            implements=[],
            modifiers=p[1],
            is_enum=True,
            enum_constants=p[5],
            line=line,
            col=col,
        )

    def p_enum_constants_opt(self, p):
        "enum_constants_opt : enum_constants"
        p[0] = p[1]

    def p_enum_constants_empty(self, p):
        "enum_constants_opt : empty"
        p[0] = []

    def p_enum_constants_many(self, p):
        "enum_constants : enum_constants COMMA enum_constant"
        p[0] = p[1] + [p[3]]

    def p_enum_constants_trailing(self, p):
        "enum_constants : enum_constants COMMA"
        p[0] = p[1]

    def p_enum_constants_one(self, p):
        "enum_constants : enum_constant"
        p[0] = [p[1]]

    def p_enum_constant(self, p):
        """enum_constant : ID
                         | TYPEID"""
        p[0] = p[1]

    def p_extends_opt(self, p):
        "extends_opt : EXTENDS class_ref"
        p[0] = p[2]

    def p_extends_empty(self, p):
        "extends_opt : empty"
        p[0] = None

    def p_class_ref(self, p):
        """class_ref : ID
                     | TYPEID"""
        p[0] = p[1]

    def p_implements_opt(self, p):
        "implements_opt : IMPLEMENTS name_list"
        p[0] = p[2]

    def p_implements_empty(self, p):
        "implements_opt : empty"
        p[0] = []

    def p_name_list_many(self, p):
        "name_list : name_list COMMA name_item"
        p[0] = p[1] + [p[3]]

    def p_name_list_one(self, p):
        "name_list : name_item"
        p[0] = [p[1]]

    def p_name_item(self, p):
        """name_item : ID
                     | TYPEID"""
        p[0] = p[1]

    def p_modifiers_many(self, p):
        "modifiers : modifiers modifier"
        p[0] = p[1] | {p[2]}

    def p_modifiers_empty(self, p):
        "modifiers : empty"
        p[0] = set()

    def p_modifier(self, p):
        """modifier : PUBLIC
                    | PRIVATE
                    | PROTECTED
                    | STATIC
                    | FINAL
                    | ABSTRACT
                    | annotation"""
        p[0] = p[1]

    def p_modifier_sealed(self, p):
        "modifier : SEALED"
        line, col = self._pos(p, 1)
        raise TranspileError(
            "sealed classes ainda não são suportadas",
            line,
            col,
        )

    def p_annotation(self, p):
        "annotation : AT ID"
        p[0] = "annotation"

    def p_class_body_many(self, p):
        "class_body : class_body member"
        p[0] = p[1] + p[2]

    def p_class_body_empty(self, p):
        "class_body : empty"
        p[0] = []

    def p_member(self, p):
        "member : modifiers member_rest"
        nodes = p[2] if isinstance(p[2], list) else [p[2]]
        for node in nodes:
            node.modifiers = p[1]
        p[0] = nodes

    def p_member_rest_constructor(self, p):
        "member_rest : TYPEID LPAREN params_opt RPAREN throws_opt block"
        line, col = self._pos(p, 1)
        p[0] = ast.ConstructorDecl(
            name=p[1],
            params=p[3],
            body=p[6],
            line=line,
            col=col,
        )

    def p_member_rest_typed(self, p):
        "member_rest : type ID member_tail"
        line, col = self._pos(p, 1)
        kind, value, body = p[3]
        if kind == "method":
            p[0] = ast.MethodDecl(
                name=p[2],
                return_type=p[1],
                params=value,
                body=body,
                line=line,
                col=col,
            )
        else:
            p[0] = ast.FieldDecl(
                name=p[2],
                type=p[1],
                init=value,
                line=line,
                col=col,
            )

    def p_member_tail_method(self, p):
        "member_tail : LPAREN params_opt RPAREN throws_opt block"
        p[0] = ("method", p[2], p[5])

    def p_member_tail_abstract_method(self, p):
        "member_tail : LPAREN params_opt RPAREN throws_opt SEMI"
        p[0] = ("method", p[2], None)

    def p_member_tail_field_init(self, p):
        "member_tail : ASSIGN expr SEMI"
        p[0] = ("field", p[2], None)

    def p_member_tail_field(self, p):
        "member_tail : SEMI"
        p[0] = ("field", None, None)

    # ------------------------------------------------------------------
    # Parâmetros e tipos
    # ------------------------------------------------------------------

    def p_params_opt(self, p):
        "params_opt : params"
        p[0] = p[1]

    def p_params_empty(self, p):
        "params_opt : empty"
        p[0] = []

    def p_params_many(self, p):
        "params : params COMMA param"
        p[0] = p[1] + [p[3]]

    def p_params_one(self, p):
        "params : param"
        p[0] = [p[1]]

    def p_param(self, p):
        "param : type ID"
        line, col = self._pos(p, 2)
        p[0] = ast.Param(name=p[2], type=p[1], line=line, col=col)

    def p_type_basic(self, p):
        """type : INT
                | DOUBLE
                | BOOLEAN
                | CHAR
                | STRING
                | VOID
                | LONG
                | FLOAT
                | BYTE
                | SHORT"""
        line, col = self._pos(p, 1)
        p[0] = ast.JavaType(p[1], 0, line, col)

    def p_type_class(self, p):
        "type : TYPEID generic_args_opt"
        line, col = self._pos(p, 1)
        p[0] = ast.JavaType(p[1], 0, line, col, tuple(p[2]))

    def p_type_array(self, p):
        "type : type LBRACKET RBRACKET"
        p[0] = ast.JavaType(
            p[1].name,
            p[1].dims + 1,
            p[1].line,
            p[1].col,
            p[1].args,
        )

    def p_generic_args_opt(self, p):
        """generic_args_opt : LT generic_args GT
                            | LT GT"""
        p[0] = p[2] if len(p) == 4 else ()

    def p_generic_args_empty(self, p):
        "generic_args_opt : empty"
        p[0] = ()

    def p_generic_args_many(self, p):
        "generic_args : generic_args COMMA type"
        p[0] = p[1] + (p[3],)

    def p_generic_args_one(self, p):
        "generic_args : type"
        p[0] = (p[1],)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def p_stmt_block(self, p):
        "stmt : block"
        p[0] = p[1]

    def p_block(self, p):
        "block : LBRACE stmt_list RBRACE"
        line, col = self._pos(p, 1)
        p[0] = ast.Block(stmts=p[2], line=line, col=col)

    def p_stmt_list_many(self, p):
        "stmt_list : stmt_list stmt"
        p[0] = p[1] + [p[2]]

    def p_stmt_list_empty(self, p):
        "stmt_list : empty"
        p[0] = []

    def p_stmt_if(self, p):
        "stmt : IF LPAREN expr RPAREN stmt else_opt"
        line, col = self._pos(p, 1)
        p[0] = ast.If(cond=p[3], then=p[5], else_=p[6], line=line, col=col)

    def p_else_opt(self, p):
        "else_opt : ELSE stmt"
        p[0] = p[2]

    def p_else_empty(self, p):
        "else_opt : empty"
        p[0] = None

    def p_stmt_while(self, p):
        "stmt : WHILE LPAREN expr RPAREN stmt"
        line, col = self._pos(p, 1)
        p[0] = ast.While(cond=p[3], body=p[5], line=line, col=col)

    def p_stmt_do_while(self, p):
        "stmt : DO stmt WHILE LPAREN expr RPAREN SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.DoWhile(body=p[2], cond=p[5], line=line, col=col)

    def p_stmt_try(self, p):
        "stmt : TRY block catch_list finally_opt"
        line, col = self._pos(p, 1)
        p[0] = ast.Try(
            body=p[2],
            catches=p[3],
            finally_=p[4],
            line=line,
            col=col,
        )

    def p_stmt_try_finally(self, p):
        "stmt : TRY block FINALLY block"
        line, col = self._pos(p, 1)
        p[0] = ast.Try(body=p[2], catches=[], finally_=p[4], line=line, col=col)

    def p_stmt_try_resources(self, p):
        "stmt : TRY LPAREN"
        line, col = self._pos(p, 1)
        raise TranspileError(
            "try-with-resources ainda não é suportado",
            line,
            col,
        )

    def p_catch_list_many(self, p):
        "catch_list : catch_list catch_clause"
        p[0] = p[1] + [p[2]]

    def p_catch_list_one(self, p):
        "catch_list : catch_clause"
        p[0] = [p[1]]

    def p_catch_clause(self, p):
        "catch_clause : CATCH LPAREN type ID RPAREN block"
        line, col = self._pos(p, 1)
        p[0] = ast.Catch(type=p[3], name=p[4], body=p[6], line=line, col=col)

    def p_catch_clause_multi(self, p):
        "catch_clause : CATCH LPAREN type BITOR"
        line, col = self._pos(p, 1)
        raise TranspileError(
            "multi-catch (catch (A | B e)) ainda não é suportado",
            line,
            col,
        )

    def p_finally_opt(self, p):
        "finally_opt : FINALLY block"
        p[0] = p[2]

    def p_finally_empty(self, p):
        "finally_opt : empty"
        p[0] = None

    def p_stmt_throw(self, p):
        "stmt : THROW expr SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Throw(value=p[2], line=line, col=col)

    def p_stmt_yield(self, p):
        "stmt : YIELD expr SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Yield(value=p[2], line=line, col=col)

    def p_stmt_switch(self, p):
        "stmt : SWITCH LPAREN expr RPAREN LBRACE switch_body RBRACE"
        line, col = self._pos(p, 1)
        p[0] = ast.Switch(expr=p[3], cases=p[6], line=line, col=col)

    def p_switch_body_many(self, p):
        "switch_body : switch_body switch_clause"
        p[0] = p[1] + [p[2]]

    def p_switch_body_empty(self, p):
        "switch_body : empty"
        p[0] = []

    def p_switch_clause_case(self, p):
        "switch_clause : CASE expr COLON stmt_list"
        line, col = self._pos(p, 1)
        p[0] = ast.SwitchCase(value=p[2], stmts=p[4], line=line, col=col)

    def p_switch_clause_default(self, p):
        "switch_clause : DEFAULT COLON stmt_list"
        line, col = self._pos(p, 1)
        p[0] = ast.SwitchCase(value=None, stmts=p[3], line=line, col=col)

    def p_switch_clause_case_arrow(self, p):
        "switch_clause : CASE expr ARROW arrow_body"
        line, col = self._pos(p, 1)
        p[0] = ast.SwitchCase(
            value=p[2],
            arrow=True,
            arrow_body=p[4],
            line=line,
            col=col,
        )

    def p_switch_clause_default_arrow(self, p):
        "switch_clause : DEFAULT ARROW arrow_body"
        line, col = self._pos(p, 1)
        p[0] = ast.SwitchCase(
            value=None,
            arrow=True,
            arrow_body=p[3],
            line=line,
            col=col,
        )

    def p_arrow_body_expr(self, p):
        "arrow_body : expr SEMI"
        p[0] = p[1]

    def p_arrow_body_block(self, p):
        "arrow_body : block"
        p[0] = p[1]

    def p_arrow_body_throw(self, p):
        "arrow_body : THROW expr SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Throw(value=p[2], line=line, col=col)

    def p_stmt_for(self, p):
        "stmt : FOR LPAREN for_header RPAREN stmt"
        line, col = self._pos(p, 1)
        kind = p[3][0]
        if kind == "classic":
            p[0] = ast.For(
                init=p[3][1],
                cond=p[3][2],
                update=p[3][3],
                body=p[5],
                line=line,
                col=col,
            )
        else:
            p[0] = ast.ForEach(
                type=p[3][1],
                name=p[3][2],
                iterable=p[3][3],
                body=p[5],
                line=line,
                col=col,
            )

    def p_for_header_classic(self, p):
        "for_header : for_init SEMI expr_opt SEMI for_update_opt"
        p[0] = ("classic", p[1], p[3], p[5])

    def p_for_header_each(self, p):
        "for_header : type ID COLON expr"
        p[0] = ("each", p[1], p[2], p[4])

    def p_for_header_each_var(self, p):
        "for_header : VAR ID COLON expr"
        p[0] = ("each", None, p[2], p[4])

    def p_for_init_local(self, p):
        "for_init : local_decl"
        p[0] = p[1]

    def p_for_init_expr(self, p):
        "for_init : expr"
        _line, _col = self._pos(p, 1)
        p[0] = ast.ExprStmt(expr=p[1], line=_line, col=_col)

    def p_for_init_empty(self, p):
        "for_init : empty"
        p[0] = None

    def p_for_update_opt(self, p):
        "for_update_opt : expr"
        p[0] = p[1]

    def p_for_update_empty(self, p):
        "for_update_opt : empty"
        p[0] = None

    def p_stmt_return(self, p):
        "stmt : RETURN expr_opt SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Return(value=p[2], line=line, col=col)

    def p_expr_opt(self, p):
        "expr_opt : expr"
        p[0] = p[1]

    def p_expr_opt_empty(self, p):
        "expr_opt : empty"
        p[0] = None

    def p_stmt_break(self, p):
        "stmt : BREAK SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Break(line=line, col=col)

    def p_stmt_continue(self, p):
        "stmt : CONTINUE SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Continue(line=line, col=col)

    def p_stmt_local(self, p):
        "stmt : local_decl SEMI"
        p[0] = p[1]

    def p_stmt_expr(self, p):
        "stmt : expr SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.ExprStmt(expr=p[1], line=line, col=col)

    def p_stmt_empty(self, p):
        "stmt : SEMI"
        line, col = self._pos(p, 1)
        p[0] = ast.Block(stmts=[], line=line, col=col)

    def p_local_decl_init(self, p):
        "local_decl : type ID ASSIGN expr"
        line, col = self._pos(p, 2)
        p[0] = ast.LocalVarDecl(name=p[2], type=p[1], init=p[4], line=line, col=col)

    def p_local_decl(self, p):
        "local_decl : type ID"
        line, col = self._pos(p, 2)
        p[0] = ast.LocalVarDecl(name=p[2], type=p[1], init=None, line=line, col=col)

    def p_local_decl_var(self, p):
        "local_decl : VAR ID ASSIGN expr"
        line, col = self._pos(p, 2)
        p[0] = ast.LocalVarDecl(name=p[2], type=None, init=p[4], line=line, col=col)

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------

    def p_expr(self, p):
        "expr : assignment"
        p[0] = p[1]

    def p_assignment_plain(self, p):
        "assignment : ternary"
        p[0] = p[1]

    def p_assignment(self, p):
        """assignment : ternary ASSIGN assignment
                      | ternary PLUS_ASSIGN assignment
                      | ternary MINUS_ASSIGN assignment
                      | ternary TIMES_ASSIGN assignment
                      | ternary DIV_ASSIGN assignment"""
        line, col = self._pos(p, 1)
        p[0] = ast.Assign(op=p[2], target=p[1], value=p[3], line=line, col=col)

    def p_ternary_plain(self, p):
        "ternary : or_expr"
        p[0] = p[1]

    def p_ternary(self, p):
        "ternary : or_expr QUESTION expr COLON ternary"
        line, col = self._pos(p, 1)
        p[0] = ast.Ternary(cond=p[1], then=p[3], else_=p[5], line=line, col=col)

    def p_or_expr_many(self, p):
        "or_expr : or_expr OR and_expr"
        line, col = self._pos(p, 1)
        p[0] = ast.Binary(op="||", left=p[1], right=p[3], line=line, col=col)

    def p_or_expr(self, p):
        "or_expr : and_expr"
        p[0] = p[1]

    def p_and_expr_many(self, p):
        "and_expr : and_expr AND equality"
        line, col = self._pos(p, 1)
        p[0] = ast.Binary(op="&&", left=p[1], right=p[3], line=line, col=col)

    def p_and_expr(self, p):
        "and_expr : equality"
        p[0] = p[1]

    def p_equality_many(self, p):
        """equality : equality EQ relational
                    | equality NE relational"""
        line, col = self._pos(p, 1)
        p[0] = ast.Binary(op=p[2], left=p[1], right=p[3], line=line, col=col)

    def p_equality(self, p):
        "equality : relational"
        p[0] = p[1]

    def p_relational_many(self, p):
        """relational : relational LT additive
                      | relational LE additive
                      | relational GT additive
                      | relational GE additive"""
        line, col = self._pos(p, 1)
        p[0] = ast.Binary(op=p[2], left=p[1], right=p[3], line=line, col=col)

    def p_relational_instanceof(self, p):
        "relational : relational INSTANCEOF type"
        line, col = self._pos(p, 1)
        p[0] = ast.InstanceOf(expr=p[1], type=p[3], line=line, col=col)

    def p_relational_instanceof_binding(self, p):
        "relational : relational INSTANCEOF type ID"
        line, col = self._pos(p, 1)
        p[0] = ast.InstanceOf(
            expr=p[1],
            type=p[3],
            binding=p[4],
            line=line,
            col=col,
        )

    def p_relational(self, p):
        "relational : additive"
        p[0] = p[1]

    def p_additive_many(self, p):
        """additive : additive PLUS multiplicative
                    | additive MINUS multiplicative"""
        line, col = self._pos(p, 1)
        p[0] = ast.Binary(op=p[2], left=p[1], right=p[3], line=line, col=col)

    def p_additive(self, p):
        "additive : multiplicative"
        p[0] = p[1]

    def p_multiplicative_many(self, p):
        """multiplicative : multiplicative TIMES unary
                          | multiplicative DIV unary
                          | multiplicative MOD unary"""
        line, col = self._pos(p, 1)
        p[0] = ast.Binary(op=p[2], left=p[1], right=p[3], line=line, col=col)

    def p_multiplicative(self, p):
        "multiplicative : unary"
        p[0] = p[1]

    def p_unary(self, p):
        """unary : NOT unary
                 | PLUS unary
                 | INC unary
                 | DEC unary"""
        line, col = self._pos(p, 1)
        p[0] = ast.Unary(op=p[1], operand=p[2], prefix=True, line=line, col=col)

    def p_unary_minus(self, p):
        "unary : MINUS unary %prec UMINUS"
        line, col = self._pos(p, 1)
        p[0] = ast.Unary(op="-", operand=p[2], prefix=True, line=line, col=col)

    def p_unary_cast(self, p):
        "unary : LPAREN type RPAREN unary"
        line, col = self._pos(p, 1)
        p[0] = ast.Cast(type=p[2], expr=p[4], line=line, col=col)

    def p_unary_postfix(self, p):
        "unary : postfix"
        p[0] = p[1]

    def p_postfix_field(self, p):
        "postfix : postfix DOT ID"
        line, col = self._pos(p, 1)
        p[0] = ast.FieldAccess(target=p[1], name=p[3], line=line, col=col)

    def p_postfix_call(self, p):
        "postfix : postfix LPAREN args_opt RPAREN"
        line, col = self._pos(p, 1)
        p[0] = ast.Call(callee=p[1], args=p[3], line=line, col=col)

    def p_postfix_index(self, p):
        "postfix : postfix LBRACKET expr RBRACKET"
        line, col = self._pos(p, 1)
        p[0] = ast.ArrayAccess(array=p[1], index=p[3], line=line, col=col)

    def p_postfix_inc(self, p):
        "postfix : postfix INC"
        line, col = self._pos(p, 1)
        p[0] = ast.Unary(op="++", operand=p[1], prefix=False, line=line, col=col)

    def p_postfix_dec(self, p):
        "postfix : postfix DEC"
        line, col = self._pos(p, 1)
        p[0] = ast.Unary(op="--", operand=p[1], prefix=False, line=line, col=col)

    def p_postfix_primary(self, p):
        "postfix : primary"
        p[0] = p[1]

    def p_args_opt(self, p):
        "args_opt : args"
        p[0] = p[1]

    def p_args_empty(self, p):
        "args_opt : empty"
        p[0] = []

    def p_args_many(self, p):
        "args : args COMMA expr"
        p[0] = p[1] + [p[3]]

    def p_args_one(self, p):
        "args : expr"
        p[0] = [p[1]]

    def p_primary_int(self, p):
        "primary : INT_LIT"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=p[1], kind="int", line=line, col=col)

    def p_primary_double(self, p):
        "primary : DOUBLE_LIT"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=p[1], kind="double", line=line, col=col)

    def p_primary_string(self, p):
        "primary : STRING_LIT"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=p[1], kind="string", line=line, col=col)

    def p_primary_char(self, p):
        "primary : CHAR_LIT"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=p[1], kind="char", line=line, col=col)

    def p_primary_true(self, p):
        "primary : TRUE"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=True, kind="boolean", line=line, col=col)

    def p_primary_false(self, p):
        "primary : FALSE"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=False, kind="boolean", line=line, col=col)

    def p_primary_null(self, p):
        "primary : NULL"
        line, col = self._pos(p, 1)
        p[0] = ast.Literal(value=None, kind="null", line=line, col=col)

    def p_primary_this(self, p):
        "primary : THIS"
        line, col = self._pos(p, 1)
        p[0] = ast.This(line=line, col=col)

    def p_primary_super(self, p):
        "primary : SUPER"
        line, col = self._pos(p, 1)
        p[0] = ast.Super(line=line, col=col)

    def p_primary_lambda_single(self, p):
        "primary : ID ARROW lambda_body"
        line, col = self._pos(p, 1)
        p[0] = ast.Lambda(params=[p[1]], body=p[3], line=line, col=col)

    def p_primary_lambda_empty(self, p):
        "primary : LPAREN RPAREN ARROW lambda_body"
        line, col = self._pos(p, 1)
        p[0] = ast.Lambda(params=[], body=p[4], line=line, col=col)

    def p_primary_lambda_multi(self, p):
        "primary : LPAREN ID COMMA ID lambda_params_tail RPAREN ARROW lambda_body"
        line, col = self._pos(p, 1)
        p[0] = ast.Lambda(
            params=[p[2], p[4], *p[5]],
            body=p[8],
            line=line,
            col=col,
        )

    def p_lambda_params_tail_many(self, p):
        "lambda_params_tail : lambda_params_tail COMMA ID"
        p[0] = p[1] + [p[3]]

    def p_lambda_params_tail_empty(self, p):
        "lambda_params_tail : empty"
        p[0] = []

    def p_lambda_body_expr(self, p):
        "lambda_body : expr"
        p[0] = p[1]

    def p_lambda_body_block(self, p):
        "lambda_body : block"
        p[0] = p[1]

    def p_primary_new_object(self, p):
        "primary : NEW class_ref generic_args_opt LPAREN args_opt RPAREN"
        line, col = self._pos(p, 2)
        p[0] = ast.NewObject(
            class_name=p[2],
            args=p[5],
            type_args=tuple(p[3]),
            line=line,
            col=col,
        )

    def p_primary_new_array(self, p):
        "primary : NEW array_type LBRACKET expr RBRACKET"
        line, col = self._pos(p, 2)
        p[0] = ast.NewArray(
            element_type=p[2],
            size=p[4],
            init=None,
            line=line,
            col=col,
        )

    def p_array_type_primitive(self, p):
        """array_type : INT
                      | DOUBLE
                      | BOOLEAN
                      | CHAR
                      | STRING
                      | LONG
                      | FLOAT
                      | BYTE
                      | SHORT"""
        line, col = self._pos(p, 1)
        p[0] = ast.JavaType(p[1], 0, line, col)

    def p_array_type_class(self, p):
        "array_type : class_ref"
        line, col = self._pos(p, 1)
        p[0] = ast.JavaType(p[1], 0, line, col)

    def p_primary_group(self, p):
        "primary : LPAREN expr RPAREN"
        p[0] = p[2]

    def p_primary_typeid_tail(self, p):
        "primary : TYPEID typeid_tail"
        line, col = self._pos(p, 1)
        kind, value = p[2]
        name = ast.Name(id=p[1], line=line, col=col)
        if kind == "class":
            p[0] = ast.ClassLiteral(
                type=ast.JavaType(p[1], 0, line, col),
                line=line,
                col=col,
            )
        else:
            p[0] = ast.FieldAccess(target=name, name=value, line=line, col=col)

    def p_typeid_tail_class(self, p):
        "typeid_tail : DOT CLASS"
        p[0] = ("class", None)

    def p_typeid_tail_id(self, p):
        "typeid_tail : DOT ID"
        p[0] = ("id", p[2])

    def p_primary_string_tail(self, p):
        "primary : STRING string_tail"
        line, col = self._pos(p, 1)
        kind, value = p[2]
        if kind == "class":
            p[0] = ast.ClassLiteral(
                type=ast.JavaType("String", 0, line, col),
                line=line,
                col=col,
            )
        else:
            target = ast.Name(id="String", line=line, col=col)
            p[0] = ast.FieldAccess(target=target, name=value, line=line, col=col)

    def p_string_tail_class(self, p):
        "string_tail : DOT CLASS"
        p[0] = ("class", None)

    def p_string_tail_id(self, p):
        "string_tail : DOT ID"
        p[0] = ("id", p[2])

    def p_primary_primitive_class(self, p):
        "primary : primitive DOT CLASS"
        line, col = self._pos(p, 1)
        p[0] = ast.ClassLiteral(
            type=ast.JavaType(p[1], 0, line, col),
            line=line,
            col=col,
        )

    def p_primitive(self, p):
        """primitive : INT
                     | DOUBLE
                     | BOOLEAN
                     | CHAR
                     | VOID
                     | LONG
                     | FLOAT
                     | BYTE
                     | SHORT"""
        p[0] = p[1]

    def p_primary_switch_expression(self, p):
        "primary : SWITCH LPAREN expr RPAREN LBRACE switch_body RBRACE"
        line, col = self._pos(p, 1)
        p[0] = ast.SwitchExpression(expr=p[3], cases=p[6], line=line, col=col)

    def p_primary_id(self, p):
        "primary : ID"
        line, col = self._pos(p, 1)
        p[0] = ast.Name(id=p[1], line=line, col=col)

    def p_empty(self, p):
        "empty :"
        p[0] = None

    def p_error(self, p):
        if p is None:
            raise TranspileError("fim de arquivo inesperado")
        raise TranspileError(
            f"erro de sintaxe próximo de {p.value!r}",
            p.lineno,
            self._column(p),
        )
