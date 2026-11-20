# Transpilador Java → PHP

Transpilador de um **subconjunto de Java (source level 21)** para **PHP 8.1+**, feito com
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
- Exceções: `try/catch/finally`, `throw`, `throws` (ignorado), exceções
  embutidas ou customizadas (`extends RuntimeException`), multi-catch
  (`catch (A | B e)`) e try-with-resources (`try (Recurso r = ...)`).
- `switch` clássico e Java 21: `case`, `default`, fallthrough, `break`,
  arrow (`case 1 ->`) e `switch` expression com `yield`.
- Enums simples (`enum Status { ATIVO, BLOQUEADO }`), acesso `Status.ATIVO`,
  comparação e `switch` sobre enum.
- Records (`record Ponto(int x, int y) { }`): componentes, construtor
  canônico, acessores `x()`/`y()`, métodos, campos/métodos static e
  `implements`.
- Sealed types: `sealed`, `non-sealed` e `permits` em classes/interfaces,
  com checagem de subtipos e `final`/`sealed`/`non-sealed`.
- Lambdas de expressão (`n -> n.length() > 2`) e streams:
  `forEach`, `removeIf`, `filter`, `map`, `collect(Collectors.toList())`,
  `count`, `anyMatch`/`allMatch`/`noneMatch`, `limit` e `sorted`.
- Text blocks (`"""`) e anotações com argumentos (parseadas e ignoradas).
- Casts primitivos/referência (`(int)`, `(char)`, `(Conta)`) e `instanceof`,
  inclusive pattern binding (`obj instanceof Conta c`).
- Class literals (`Conta.class`) com `getName`, `getSimpleName`, `isInstance` e `toString`.
- `package`/`import` → `namespace`/`use` PHP no modo projeto.
- `var` com inferência local e em `for`/`for-each`.
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

Pré-requisitos: Python 3.10+, PHP 8.1+ e JDK 21+ (para os testes diferenciais).

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

## Java 21

O transpilador aceita o subconjunto suportado com **source level Java 21**.
Os testes compilam com `javac --release 21` e rodam no JDK 21.

Isso não significa Java 21 completo. Recursos ainda não suportados produzem
diagnóstico explícito, por exemplo:

```text
public @interface Foo { }      → @interface ainda não é suportado
```

Recursos como `@interface` e pattern matching em `switch` ficam para fases
futuras. `var`, `switch` arrow/expression, pattern `instanceof`,
try-with-resources, multi-catch, records e sealed classes já são suportados.

## Modo projeto (vários arquivos)

```bash
transpilar tests/project/src -o build/project --main Main
php build/project/run.php
```

A pasta de entrada é varrida recursivamente. A saída preserva as subpastas e
gera um autoloader:

```text
build/project/
├── bootstrap.php
├── run.php
├── runtime/
├── Main.php
├── model/
│   ├── Conta.php
│   └── ContaCorrente.php
└── error/
    └── SaldoInsuficienteException.php
```

O `bootstrap.php` registra o autoloader; o `run.php` chama
`Main::main(array_slice($argv, 1))`. Se houver mais de uma classe com `main`,
use `--main NomeDaClasse`.

Limitações do modo projeto: `package`/`import` viram `namespace`/`use`, mas
nomes simples de classe ainda precisam ser únicos (sem aliases/namespaces
duplicados); não há suporte a `.jar`/dependências externas nem build
incremental.

## Testando com seus próprios arquivos

### Um arquivo Java

Crie `Ola.java`:

```java
public class Ola {
    public static void main(String[] args) {
        System.out.println("Olá, PHP!");
    }
}
```

Transpile e execute:

```bash
transpilar Ola.java -o build/Ola
php build/Ola/Ola.php
# Olá, PHP!
```

O diretório de saída fica assim:

```text
build/Ola/
├── Ola.php
└── runtime/
    └── ...
```

Se a classe não tiver `main`, o transpilador gera as classes PHP e não cria
chamada de entrada. Para usar como biblioteca:

```php
require_once 'build/MinhaClasse/bootstrap.php';
```

### Uma pasta de projeto

```bash
transpilar src/ -o build/meu-projeto --main Main
php build/meu-projeto/run.php
```

- `package a.b;` vira `namespace a\b;`.
- `import a.b.C;` vira `use a\b\C;`.
- `bootstrap.php` registra o autoloader.
- `run.php` chama a `main` escolhida.
- Se existir mais de uma classe com `main`, informe `--main NomeDaClasse`.
- Se não existir nenhuma, só o `bootstrap.php` é gerado.

### Exemplos prontos

