# Transpilador Java → PHP

**Disciplina:** Compiladores e Paradigmas de Programação<br>
**Autor(es):** ______________________________<br>
**Data:** novembro de 2026

## Resumo

Este trabalho apresenta um transpilador de um subconjunto de Java para PHP,
implementado em Python com a biblioteca PLY (lex/yacc). O objetivo não é
traduzir Java completo, mas construir um pipeline real de compilação —
análise léxica, sintática, semântica e geração de código — capaz de traduzir
programas de console e pequenos projetos orientados a objetos, com testes
diferenciais executando o mesmo programa em Java e em PHP.

O subconjunto cobre classes, herança, interfaces, classes abstratas, enums,
records, exceções, `switch`, `ArrayList`/`HashMap`/`HashSet`, `Scanner`,
lambdas, streams, casts, `instanceof` (com pattern binding), class literals,
text blocks, anotações com argumentos e `package`/`import` mapeados para
namespace/use do PHP. O resultado é validado por 123 testes unitários,
30 programas no teste
diferencial Java×PHP e um teste de projeto multi-arquivo, todos executados
por `make check` e pelo CI.

## 1. Introdução

### 1.1 Contexto e motivação

Java e PHP ocupam espaços diferentes: Java é uma linguagem estática,
nominal e executada na JVM; PHP é uma linguagem dinâmica/gradual, muito usada
em hospedagem web e execução por requisição. Traduzir código Java para PHP
não é apenas trocar palavras-chave: exige preservar semântica onde as
linguagens coincidem e decidir explicitamente o que fazer onde elas divergem.

O projeto foi construído como um **transpilador fonte→fonte**: a entrada é
um arquivo `.java`; a saída é um arquivo `.php` executável, acompanhado de
uma pequena biblioteca de runtime que emula partes da biblioteca Java.

### 1.2 Objetivos

- Definir um subconjunto de Java com escopo viável.
- Implementar as fases clássicas de compilação.
- Gerar PHP legível e executável.
- Preservar semântica nos casos suportados.
- Validar com testes diferenciais Java×PHP.
- Documentar decisões, limitações e reuso de ferramentas.

### 1.3 Justificativa do recorte

Java completo é inviável em um semestre e desnecessário para demonstrar os
conceitos. A estratégia adotada foi um **corte vertical**: implementar um
subconjunto pequeno, porém completo, de ponta a ponta, e ampliá-lo em fases.
Assim, cada fase tem um exemplo executável, testes e documentação.

## 2. Fundamentação

### 2.1 Transpilação e fases de compilação

Transpilação é uma forma de compilação fonte→fonte. O pipeline implementado
segue as fases clássicas:

```text
código Java
  → análise léxica (tokens)
  → análise sintática (AST)
  → análise semântica (símbolos, escopos, tipos)
  → lowering/desugaring
  → geração de código PHP
  → runtime PHP
```

A **AST tipada** é usada como representação intermediária (IR) do projeto.
Não foi implementada uma IR de três endereços: para um transpilador
fonte→fonte, a AST anotada é suficiente e reduz o custo de implementação.

### 2.2 LALR(1) e PLY

O parser foi gerado com PLY, que implementa LALR(1) no estilo lex/yacc. A
gramática foi escrita para um subconjunto de Java, com decisões específicas
para evitar ambiguidades:

- `else` pendente resolvido por precedência;
- `new T[n]` vs `new T(...)` por lookahead;
- construtor vs método por lookahead;
- `for` clássico vs `for-each` por lookahead;
- declaração de variável vs indexação de array por uma passada prévia que
  marca nomes de classes como `TYPEID`.

### 2.3 Java vs PHP: paradigmas e lacunas

