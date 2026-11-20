# Escopo do subconjunto suportado

Este projeto **não** implementa Java completo. O contrato é o subconjunto
abaixo; o que não está aqui é rejeitado com diagnóstico ou documentado como
limitação.

## Suportado

| Categoria | Itens |
|---|---|
| Estrutura | classes, campos, métodos, construtores, `this`, `new`, `static`, `final`, `public/private/protected` |
| Sintaxe moderna | text blocks (`"""`) e anotações com argumentos (parseadas e ignoradas) |
| Java 21 | source level 21 para o subconjunto; diagnósticos claros para sealed/`@interface`/etc. |
| Records | componentes, construtor canônico, acessores, métodos, static e `implements` |
| `var` | inferência em variáveis locais, `for` clássico e `for-each` |
| `switch` 21 | statement arrow, switch expression e `yield` |
| Casts/instanceof | casts primitivos e de referência; `instanceof` para classes/interfaces/String/arrays, com pattern binding |
| Class literals | `X.class`, `int.class`, `String.class`; `getName`, `getSimpleName`, `isInstance`, `toString` |
| Herança | `extends` simples, `super(...)`, `super.metodo(...)`, override, polimorfismo |
| Interfaces/abstratas | `interface`, `implements` múltiplo, classes abstratas, métodos abstratos, checagem de implementação |
| Exceções | `try/catch/finally`, `throw`, `throws` (lido e ignorado), `RuntimeException`/`Exception`, exceções customizadas, multi-catch e try-with-resources |
| `switch` | statement clássico + arrow, switch expression, `default`, fallthrough e `yield`; `int`, `char`, `String` e enum |
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
| exceções | sem checagem de exceções checadas; `printStackTrace` vai para stderr |
| try-with-resources | um ou mais recursos (inclusive `var`), fechamento em ordem inversa antes de `catch`/`finally` |
| multi-catch | `catch (A \| B e)` com tipos de exceção não relacionados; o parâmetro recebe o supertipo comum |
| `switch` | `continue` dentro do switch, labels e pattern matching em `switch` |
| enums | só constantes; sem campos, métodos, `values()` ou `ordinal()` |
| records | sem `equals`/`hashCode`/`toString` gerados, sem construtor compacto nem record patterns; campos de instância extras são proibidos |
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
- Validação de exceções checadas (`throws` é ignorado) e exceções suprimidas.
- Nomes simples duplicados em pacotes diferentes e aliases de `use`.
- Spring/JPA/Lombok e reflection completa (`getMethods`, `getFields` etc.).
- `continue` dentro de `switch`, labels e pattern matching em `switch`.
- Sobrecarga de métodos (construtores podem ter aridade diferente).
- `LinkedHashMap`/`TreeMap`/`entrySet`, `StringBuilder`, `ArrayList` além dos métodos listados.
- Genéricos: só listas, mapas e sets; sem tipos boxed (`Integer` etc.).
- Classes internas e anônimas.
- Reflection, threads, `synchronized`, `volatile`.
- Sealed classes e pattern matching em `switch`.
- Record patterns, construtor compacto e `equals`/`hashCode`/`toString` automáticos.
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

- Exemplos no diff: **30/30**
- Testes unitários: **123**
- Linhas aproximadas do transpilador: ver `wc -l src/transpilador/*.py`
