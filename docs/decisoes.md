# Decisões de projeto (ADRs resumidos)

## 1. PLY em vez de parser escrito à mão

**Contexto:** a disciplina permite gerador de parser; o prazo é curto.
**Decisão:** PLY (lex/yacc) em Python.
**Motivo:** gramática e ações semânticas em um só lugar; LALR(1) suficiente
para o subconjunto; sem build nativo.
**Consequência:** menos mérito “artesanal” de lexer/parser, mas mais tempo
para semântica, codegen e testes.

## 2. Python 3.14 + PLY 3.11

PLY 3.11 é antigo, mas foi testado no ambiente (Python 3.14.10) e funcionou.
Se houver regressão, o fallback é Lark 1.3.1 (EBNF + Transformer).

## 3. `TYPEID` para separar declaração de indexação

**Problema:** `Conta c` e `contas[i]` começam com identificador.
**Decisão:** primeira passada coleta nomes de classes; o lexer marca esses
nomes como `TYPEID`.
**Consequência:** gramática LALR(1) sem conflito; variável com nome de classe
é limitação conhecida.

## 4. AST tipada como IR

**Decisão:** não criar TAC/IR de três endereços nesta versão. A AST anotada
(`inferred_type`, `binding`, `call_kind`) é o IR.
**Motivo:** fonte→fonte se beneficia de AST→AST; TAC dobraria o trabalho.
**Consequência:** otimizações ficam como trabalho futuro.

## 5. Arrays nativos do PHP

**Decisão:** `T[]` vira `array` do PHP; `new T[n]` vira `array_fill`.
**Motivo:** legibilidade e simplicidade.
**Consequência:** não há identidade de array nem `ArrayStoreException`;
bounds check fica por conta do PHP (warning).

## 6. Strings nativas + `JString`

**Decisão:** `String` vira `string`; operações que diferem do Java passam por
`JString` (`valueOf`, `concat`, `charAt`, `substring`, `indexOf`, `split`).
**Motivo:** preservar `null` → `"null"`, `true` → `"true"`, `1.0` → `"1.0"`.
**Consequência:** strings são bytes, não UTF-16; `length()` usa `strlen`.

## 7. Divisão inteira com `intdiv`

**Decisão:** se ambos os operandos são `int`/`char`, gerar `intdiv(a, b)`.
**Motivo:** PHP `/` retorna float; Java trunca.
**Consequência:** divisão por zero lança `DivisionByZeroError` (não
`ArithmeticException`).

## 8. Igualdade e ordem

- `==`/`!=` numéricos → `==`/`!=` no PHP;
- booleanos e referências/String → `===`/`!==`;
- `< <= > >=` só numéricos (Java não permite String).

## 9. Tipos nullable no PHP

**Decisão:** referências (`String`, classes, arrays) viram `?Tipo` em campos,
parâmetros e retornos.
**Motivo:** Java permite `null`; `?` evita `TypeError` em `strict_types`.
**Consequência:** campos de referência são inicializados com `null`.

## 10. Herança simples implementada

**Decisão:** suportar `extends` com uma única superclasse, `super(...)`,
`super.metodo(...)`, override e polimorfismo.
**Motivo:** é a lacuna semântica mais importante para o relatório e para a
demo de banco (Conta/ContaCorrente).
**Consequência:** o analisador resolve métodos/campos subindo a hierarquia e
checa subtipos; o gerador emite `class B extends A` e `parent::...`.
**Limitações:** sem `this(...)`, sem ocultação de campos e sem herança
múltipla. Se o pai não tiver construtor sem argumentos, o construtor do
filho precisa chamar `super(...)`.

## 10.1. `super()` implícito

**Decisão:** se o construtor do filho não chama `super(...)` e o pai tem
construtor sem argumentos, o gerador insere `parent::__construct();`.
**Motivo:** reproduzir a inserção automática do Java.
**Consequência:** se o pai só tem construtores com argumentos, o erro é
detectado na análise semântica.

## 10.2. Interfaces e classes abstratas

**Decisão:** suportar `interface` com métodos abstratos, `implements`
múltiplo, classes `abstract` e métodos abstratos.
**Motivo:** completar o núcleo de OO e permitir polimorfismo por contrato.
**Consequência:** o analisador coleta interfaces da hierarquia, checa
assinaturas e exige que toda classe concreta implemente os métodos
abstratos. O gerador emite `interface`, `abstract class`,
`implements A, B` e `abstract public function ...;`.
**Limitações:** sem `default`, constantes de interface, métodos
`static`/`private` em interface e sem interface estendendo várias
interfaces.

