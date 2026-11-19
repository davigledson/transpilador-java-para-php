# Relatório (esqueleto)

## 1. Introdução
- Motivação: executar programas Java em ambiente PHP.
- Objetivo: transpilador de um subconjunto de Java 8 para PHP 8.
- Justificativa do recorte.

## 2. Fundamentação
- Compilação e transpilação fonte→fonte.
- Fases: léxica, sintática, semântica, geração.
- LALR(1) e PLY.
- Java vs PHP: tipagem, strings, arrays, inteiros, modelo de execução.

## 3. Escopo e gramática
- Subconjunto suportado (ver `docs/escopo.md`).
- EBNF (ver `docs/gramatica.md`).
- Estratégia `TYPEID` para declaração vs indexação.

## 4. Implementação
- Lexer: tokens, literais, comentários, linha/coluna.
- Parser: gramática, precedência, conflitos resolvidos.
- AST: nós e visitor implícito via `isinstance`.
- Semântica: tabela de símbolos, escopos, tipos, chamadas.
- Codegen: mapeamento de tipos, lowering, runtime.
- Runtime PHP: `JString`, `JSystem`.

## 5. Testes e resultados
- Testes unitários: 20.
- Teste diferencial: 8/8 exemplos.
- Tabela de casos e saídas.
- Limitações observadas.

## 6. Limitações e trabalhos futuros
- Herança/interfaces, coleções, exceções, lambdas.
- Melhor tratamento de `char`/Unicode, bounds check, formatação de double.
- Otimizações e IR explícito.

## 7. Conclusão

## Apêndices
- Gramática completa.
- Exemplos de código Java/PHP.
- Registro de reuso (`docs/reuso.md`).
