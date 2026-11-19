# Gramática do subconjunto

A gramática é implementada em `src/transpilador/parser.py` com PLY/yacc
(LALR(1)). Abaixo, a versão em EBNF que serve de contrato.

```ebnf
program        := package_opt imports_opt top_decl_list
package_opt    := "package" dotted_name ";" | ε
imports_opt    := { "import" dotted_name ";" }
dotted_name    := dotted_part { "." dotted_part }
dotted_part    := ID | TYPEID

top_decl_list  := top_decl { top_decl }
top_decl       := class_decl | interface_decl
class_decl     := modifiers "class" TYPEID extends_opt implements_opt
                  "{" class_body "}"
interface_decl := modifiers "interface" TYPEID extends_opt
                  "{" interface_body "}"
extends_opt    := "extends" class_ref | ε
implements_opt := "implements" name_list | ε
name_list      := ID { "," ID }
class_ref      := ID | TYPEID

modifiers      := { modifier }
modifier       := "public" | "private" | "protected" | "static" | "final"
                | "abstract" | annotation
annotation     := "@" ID

class_body     := { member }
member         := modifiers member_rest
member_rest    := TYPEID "(" params_opt ")" throws_opt block  (* construtor *)
                | type ID member_tail
member_tail    := "(" params_opt ")" throws_opt block         (* método *)
                | "(" params_opt ")" throws_opt ";"           (* método abstrato *)
                | "=" expr ";"                               (* campo *)
                | ";"                                        (* campo sem init *)

interface_body := { interface_member }
interface_member := modifiers type ID "(" params_opt ")" throws_opt ";"
throws_opt     := "throws" name_list | ε

params_opt     := params | ε
params         := param { "," param }
param          := type ID
type           := ( "int" | "double" | "boolean" | "char" | "String"
                  | "void" | "long" | "float" | "byte" | "short"
                  | TYPEID generic_args_opt ) { "[" "]" }
generic_args_opt := "<" generic_args ">" | "<" ">" | ε
generic_args   := type { "," type }

stmt           := block
                | "if" "(" expr ")" stmt [ "else" stmt ]
                | "while" "(" expr ")" stmt
                | "do" stmt "while" "(" expr ")" ";"
                | "for" "(" for_header ")" stmt
                | "try" block catch_list [ "finally" block ]
                | "try" block "finally" block
                | "throw" expr ";"
                | "return" [ expr ] ";"
                | "break" ";"
                | "continue" ";"
                | local_decl ";"
                | expr ";"
                | ";"
catch_list     := catch_clause { catch_clause }
catch_clause   := "catch" "(" type ID ")" block
block          := "{" { stmt } "}"
local_decl     := type ID [ "=" expr ]
for_header     := for_init ";" [ expr ] ";" [ expr ]         (* clássico *)
                | type ID ":" expr                           (* for-each *)
for_init       := local_decl | expr | ε

expr           := assignment
assignment     := ternary [ ( "=" | "+=" | "-=" | "*=" | "/=" ) assignment ]
ternary        := or_expr [ "?" expr ":" ternary ]
or_expr        := and_expr { "||" and_expr }
and_expr       := equality { "&&" equality }
equality       := relational { ( "==" | "!=" ) relational }
relational     := additive { ( "<" | "<=" | ">" | ">=" ) additive }
additive       := multiplicative { ( "+" | "-" ) multiplicative }
multiplicative := unary { ( "*" | "/" | "%" ) unary }
unary          := ( "!" | "-" | "+" | "++" | "--" ) unary | postfix
postfix        := primary { "." ID | "(" args_opt ")" | "[" expr "]"
                          | "++" | "--" }
primary        := INT_LIT | DOUBLE_LIT | STRING_LIT | CHAR_LIT
                | "true" | "false" | "null" | "this" | "super"
                | "new" class_ref generic_args_opt "(" args_opt ")"
                | "new" array_type "[" expr "]"
                | "(" expr ")"
                | ID | TYPEID "." ID | STRING "." ID
array_type     := ( "int" | "double" | "boolean" | "char" | "String"
                  | "long" | "float" | "byte" | "short" | class_ref )
args_opt       := args | ε
args           := expr { "," expr }
```

## Por que existe `TYPEID`

Em Java, `Conta c` (declaração) e `conta[i]` (acesso a array) começam com um
identificador. Um parser LALR(1) ingênuo confunde `T[]` com indexação.

Solução: antes de parsear, uma primeira passada descobre os nomes de classes
declaradas (`collect_type_names`) e o lexer marca esses nomes como `TYPEID`.
Assim:

- `TYPEID ID` → declaração de variável de tipo de classe;
- `ID "["` → acesso a array.

Limitação conhecida: uma variável local com o mesmo nome de uma classe é
tratada como `TYPEID` e pode falhar. É um caso raro e documentado.

## Conflitos e decisões

| Situação | Decisão |
|---|---|
| `else` pendente | precedência `ELSE` (shift) |
| cast `(int) x` | não implementado nesta versão |
| `new T[n]` vs `new T(...)` | lookahead `[` vs `(` |
| construtor vs método | `TYPEID "("` vs `type ID "("` |
| `for` clássico vs for-each | lookahead `;` vs `:` |
| genéricos | `ArrayList`/`List`, `HashMap`/`Map`, `HashSet`/`Set`; apagados no PHP |
| arrays `T[]` | suportados via `TYPEID` + `[]` |