## 10.3. Coleções e `Scanner`

**Decisão:** mapear `ArrayList`/`List` para `JArrayList`, `HashMap`/`Map`
para `JHashMap`, `HashSet`/`Set` para `JHashSet` e `Scanner` para `JScanner`,
apagando os argumentos genéricos no PHP, mas usando-os na checagem de tipos.
**Motivo:** são as APIs mais usadas em exercícios de Java e viabilizam uma
demo com lista/mapa de objetos e entrada de dados.
**Consequência:** `List<String> l = new ArrayList<>()` e
`Map<String, Conta> m = new HashMap<>()` funcionam; `get`/`keySet`/`values`
preservam os tipos para a análise semântica; `for-each` funciona em listas e
sets.
**Limitações:** sem `LinkedHashMap`/`TreeMap`/`entrySet`; chaves de mapa
escalares são comparadas por valor e objetos por identidade, não `equals()`;
sem genéricos em classes do usuário e sem tipos boxed (`ArrayList<Integer>`).

## 10.4. Exceções

**Decisão:** suportar `try/catch/finally`, `throw`, `throws` (lido e
ignorado), exceções embutidas (`RuntimeException`, `Exception`, etc.) e
classes de exceção do usuário que estendem uma exceção embutida.
**Motivo:** completar o controle de fluxo e permitir o padrão de erro
customizado (`SaldoInsuficienteException`).
**Consequência:** o gerador emite `try/catch/finally`, `throw` e
`class X extends \RuntimeException`; `getMessage`/`getCode` são mapeados.
**Limitações:** não há checagem de exceções checadas; `printStackTrace` vai
para stderr, sem stack trace do Java.

## 10.4.1. Multi-catch e try-with-resources

**Decisão:** aceitar `catch (A | B e)` e `try (Recurso r = ...)`, inclusive
com `var` e vários recursos.
**Motivo:** são as formas modernas de tratamento de recursos e erros e
aparecem juntas em código Java 21.
**Consequência:** o multi-catch vira `catch (\A | \B $e)` no PHP; o parâmetro
recebe o supertipo comum dos tipos. Try-with-resources é abaixado para
`try/finally` aninhados, fechando os recursos em ordem inversa antes de
`catch`/`finally`; recursos visíveis só no corpo do `try`.
**Limitações:** sem exceções suprimidas; o recurso precisa implementar
`AutoCloseable`/`Closeable` (ou ser `Scanner`); `Closeable` e
`AutoCloseable` são interfaces do runtime PHP.

## 10.5. `switch`

**Decisão:** suportar o `switch` statement clássico (`case`, `default`,
fallthrough e `break`) para `int`, `char` e `String`.
**Motivo:** é controle de fluxo comum e barato de mapear para PHP.
**Consequência:** o gerador avalia a expressão uma vez em `$__switchN` e usa
`switch (true)` com comparações `===`, preservando a semântica estrita do
Java para `String`/`char`.
**Limitações:** sem labels, `continue` dentro do `switch` e pattern matching
em `switch`.

## 10.15. `switch` Java 21

**Decisão:** suportar `case ... ->`, `switch` expression e `yield`.
**Motivo:** são as formas modernas das mesmas construções de `switch` e
aparecem em código Java 21.
**Consequência:** statement arrow vira `if/else if`; switch expression usa
uma variável temporária e `switch (true)`; `yield` atribui ao resultado e
quebra o switch. `default` é obrigatório nesta versão.
**Limitações:** sem pattern matching em `switch`, labels ou `continue`
dentro do switch.

## 10.6. Enums simples

**Decisão:** mapear `enum` com constantes para `enum` do PHP 8.1; acessos
`Status.ATIVO` viram `Status::ATIVO`; `switch` sobre enum usa `===`.
**Motivo:** fechar o domínio de `switch`/tipos e permitir modelagem simples
de estados.
**Consequência:** `Status s = Status.ATIVO`, `s == Status.ATIVO` e
`switch (s) { case ATIVO: ... }` funcionam; `println(s)` imprime `ATIVO`
via `JString::valueOf` (`UnitEnum`).
**Limitações:** enums só com constantes; sem campos, métodos, `values()` ou
`ordinal()`.