```bash
transpilar examples/Estoque.java -o build/Estoque
php build/Estoque/Estoque.php

transpilar examples/Funcionarios.java -o build/Funcionarios
php build/Funcionarios/Funcionarios.php
```

### Quando algo não é suportado

O transpilador falha com diagnóstico no formato:

```text
caminho/Arquivo.java:linha:coluna: erro: mensagem
```

Exemplo: `String s = 1;` gera erro de tipo; reflection e APIs de framework
não fazem parte do subconjunto.


## Testes

```bash
make test   # testes unitários (pytest)
make diff   # diferencial: javac/java vs php, comparando stdout
make project # projeto multi-arquivo: javac/java vs run.php
make check  # test + diff + project + lint
make demo   # diferencial só do Banco
```

O teste diferencial compila o `.java`, executa, transpila, roda `php -l`,
executa o PHP e compara a saída. Hoje: **31/31 casos**.

O CI em `.github/workflows/ci.yml` roda `make check` em cada push/PR com
Python, PHP 8.3 e JDK 21.

## Demo integradora

`examples/BancoMenu.java` junta `Scanner`, `ArrayList`, herança, exceção,
`try/catch/finally`, `for-each` e `switch` em um menu de banco:

```bash
transpilar examples/BancoMenu.java -o build/BancoMenu
php build/BancoMenu/BancoMenu.php < examples/BancoMenu.in
```

O caso também está no diff com `BancoMenu.in`.

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

Ainda **não** suportado:
sobrecarga de métodos, classes internas, `LinkedHashMap`/`TreeMap`/`entrySet`,
`StringBuilder`, threads e reflection. Genéricos existem só em
`ArrayList`/`List`, `HashMap`/`Map`, `HashSet`/`Set` e `Stream`, e são
apagados na geração.
Exceções checadas não são validadas: `throws` é lido e ignorado.
Try-with-resources e multi-catch são suportados. `switch`
arrow/expression é suportado; `continue` dentro de `switch` ainda não. Enums têm só
constantes: sem campos, métodos, `values()` ou `ordinal()`. Lambdas só com
corpo de expressão, sem method references; `collect` só aceita
`Collectors.toList()`. Records não geram `equals`/`hashCode`/`toString`
próprios, não aceitam construtor compacto nem record patterns. Sealed é
verificado em compilação e não tem equivalente em runtime no PHP.
Arrays multidimensionais também ficam para depois (`T[][]` no tipo, mas
`new T[n][m]` e inicializadores `{...}` não). Interfaces aceitam só métodos
abstratos: sem `default`, sem constantes e sem métodos `static`/`private`.
A herança é simples: uma superclasse, sem `this(...)` e sem ocultação de
campos. O `Scanner` cobre `next`, `nextInt`, `nextDouble`, `nextLine`,
`hasNext*` e `close`. No modo projeto, `package`/`import` viram
`namespace`/`use`; nomes simples de classe ainda precisam ser únicos e não há
suporte a `.jar`. Nomes de classe iguais a palavras reservadas do PHP (ex.:
`Var`) precisam ser renomeados. Projetos reais com Spring/JPA/Lombok ainda
não são suportados.

Detalhes e a matriz completa estão em [`docs/escopo.md`](docs/escopo.md).

## Status

- [x] Lexer/parser do subconjunto
- [x] AST + análise semântica básica
- [x] Codegen PHP + runtime
- [x] 31 programas de exemplo passando no diff
- [x] 134 testes unitários
- [x] Herança simples (`extends`, `super`, override, polimorfismo)
- [x] Interfaces e classes abstratas
- [x] `ArrayList`/`List` + `Scanner`
- [x] `HashMap`/`HashSet`
- [x] Exceções (`try/catch/finally`, `throw`, customizadas)
- [x] `switch` clássico
- [x] Demo integradora (`BancoMenu`)
- [x] Enums simples
- [x] Lambdas/streams
- [x] Modo projeto multi-arquivo (`bootstrap.php` + `run.php`)
- [x] Text blocks + anotações com argumentos
- [x] Casts e `instanceof`
- [x] Class literals (`X.class`)
- [x] `package`/`import` → namespace/use PHP
- [x] Source level Java 21 + diagnósticos de recursos não suportados
- [x] `var` (locals, `for` e `for-each`)
- [x] `switch` arrow/expression + `yield`
- [x] Pattern `instanceof` (`obj instanceof Conta c`)
- [x] Try-with-resources e multi-catch
- [x] Records (componentes, construtor canônico e acessores)
- [x] Sealed/non-sealed/permits
- [ ] Relatório final e slides