| Aspecto | Java | PHP | Consequência |
|---|---|---|---|
| Tipagem | estática, nominal | dinâmica/gradual | análise semântica precisa dirigir o codegen |
| Herança | uma classe + interfaces | uma classe + interfaces | mapeamento direto |
| Sobrecarga | sim | não | sobrecarga de usuário é rejeitada |
| Genéricos | apagados na JVM | não existem | apagados na geração; usados na checagem |
| Strings | UTF-16, imutáveis | bytes | `strlen`, `substr`, `ord`/`chr` |
| Inteiros | 32/64 bits com wrap | 64 bits, overflow vira float | `intdiv`; overflow não modelado |
| Arrays | fixos, default, bounds check | mapas dinâmicos | `array_fill`, `count`, sem bounds check |
| Exceções | checadas | não checadas | `throws` ignorado |
| Execução | `main` + JVM | script/requisição | `run.php`/entrypoint |
| Concorrência | threads | shared-nothing | fora do escopo |

As lacunas foram tratadas com quatro estratégias:

1. **Tradução direta**: `if`, `while`, `class`, `new`, `this`.
2. **Lowering**: `for-each` → `foreach`; `int/int` → `intdiv`; `.length` → `count`.
3. **Runtime shim**: `JString`, `JSystem`, `JArrayList`, `JHashMap`,
   `JHashSet`, `JScanner`, `JStream`, `JCast`, `JClass`.
4. **Rejeição explícita**: threads, reflection, frameworks, recursos não
   suportados.

## 3. Escopo

### 3.1 Suportado

| Categoria | Itens |
|---|---|
| Estrutura | classes, campos, métodos, construtores, `this`, `new`, `static`, `final`, visibilidade |
| Herança | `extends` simples, `super(...)`, `super.metodo(...)`, override, polimorfismo |
| Interfaces/abstratas | `interface`, `implements` múltiplo, classes abstratas, métodos abstratos |
| Exceções | `try/catch/finally`, `throw`, `throws` ignorado, exceções embutidas e customizadas, multi-catch e try-with-resources |
| Controle | `if/else`, `while`, `do/while`, `for`, `for-each`, `switch`, `break`, `continue` |
| Enums | constantes, `Enum.CONSTANTE`, comparação, `switch` |
| Records | componentes, construtor canônico, acessores, métodos, static e `implements` |
| Coleções | `ArrayList`/`List`, `HashMap`/`Map`, `HashSet`/`Set` |
| Funcional | lambdas de expressão, `filter`, `map`, `forEach`, `removeIf`, `collect(Collectors.toList())`, `count`, `anyMatch` etc. |
| Tipos | `int`, `double`, `boolean`, `char`, `String`, arrays, `void`; `long`/`float`/`byte`/`short` normalizados |
| Sintaxe moderna | text blocks, anotações com argumentos (ignoradas), casts, `instanceof` com pattern, class literals |
| Projeto | pasta recursiva, `package` → namespace, `import` → `use`, autoloader, `run.php` |

### 3.2 Fora do escopo

- Semântica de framework: Spring, JPA, Lombok, servlets, injeção de dependência.
- Reflection completa (`getMethods`, `getFields`, `newInstance`).
- Threads, `synchronized`, `volatile`, concorrência.
- `.jar`/dependências externas, build incremental.
- Sobrecarga de métodos do usuário.
- Validação de exceções checadas (`throws` é ignorado) e exceções suprimidas.
- `default`/`static`/`private` em interfaces e constantes de interface.
- Genéricos em classes do usuário, wildcards e tipos boxed.
- Classes internas/anônimas, sealed classes, `@interface`, record patterns e construtor compacto de record.
- Fidelidade total de Unicode, overflow de inteiros e identidade de arrays/strings.

## 4. Gramática e front-end

A gramática completa está em [`docs/gramatica.md`](gramatica.md). Um recorte:

```ebnf
program        := package_opt imports_opt top_decl_list
top_decl       := class_decl | interface_decl | enum_decl
class_decl     := modifiers "class" TYPEID extends_opt implements_opt
                  "{" class_body "}"
stmt           := block | if | while | do_while | for
                | try | throw | switch
                | "return" [ expr ] ";"
                | local_decl ";" | expr ";" | ";"
expr           := assignment
assignment     := ternary [ ("=" | "+=" | "-=" | "*=" | "/=") assignment ]
ternary        := or_expr [ "?" expr ":" ternary ]
...
primary        := literal | "this" | "super"
                | "new" class_ref generic_args_opt "(" args_opt ")"
                | "new" array_type "[" expr "]"
                | ID "->" lambda_body
                | TYPEID "." ID | STRING "." ID
                | TYPEID "." "class" | primitive "." "class"
```

### 4.1 A estratégia `TYPEID`

Em Java, `Conta c` (declaração) e `contas[i]` (indexação) começam com um
identificador. Um parser LALR(1) ingênuo confunde `T[]` com indexação. A
solução foi uma passada prévia que coleta nomes de classes/interfaces/enums
e faz o lexer marcá-los como `TYPEID`.

### 4.2 Conflitos e soluções

| Situação | Solução |
|---|---|
| `else` pendente | precedência `ELSE` |
| `(int) x` vs `(expr)` | cast só com tipo primitivo/`TYPEID`/`STRING` |
| `new T[n]` vs `new T(...)` | lookahead `[` vs `(` |
| construtor vs método | `TYPEID (` vs `type ID (` |
| `for` vs `for-each` | lookahead `;` vs `:` |
| genéricos | apagados; usados só na checagem |
| lambdas | param único sem parênteses, zero ou 2+ com parênteses |
| class literals | `TYPEID . class` separado de `TYPEID . ID` |

## 5. Implementação

### 5.1 Arquitetura

```text
.java
  │ lexer.py (PLY lex)
  ▼
tokens
  │ parser.py (PLY yacc + AST)
  ▼
AST
  │ semantico.py (símbolos, escopos, tipos)
  ▼
AST tipada
  │ codegen.py (emitter PHP)
  ▼
.php + runtime/php/
```

### 5.2 Lexer

- PLY lex com linha/coluna.
- Palavras-chave, identificadores, literais, operadores e comentários.
- Strings com escapes e `char`.
- Text blocks (`"""`) com remoção de indentação e escapes.
- Pré-processamento de anotações com argumentos: os argumentos são
  substituídos por espaços, preservando linhas/colunas; a anotação em si
  continua sendo lida e ignorada.
- `collect_type_names` faz a passada de nomes antes do parser.

### 5.3 Parser e AST

- PLY/yacc LALR(1).
- AST com dataclasses: declarações, comandos, expressões e tipos.
- Cada nó carrega linha/coluna; o modo projeto anota também o arquivo de
  origem para diagnósticos.
- O parser respeita a precedência de expressões e as decisões da Seção 4.

### 5.4 Análise semântica

- Duas passadas de declaração: classes/interfaces/enums e membros.
- Tabela de símbolos por escopo.
- Resolução de nomes e tipos.
- Compatibilidade e promoção numérica.
- Herança/interfaces: subtipos, override, checagem de implementação.
- Exceções: `throw`/`catch` só aceitam tipos de exceção; construtor com
  `super(...)`; exceções customizadas.
- Coleções: tipo do elemento, métodos e `for-each`.
- Streams/lambdas: tipos esperados dos parâmetros e retorno.
- Enums: constantes e `switch`.
- Pacotes: `qualified_name` para namespace/autoloader.
- Diagnósticos com `arquivo:linha:col: erro`.

### 5.5 Geração de código

- Emissor PHP com indentação e precedência.
- Regras principais:

| Java | PHP |
|---|---|
| `int/int` | `intdiv` |
| `String + x` | `JString::concat` |
| `s.length()` | `strlen` |
| `a.length` | `count` |
| `new int[n]` | `array_fill` |
| `for-each` | `foreach` |
| `a == b` (referência) | `===` |
| `s1 < s2` (String) | `strcmp` |
| `System.out.println` | `JSystem::println` |
| `(char) x` | `chr` |
| `(int) 'a'` | `ord` |
| `(Conta) x` | `JCast::to(...)` |
| `x instanceof Conta` | `instanceof` |
| `x instanceof Conta c` | `($c = $x) instanceof Conta` |
| `try (R r = expr) { }` | `$r = expr; try { ... } finally { close }` |
| `catch (A \| B e)` | `catch (\A \| \B $e)` |
| `Conta.class` | `JClass::of(Conta::class)` |
| `new ArrayList<>()` | `new JArrayList()` |
| `stream().filter(...)` | `->filter(fn($x) => ...)` |
| `collect(Collectors.toList())` | `->toList()` |

- Modo single-file: um `.php` por `.java`, com entrypoint protegido.
- Modo projeto: um `.php` por arquivo, `namespace`/`use`, `bootstrap.php`
  com autoloader e `run.php`.

### 5.6 Runtime PHP

| Classe | Função |
|---|---|
| `JString` | `valueOf`, `concat`, `charAt`, `substring`, `indexOf`, `split` |
| `JSystem` | `print`, `println` |
| `JArrayList` | lista com `get`, `set`, `add`, `remove`, `stream` |
| `JHashMap` | mapa com `put`, `get`, `keySet`, `values` |
| `JHashSet` | conjunto com `add`, `remove`, `forEach` |
| `JScanner` | leitura de `stdin` |
| `JStream` | pipeline eager de streams |
| `JCast` | casts de referência |
| `JClass` | class literals mínimos |

### 5.7 CLI e modo projeto

```bash
# arquivo único
transpilar Pessoa.java -o build/Pessoa
php build/Pessoa/Pessoa.php

# projeto
transpilar src/ -o build/project --main Main
php build/project/run.php
```

No modo projeto, a pasta é varrida recursivamente, os tipos são coletados
globalmente, a análise semântica é única e o `bootstrap.php` indexa as
classes por nome qualificado.

## 6. Testes e resultados

### 6.1 Estratégia

- **Unitários:** lexer, parser, semântica, codegen.
- **Diferencial:** compila e executa o `.java`, transpila, roda `php -l`,
  executa o PHP e compara stdout.
- **Projeto:** compila todos os `.java`, roda `java app.Main`, transpila a
  pasta, executa `run.php` e compara.
- **Lint:** `compileall` e `php -l`.
- **CI:** GitHub Actions com Python, PHP 8.3 e JDK 21.
- **Source level:** os testes compilam com `javac --release 21`; o
  subconjunto suportado é aceito nessa versão. Recursos modernos ainda não
  implementados geram diagnóstico explícito.

Comando único:

```bash
make check
```

### 6.2 Números atuais

```text
123 testes unitários
30/30 casos no diff Java×PHP
[projeto] OK
php -l em todo o runtime
```

### 6.3 Corpus

O corpus cobre: `Hello`, `Calculadora`, `FizzBuzz`, `Vetores`, `Textos`,
`Utilitarios`, `Conta`, `Banco`, `HerancaConta`, `Animais`, `Formas`,
`BancoLista`, `Leitura`, `MapaBanco`, `Conjunto`, `Excecoes`, `Escolhas`,
`Enums`, `Lambdas`, `BancoMenu`, `Moderno`, `Casts`, `Classes`, `Estoque`,
`Funcionarios`, `Variaveis`, `SwitchModerno`, `PatternInstanceof`, `Recursos`
e `Records`.

O modo projeto usa `tests/project/src`, com `Main` em `package app`,
`Conta`/`ContaCorrente` em `package model` e a exceção em `package error`.

### 6.4 Exemplos de execução

`examples/BancoMenu.java`:

```text
1=listar 2=sacar 0=sair
Ana: 100.0
Bia: 200.0 (limite 50.0)
1=listar 2=sacar 0=sair
erro: saldo insuficiente para Ana
fim da operacao
...
```