## 10.7. Lambdas e streams

**Decisão:** suportar lambdas de expressão em contextos de coleções/streams,
mapeadas para `fn(...) => ...` do PHP, e um `JStream` eager para
`filter`/`map`/`forEach`/`count`/`anyMatch`/`allMatch`/`noneMatch`/
`limit`/`sorted`.
**Motivo:** fechar o paradigma funcional sem implementar interfaces
funcionais genéricas nem um pipeline lazy completo.
**Consequência:** `nomes.forEach(n -> ...)`, `nomes.removeIf(n -> ...)` e
`nomes.stream().filter(...).map(...).collect(Collectors.toList())` funcionam;
`collect` vira `->toList()`.
**Limitações:** lambda só de expressão, sem method references, sem streams
paralelos e sem `Collectors` além de `toList()`.

## 10.8. Modo projeto

**Decisão:** se a entrada for um diretório, transpilar todos os `.java`
recursivamente, com coleta global de tipos e uma única análise semântica;
gerar um `.php` por arquivo Java, um `bootstrap.php` com autoloader e um
`run.php` para a classe `main`.
**Motivo:** permitir projetos com várias classes sem exigir que o usuário
monte `require`/ordem de carregamento manualmente.
**Consequência:** `transpilar src/ -o build --main Main` gera
`build/bootstrap.php`, `build/run.php` e os módulos PHP preservando subpastas.
**Limitações:** nomes simples precisam ser únicos (sem aliases/namespaces
duplicados), sem `.jar` e sem build incremental.

## 10.12. `package` → namespace

**Decisão:** mapear `package a.b` para `namespace a\b;` e `import a.b.C`
para `use a\b\C;` (incluindo wildcard quando o pacote é do projeto).
**Motivo:** projetos Java com pacotes devem gerar PHP com namespaces e
autoloader por FQN.
**Consequência:** `bootstrap.php` indexa classes pelo nome qualificado;
`run.php` chama `\a\Main::main(...)`; classes de outros pacotes usam `use`
ou FQN.
**Limitações:** nomes simples duplicados ainda são rejeitados; imports
externos são ignorados; aliases manuais de `use` não são suportados.

## 10.13. Source level Java 21

**Decisão:** manter o mesmo subconjunto, mas declarar e testar source level
21, com diagnósticos explícitos para recursos modernos ainda não suportados.
**Motivo:** o código aceito já é Java 21 válido; o que falta é sintaxe nova,
não uma mudança no pipeline.
**Consequência:** os testes usam `javac --release 21`; `@interface` falha com
mensagem clara em vez de erro genérico.
**Limitações:** não são esses recursos que estão implementados; eles apenas
são diagnosticados.

## 10.14. `var`

**Decisão:** inferir o tipo de variáveis locais declaradas com `var`,
inclusive em `for` clássico e `for-each`.
**Motivo:** é a forma mais comum em código Java moderno e não exige mudança
no codegen além de omitir o tipo local.
**Consequência:** `var x = 1;` vira `$x = 1;`; `var` sem inicializador ou
com `null` é erro; campos e parâmetros continuam exigindo tipo explícito.
**Limitações:** sem `var` em lambda ou parâmetro de `catch` (locais, `for`,
`for-each` e recursos de try-with-resources são suportados).

## 10.9. Text blocks e anotações com argumentos

**Decisão:** suportar text blocks (`"""`) no lexer e remover os argumentos de
anotações antes do parsing, preservando linhas/colunas.
**Motivo:** permitir que o parser avance em código Java moderno sem
implementar semântica de framework.
**Consequência:** `@Column(name = "x", length = 150)` vira apenas
`@Column` + espaços; text blocks viram string normal com indentação e
escapes processados.
**Limitações:** anotações continuam sem efeito semântico; `@interface` e
class literals dentro de anotações não são suportados.

## 10.10. Casts e `instanceof`

**Decisão:** suportar casts primitivos (`int`, `double`, `char`) e de
referência, além de `instanceof` para classes/interfaces/String/arrays.
**Motivo:** são operações comuns em código OO e permitem polimorfismo com
checagem de tipo.
**Consequência:** `(char) 65` vira `chr(65)`, `(int) 'a'` vira `ord("a")`,
`(Conta) obj` vira `JCast::to(...)` e `obj instanceof Conta` vira
`instanceof` do PHP.
**Limitações:** sem unboxing/casts entre primitivos e wrappers; casts de
array só verificam `array` em runtime.

