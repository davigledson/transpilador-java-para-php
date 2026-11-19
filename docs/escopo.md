# Escopo do subconjunto suportado

Este projeto **não** implementa Java completo. O contrato é o subconjunto
abaixo; o que não está aqui é rejeitado com diagnóstico ou documentado como
limitação.

## Suportado

| Categoria | Itens |
|---|---|
| Estrutura | classes, campos, métodos, construtores, `this`, `new`, `static`, `final`, `public/private/protected` |
| Herança | `extends` simples, `super(...)`, `super.metodo(...)`, override, polimorfismo |
| Interfaces/abstratas | `interface`, `implements` múltiplo, classes abstratas, métodos abstratos, checagem de implementação |
| Exceções | `try/catch/finally`, `throw`, `throws` (lido e ignorado), `RuntimeException`/`Exception` e exceções customizadas |
| Tipos | `int`, `double`, `boolean`, `char`, `String`, `T[]`, `void`; `long`/`float`/`byte`/`short` são normalizados |
| Comandos | bloco, declaração local, atribuição, `if/else`, `while`, `do/while`, `for`, `for-each`, `return`, `break`, `continue` |
| Expressões | literais, nomes, `this`, binárias, unárias, atribuição composta, ternário, acesso a campo, chamada, `new` objeto/array, índice |
| Biblioteca | `System.out.print/println`, `String` (principais métodos), `Math`, `Integer/Double`, `String.valueOf`, `ArrayList`/`List`, `HashMap`/`Map`, `HashSet`/`Set`, `Scanner` |
| Arrays | `new T[n]`, `.length`, acesso, `for-each`, valores default |
| Runtime | `JString`, `JSystem`, `JArrayList`, `JHashMap`, `JHashSet`, `JScanner` |

## Parcial / com ressalvas

| Item | Ressalva |
|---|---|
| `char` | vira `string` de 1 caractere; aritmética usa `ord()`; sem semântica UTF-16 |
| `double` | formatação de `println` é aproximada; casos exóticos podem divergir |
| arrays | sem bounds check explícito; PHP emite warning em índice inválido |
| arrays multidimensionais | `T[][]` é aceito no tipo, mas `new T[n][m]` e inicializadores `{...}` não são implementados |
| herança | uma superclasse; sem `this(...)`, sem ocultação de campos; construtor deve chamar `super(...)` quando o pai não tem construtor sem argumentos |
| interfaces | só métodos abstratos; sem `default`, constantes, métodos `static`/`private`; interface pode estender uma interface |
| classes abstratas | métodos abstratos e concretos; não podem ser instanciadas |
| `ArrayList`/`List` | genéricos apagados; métodos `add`, `addAt`, `get`, `set`, `size`, `isEmpty`, `contains`, `remove`, `clear`, `indexOf`, `toString`; `contains`/`remove` usam igualdade estrita do PHP |
| `HashMap`/`Map` | `put`, `get`, `containsKey`, `containsValue`, `remove`, `size`, `isEmpty`, `clear`, `keySet`, `values`, `toString`; chaves escalares por valor, objetos por identidade |
| `HashSet`/`Set` | `add`, `contains`, `remove`, `size`, `isEmpty`, `clear`, `toString`, `for-each`; igualdade estrita do PHP |
| `Scanner` | `next`, `nextInt`, `nextDouble`, `nextLine`, `hasNext*`, `close`; lê de stdin |
| exceções | sem checagem de exceções checadas, sem multi-catch e sem try-with-resources; `printStackTrace` vai para stderr |
| acesso | `private/protected` são emitidos, mas a checagem de acesso não é aplicada |
| `static final` | vira propriedade estática, não `const` |
| `package/import` | lidos e ignorados; todas as classes ficam no namespace global |
| `@Override` | lido e ignorado; não vira atributo PHP |
| `char`/`String` | índices são bytes, não code units UTF-16 |

## Fora do escopo (por enquanto)

- Métodos `default`/`static`/`private` em interfaces e constantes de interface.
- Enums.
- Genéricos em classes do usuário e tipos boxed.
- Lambdas, method references, streams.
- Multi-catch, try-with-resources e validação de exceções checadas (`throws` é ignorado).
- `switch`, `case`, `default`.
- Sobrecarga de métodos (construtores podem ter aridade diferente).
- `LinkedHashMap`/`TreeMap`/`entrySet`, `StringBuilder`, `ArrayList` além dos métodos listados.
- Genéricos: só listas, mapas e sets; sem tipos boxed (`Integer` etc.).
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
| Runtime shim | `System.out`, `String.valueOf`, `JString::concat`, `JArrayList`, `JHashMap`, `JHashSet`, `JScanner` |
| Rejeitar | threads, reflection, `LinkedHashMap`/`TreeMap`, genéricos fora de coleções |

## Métricas atuais

- Exemplos no diff: **16/16**
- Testes unitários: **55**
- Linhas aproximadas do transpilador: ver `wc -l src/transpilador/*.py`
