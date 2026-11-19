# Escopo do subconjunto suportado

Este projeto **não** implementa Java completo. O contrato é o subconjunto
abaixo; o que não está aqui é rejeitado com diagnóstico ou documentado como
limitação.

## Suportado

| Categoria | Itens |
|---|---|
| Estrutura | classes, campos, métodos, construtores, `this`, `new`, `static`, `final`, `public/private/protected` |
| Sintaxe moderna | text blocks (`"""`) e anotações com argumentos (parseadas e ignoradas) |
| Java 21 | source level 21 para o subconjunto; diagnósticos claros para record/sealed/switch expression/etc. |
| `var` | inferência em variáveis locais, `for` clássico e `for-each` |
| Casts/instanceof | casts primitivos e de referência; `instanceof` para classes/interfaces/String/arrays |
| Class literals | `X.class`, `int.class`, `String.class`; `getName`, `getSimpleName`, `isInstance`, `toString` |
| Herança | `extends` simples, `super(...)`, `super.metodo(...)`, override, polimorfismo |
| Interfaces/abstratas | `interface`, `implements` múltiplo, classes abstratas, métodos abstratos, checagem de implementação |
| Exceções | `try/catch/finally`, `throw`, `throws` (lido e ignorado), `RuntimeException`/`Exception` e exceções customizadas |
| `switch` | statement clássico com `case`, `default`, fallthrough e `break`; `int`, `char` e `String` |
| Enums | constantes, tipo, `Enum.CONSTANTE`, comparação e `switch` |
| Lambdas/streams | lambda de expressão, `forEach`, `removeIf`, `filter`, `map`, `collect(Collectors.toList())`, `count`, `anyMatch`/`allMatch`/`noneMatch`, `limit`, `sorted` |
| Tipos | `int`, `double`, `boolean`, `char`, `String`, `T[]`, `void`; `long`/`float`/`byte`/`short` são normalizados |
| Comandos | bloco, declaração local, atribuição, `if/else`, `while`, `do/while`, `for`, `for-each`, `return`, `break`, `continue` |
| Expressões | literais, nomes, `this`, binárias, unárias, atribuição composta, ternário, acesso a campo, chamada, `new` objeto/array, índice |
| Biblioteca | `System.out.print/println`, `String` (principais métodos), `Math`, `Integer/Double`, `String.valueOf`, `ArrayList`/`List`, `HashMap`/`Map`, `HashSet`/`Set`, `Scanner` |
| Arrays | `new T[n]`, `.length`, acesso, `for-each`, valores default |
| Runtime | `JString`, `JSystem`, `JArrayList`, `JHashMap`, `JHashSet`, `JScanner` |
| Projeto | pasta recursiva, autoloader (`bootstrap.php`), `run.php`, `--main` |
| Pacotes/namespaces | `package` → `namespace` PHP; `import` → `use` (incluindo `*`) |

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
| `switch` | só statement clássico; sem `switch`-expression/arrow, sem labels e sem `continue` dentro do switch |
| enums | só constantes; sem campos, métodos, `values()` ou `ordinal()` |
| lambdas/streams | lambda só de expressão, sem method references; `collect` só `Collectors.toList()`; sem streams paralelos/infinitos |
| modo projeto | nomes simples de classe ainda precisam ser únicos (sem aliases/namespaces duplicados); sem `.jar` e sem build incremental |
| nomes PHP | classes com nome de palavra reservada do PHP (ex.: `Var`) precisam ser renomeadas |
| acesso | `private/protected` são emitidos, mas a checagem de acesso não é aplicada |
| `static final` | vira propriedade estática, não `const` |
| `package/import` | viram `namespace`/`use`; imports externos são ignorados |
| `@Override` | lido e ignorado; não vira atributo PHP |
| `char`/`String` | índices são bytes, não code units UTF-16 |

## Fora do escopo (por enquanto)

- Métodos `default`/`static`/`private` em interfaces e constantes de interface.
- Enums com campos/métodos, `values()` e `ordinal()`.
- Genéricos em classes do usuário e tipos boxed.
- Lambdas com bloco, method references, streams paralelos e `Collectors` além de `toList()`.
- Multi-catch, try-with-resources e validação de exceções checadas (`throws` é ignorado).
- Nomes simples duplicados em pacotes diferentes e aliases de `use`.
- Spring/JPA/Lombok e reflection completa (`getMethods`, `getFields` etc.).
- `switch`-expression/arrow, labels e `continue` dentro de `switch`.
- Sobrecarga de métodos (construtores podem ter aridade diferente).
- `LinkedHashMap`/`TreeMap`/`entrySet`, `StringBuilder`, `ArrayList` além dos métodos listados.
- Genéricos: só listas, mapas e sets; sem tipos boxed (`Integer` etc.).
- Classes internas e anônimas.
- Reflection, threads, `synchronized`, `volatile`.
- Records, sealed classes, pattern matching.
- `BigDecimal`, `BigInteger`, datas.
- `>>>` e operadores bit a bit.
- Preservação de comentários no código gerado.

## Estratégias de tradução

| Estratégia | Exemplos |
|---|---|
| Direta | `if`, `while`, `class`, `new`, `this`, `public/private` |
| Lowering | `for-each` → `foreach`; `int/int` → `intdiv`; `.length` → `count`; `s.length()` → `strlen` |
| Runtime shim | `System.out`, `String.valueOf`, `JString::concat`, `JArrayList`, `JHashMap`, `JHashSet`, `JScanner` |
| Rejeitar | threads, reflection, `LinkedHashMap`/`TreeMap`, genéricos fora de coleções |

## Métricas atuais

- Exemplos no diff: **26/26**
- Testes unitários: **100**
- Linhas aproximadas do transpilador: ver `wc -l src/transpilador/*.py`