## 10.10.1. Pattern `instanceof`

**Decisão:** aceitar `expr instanceof Tipo nome` e disponibilizar `nome` no
ramo verdadeiro do `if`/`while` e à direita de `&&`.
**Motivo:** é a forma idiomática de testar e converter em Java moderno.
**Consequência:** o codegen atribui a variável dentro da própria condição
(`($c = $obj) instanceof Conta`); a análise semântica declara o binding só no
escopo em que ele é garantido.
**Limitações:** sem binding em `||`, em condições negadas ou fora do ramo
verdadeiro; sem pattern matching em `switch`.

## 10.11. Class literals

**Decisão:** mapear `X.class`, `int.class` e `String.class` para
`JClass::of(...)`, com `getName`, `getSimpleName`, `isInstance` e `toString`.
**Motivo:** permitir código que usa `Class` como valor sem implementar
reflection completa.
**Consequência:** `Conta.class.getSimpleName()` vira
`JClass::of(Conta::class)->getSimpleName()`; `println(Conta.class)` imprime
`class Conta`.
**Limitações:** sem `getMethods`/`getFields`/`newInstance`; nomes de classes
com pacote são resolvidos via namespace/use.

## 10.16. Records

**Decisão:** suportar `record Nome(Tipo a, Tipo b) { ... }` com componentes,
construtor canônico implícito, acessores `a()`/`b()`, métodos e membros
`static`; `implements` é permitido.
**Motivo:** records são a forma moderna de portadores de dados e aparecem com
frequência em código Java 21.
**Consequência:** o codegen emite `final class`, propriedades `readonly`
inicializadas no construtor, um `__construct` canônico e um método acessor
por componente. Um construtor canônico explícito é aceito e não é duplicado;
campos de instância extras e construtores não canônicos são rejeitados.
**Limitações:** sem `equals`/`hashCode`/`toString` automáticos, sem construtor
compacto e sem record patterns; componentes não podem ser genéricos.

## 10.17. Sealed, non-sealed e permits

**Decisão:** suportar `sealed`/`non-sealed` em classes e interfaces e
`permits` em classes/interfaces sealed, com inferência de permits quando os
subtipos diretos estão no mesmo arquivo/projeto.
**Motivo:** completar a modelagem de hierarquias fechadas de Java 21 e
permitir `switch` exaustivo no futuro.
**Consequência:** a checagem é toda em compilação: subtipos diretos precisam
ser permitidos; cada permitido precisa ser `final`, `sealed` ou `non-sealed`;
`permits` só vale em tipo sealed; `non-sealed` exige supertipo sealed; tudo
no mesmo pacote. O codegen emite classes/interfaces PHP normais, sem
`sealed`/`permits`.
**Limitações:** PHP não tem equivalente de runtime, então extensão fora do
conjunto permitido não é impedida em tempo de execução; `sealed enum` ainda
não é suportado.

## 11. Sobrecarga rejeitada

**Decisão:** métodos com mesmo nome são erro; construtores podem variar a
aridade.
**Motivo:** PHP não tem sobrecarga; resolver em compilação exigiria
mangulação de nomes.
**Consequência:** sobrecarga de métodos do usuário fica fora. Overloads de
biblioteca são resolvidos caso a caso (ex.: `ArrayList.remove(int)` vs
`remove(Object)`).

## 12. `static final` vira propriedade estática

**Decisão:** `public static int $N = 3;` em vez de `const`.
**Motivo:** inicializadores podem ser expressões e o acesso `Classe.N` fica
uniforme.
**Consequência:** não é imutável em tempo de execução.

## 13. Entrypoint `main`

**Decisão:** gerar `Classe::main(array_slice($argv, 1))` no fim do arquivo,
protegido por `PHP_SAPI === 'cli'` e `realpath(...) === __FILE__`.
**Motivo:** permitir `require` do arquivo sem executar `main`.

## 14. Erros com linha/coluna

**Decisão:** `TranspileError(message, line, col)`; CLI imprime
`arquivo:linha:col: erro: ...`.
**Motivo:** diagnóstico é parte da nota e da usabilidade.

## 15. Acesso não é checado

**Decisão:** `private/protected` são emitidos, mas o analisador não impede
acesso indevido.
**Motivo:** custo/benefício no prazo.
**Consequência:** o PHP pode permitir o que o Java rejeitaria; documentado.
