# Reuso de código e fontes

A disciplina permite bibliotecas e código aberto **com atribuição**. Este
documento registra o que foi usado e sob qual licença.

## Dependências de software

| Fonte | Licença | Uso |
|---|---|---|
| [PLY (Python Lex-Yacc)](https://github.com/dabeaz/ply) | BSD-3-Clause | Biblioteca de lexer/parser (`pip install ply`) |
| [pytest](https://pytest.org) | MIT | Testes unitários |
| [PHP](https://www.php.net/) | PHP License | Runtime de destino |

## Referências consultadas (sem cópia de código)

| Fonte | Licença | Uso |
|---|---|---|
| [Java Language Specification](https://docs.oracle.com/javase/specs/) | Copyright Oracle | Referência de sintaxe/semântica; gramática adaptada e parafraseada |
| [ANTLR grammars-v4 – Java](https://github.com/antlr/grammars-v4/tree/master/java) | BSD-3-Clause (verificar `LICENSE`) | Referência de produções para o subconjunto |
| [JavaParser](https://github.com/javaparser/javaparser) | Apache-2.0 | Inspiração para nomes/estrutura de AST |
| [Spoon](https://github.com/INRIA/spoon) | CeCILL-C (copyleft) | Apenas ideias; nenhum código copiado |
| [bafolts/java2php](https://github.com/bafolts/java2php) | Sem licença explícita | Apenas leitura de ideias; **nenhum código copiado** |
| [Documentação do PHP](https://www.php.net/manual/) | CC BY-SA (texto) | Referência de funções e semântica; runtime escrito neste projeto |

## O que é autoral

- `src/transpilador/lexer.py`: tokens, escapes e a passada `TYPEID`.
- `src/transpilador/parser.py`: gramática PLY do subconjunto e AST.
- `src/transpilador/ast.py`: nós e utilitários.
- `src/transpilador/semantico.py`: tabela de símbolos, escopos, tipos e
  resolução de chamadas.
- `src/transpilador/codegen.py`: emissor PHP e regras de lowering.
- `runtime/php/`: `JString`, `JSystem`, `JCast`, `JClass`, `JArrayList`, `JStream`, `JHashMap`, `JHashSet`, `JScanner` e `bootstrap`.
- `scripts/diff_test.py`: harness diferencial.
- Exemplos e testes.

## Licenças e citação

Se algum trecho for adaptado no futuro, registrar aqui: URL, autor, licença,
trecho e modificação. Para o relatório, citar PLY, a JLS e as referências
acima na seção “Trabalhos relacionados”/“Ferramentas utilizadas”.
