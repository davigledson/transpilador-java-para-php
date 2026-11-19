# Escopo do subconjunto suportado

Este projeto **não** implementa Java completo. O contrato é o subconjunto
abaixo; o que não está aqui é rejeitado com diagnóstico ou documentado como
limitação.

## Suportado

| Categoria | Itens |
|---|---|
| Estrutura | classes, campos, métodos, construtores, `this`, `new`, `static`, `final`, `public/private/protected` |
| Tipos | `int`, `double`, `boolean`, `char`, `String`, `T[]`, `void`; `long`/`float`/`byte`/`short` são normalizados |
| Comandos | bloco, declaração local, atribuição, `if/else`, `while`, `do/while`, `for`, `for-each`, `return`, `break`, `continue` |
| Expressões | literais, nomes, `this`, binárias, unárias, atribuição composta, ternário, acesso a campo, chamada, `new` objeto/array, índice |
| Biblioteca | `System.out.print/println`, `String` (principais métodos), `Math`, `Integer/Double`, `String.valueOf` |
| Arrays | `new T[n]`, `.length`, acesso, `for-each`, valores default |
| Runtime | `JString`, `JSystem` (conversão de `null`, booleanos, `double`, concatenação) |

## Parcial / com ressalvas

| Item | Ressalva |
|---|---|
| `char` | vira `string` de 1 caractere; aritmética usa `ord()`; sem semântica UTF-16 |
| `double` | formatação de `println` é aproximada; casos exóticos podem divergir |
| arrays | sem bounds check explícito; PHP emite warning em índice inválido |
| arrays multidimensionais | `T[][]` é aceito no tipo, mas `new T[n][m]` e inicializadores `{...}` não são implementados |
| acesso | `private/protected` são emitidos, mas a checagem de acesso não é aplicada |
| `static final` | vira propriedade estática, não `const` |
| `package/import` | lidos e ignorados; todas as classes ficam no namespace global |
| `@Override` | lido e ignorado; não vira atributo PHP |
| `char`/`String` | índices são bytes, não code units UTF-16 |

## Fora do escopo (por enquanto)

- Herança (`extends`), interfaces (`implements`), classes abstratas.
- Enums.
- Genéricos.
- Lambdas, method references, streams.
- Exceções (`try/catch/finally/throw`).
- `switch`, `case`, `default`.
- Sobrecarga de métodos (construtores podem ter aridade diferente).
- Coleções (`ArrayList`, `HashMap`, `HashSet`), `Scanner`, `StringBuilder`.
- Classes internas e anônimas.
- Reflection, threads, `synchronized`, `volatile`.
- Records, sealed classes, pattern matching.
- `BigDecimal`, `BigInteger`, datas.
- Casts de classe, `instanceof`, `>>>`, operadores bit a bit.
- Preservação de comentários no código gerado.

## Estratégias de tradução

| Estratégia | Exemplos |
|---|---|
| Direta | `if`, `while`, `class`, `new`, `this`, `public/private` |
| Lowering | `for-each` → `foreach`; `int/int` → `intdiv`; `.length` → `count`; `s.length()` → `strlen` |
| Runtime shim | `System.out`, `String.valueOf`, `JString::concat`, `JString::charAt` |
| Rejeitar | threads, reflection, herança nesta versão, genéricos |

## Métricas atuais

- Exemplos no diff: **8/8**
- Testes unitários: **20**
- Linhas aproximadas do transpilador: ver `wc -l src/transpilador/*.py`