`examples/Casts.java`:

```text
i=3
d=3.0
c=A
codigo=97
true
false
Rex: au au
```

### 6.5 Projetos reais

Foram testadas pastas reais de backend Spring. O modo projeto funcionou,
mas os projetos param em recursos fora do subconjunto:

- text blocks/anotações foram resolvidos na Fase 1;
- depois restaram tipos externos (`TaskExecutor`, `ResponseEntity`),
  `@interface` e APIs de framework.

Isso confirma a fronteira: o projeto não implementa semântica de framework.
Uma classe simples real (`BusinessException`) foi transpilada com sucesso.

## 7. Limitações e trabalhos futuros

### 7.1 Limitações

- Sem semântica de Spring/JPA/Lombok.
- Sem reflection completa.
- Sem threads/concorrência.
- Sem sobrecarga de métodos do usuário.
- Sem validação de exceções checadas e sem exceções suprimidas.
- Records sem `equals`/`hashCode`/`toString` automáticos, sem construtor compacto e sem record patterns.
- Sem pattern matching em `switch`.
- Sem métodos `default`/`static`/`private` em interfaces.
- Genéricos de usuário e tipos boxed não suportados.
- Nomes simples de classe precisam ser únicos no projeto.
- Sem `.jar`/dependências externas.
- Fidelidade parcial em Unicode, overflow, identidade de arrays/strings.

### 7.2 Trabalhos futuros

- Suporte a tipos externos como classes opacas.
- `@interface` e anotações com semântica própria.
- Sobrecarga com mangling.
- Pattern matching em `switch`.
- Reflection mínima além de `Class`.
- Melhor fidelidade de `char`/UTF-16 e overflow.
- Build incremental e cache de análise.

## 8. Conclusão

O projeto entregou um transpilador funcional para um subconjunto amplo de
Java, com pipeline completo, runtime PHP e validação diferencial. A maior
contribuição não é “traduzir Java inteiro”, mas demonstrar, de forma
executável, como decisões de análise semântica e de mapeamento de paradigmas
afetam a tradução: `intdiv`, `JString`, arrays, coleções, exceções,
namespaces e streams só funcionam porque a semântica dirige a geração.

O escopo foi deliberadamente recortado. Recusar recursos — especialmente
frameworks — foi uma decisão de engenharia, não uma falha: mantém o projeto
verificável e permite explicar cada escolha.

## Referências

- PLY — Python Lex-Yacc. https://github.com/dabeaz/ply
- Java Language Specification. https://docs.oracle.com/javase/specs/
- ANTLR grammars-v4 — Java. https://github.com/antlr/grammars-v4/tree/master/java
- JavaParser. https://github.com/javaparser/javaparser
- Spoon. https://github.com/INRIA/spoon
- PHP Manual. https://www.php.net/manual/
- bafolts/java2php. https://github.com/bafolts/java2php (referência de ideias)
- ts2php. https://github.com/searchfe/ts2php
- cs2php. https://github.com/isukces/cs2php

## Apêndice A — Comandos

```bash
make install
make test
make diff
make project
make check
make demo
```

## Apêndice B — Estrutura

```text
src/transpilador/   lexer, parser, ast, semantico, codegen, cli
runtime/php/        JString, JSystem, JCast, JClass,
                    JArrayList, JStream, JHashMap, JHashSet, JScanner
examples/           programas Java de demonstração
tests/unit/         testes unitários
tests/corpus/java/  corpus do diff
tests/project/      projeto multi-arquivo
scripts/            diff_test.py, project_test.py
docs/               escopo, gramática, decisões, reuso
```

## Apêndice C — Reuso

O registro de fontes, licenças e adaptações está em
[`docs/reuso.md`](reuso.md). Nenhum transpilador completo foi copiado; a
implementação, a AST, a semântica, o codegen e o runtime foram escritos para
este projeto, com PLY como biblioteca de parsing.
