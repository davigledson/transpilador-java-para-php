# Transpilador Java → PHP

Transpilador de um **subconjunto de Java 8** para **PHP 8.1+**, feito com
[PLY](https://github.com/dabeaz/ply) (lex/yacc em Python). O projeto nasceu
como trabalho de Compiladores/Paradigmas e tem um objetivo deliberadamente
recortado: traduzir programas pequenos de forma **correta e testável**, em vez
de prometer Java inteiro.

## O que já funciona

- Classes, campos, métodos, construtores, `this`, `new`, `static`,
  `public/private/protected` e `static final`.
- Herança simples: `extends`, `super(...)`, `super.metodo(...)`, override,
  polimorfismo e arrays de supertipo.
- Interfaces (`interface`/`implements`), classes abstratas e métodos abstratos,
  com checagem de implementação nas classes concretas.
- `ArrayList`/`List` com genéricos apagados (`ArrayList<String>`,
  `new ArrayList<>()`) e `Scanner` para `stdin`.
- `HashMap`/`Map` e `HashSet`/`Set` com genéricos apagados.
- Exceções: `try/catch/finally`, `throw`, `throws` (ignorado) e exceções
  embutidas ou customizadas (`extends RuntimeException`).
- Tipos `int`, `double`, `boolean`, `char`, `String`, arrays (`T[]`) e `void`.
- `if/else`, `while`, `do/while`, `for`, `for-each`, `return`,
  `break/continue` e blocos.
- Operadores aritméticos, relacionais, lógicos, atribuição composta,
  `++/--` e ternário.
- `System.out.print/println`.
- Métodos de `String` (`length`, `charAt`, `substring`, `equals`,
  `toUpperCase`, `toLowerCase`, `trim`, `indexOf`, `contains`,
  `startsWith`, `endsWith`, `replace`, `split`, `isEmpty`, `compareTo`).
- `Math.*`, `Integer.parseInt/toString`, `Double.parseDouble/toString`,
  `String.valueOf`.
- Arrays com `.length`, `new T[n]`, acesso por índice e `for-each`.
- Runtime PHP que preserva detalhes do Java: `null` vira `"null"`,
  `true/false` viram `"true"/"false"`, `1.0` continua `"1.0"`, divisão
  inteira usa `intdiv`, concatenação usa `JString::concat`.

## Como rodar

Pré-requisitos: Python 3.10+, PHP 8.1+ e JDK 17+ (para os testes diferenciais).

```bash
make install
source .venv/bin/activate
```

Transpile um arquivo:

```bash
transpilar examples/Banco.java -o build/Banco
php build/Banco/Banco.php
```

Ou:

```bash
transpilar examples/Conta.java -o build/Conta
php build/Conta/Conta.php
```

Ver a AST:

```bash
transpilar examples/Hello.java --dump-ast
```

Ver o PHP gerado sem escrever arquivo:

```bash
transpilar examples/Banco.java --dump-php
```

## Testes

```bash
make test   # testes unitários (pytest)
make diff   # diferencial: javac/java vs php, comparando stdout
make demo   # diferencial só do Banco
```

O teste diferencial compila o `.java`, executa, transpila, roda `php -l`,
executa o PHP e compara a saída. Hoje: **16/16 casos**.

## Exemplo

`examples/Banco.java`:

```java
public class Banco {
    static final int TOTAL = 3;

    public static void main(String[] args) {
        Conta[] contas = new Conta[TOTAL];
        contas[0] = new Conta("Ana", 100.0);
        // ...
        for (int i = 0; i < contas.length; i++) {
            contas[i].depositar(10.0);
            System.out.println(contas[i].getTitular() + ": " + contas[i].getSaldo());
        }
    }
}
```

Trecho gerado:

```php
class Banco
{
    public static int $TOTAL = 3;

    public static function main(?array $args): void
    {
        $contas = array_fill(0, self::$TOTAL, null);
        // ...
        for ($i = 0; ($i < count($contas)); $i++) {
            $contas[$i]->depositar(10.0);
            JSystem::println(JString::concat(
                JString::concat($contas[$i]->getTitular(), ": "),
                $contas[$i]->getSaldo()
            ));
        }
    }
}
```

## Arquitetura

```text
.java
  │  lexer.py (PLY lex)
  ▼
tokens ──► parser.py (PLY yacc + AST)
  │
  ▼
semantico.py (tabela de símbolos, escopos, tipos)
  │
  ▼
codegen.py (emitter PHP)
  │
  ▼
.php + runtime/php/
```

A **AST tipada é o IR** do projeto. Não há TAC nem otimizações nesta versão.

## Estrutura

```text
src/transpilador/   lexer, parser, AST, semântica, codegen e CLI
runtime/php/        JString, JSystem e bootstrap
examples/           programas Java de demonstração
tests/unit/         testes de lexer/parser/semântica/codegen
tests/corpus/java/  cópia dos exemplos usados no diff
scripts/diff_test.py
docs/               escopo, gramática, decisões, reuso e relatório
```

## Limitações atuais

Ainda **não** suportado: enums, lambdas/streams, `switch`,
sobrecarga de métodos, pacotes/namespaces (são lidos e ignorados), classes
internas, `LinkedHashMap`/`TreeMap`/`entrySet`, `StringBuilder`, threads e
reflection. Genéricos existem só em `ArrayList`/`List`, `HashMap`/`Map` e
`HashSet`/`Set`, e são apagados na geração.
Exceções checadas não são validadas: `throws` é lido e ignorado; não há
multi-catch nem try-with-resources.
Arrays multidimensionais também ficam para depois (`T[][]` no tipo, mas
`new T[n][m]` e inicializadores `{...}` não). Interfaces aceitam só métodos
abstratos: sem `default`, sem constantes e sem métodos `static`/`private`.
A herança é simples: uma superclasse, sem `this(...)` e sem ocultação de
campos. O `Scanner` cobre `next`, `nextInt`, `nextDouble`, `nextLine`,
`hasNext*` e `close`.

Detalhes e a matriz completa estão em [`docs/escopo.md`](docs/escopo.md).

## Status

- [x] Lexer/parser do subconjunto
- [x] AST + análise semântica básica
- [x] Codegen PHP + runtime
- [x] 16 programas de exemplo passando no diff
- [x] 55 testes unitários
- [x] Herança simples (`extends`, `super`, override, polimorfismo)
- [x] Interfaces e classes abstratas
- [x] `ArrayList`/`List` + `Scanner`
- [x] `HashMap`/`HashSet`
- [x] Exceções (`try/catch/finally`, `throw`, customizadas)
- [ ] Lambdas, enums, `switch`
- [ ] Relatório final e slides
