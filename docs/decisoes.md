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
**Limitações:** não há checagem de exceções checadas, multi-catch ou
try-with-resources; `printStackTrace` vai para stderr, sem stack trace do
Java.

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
