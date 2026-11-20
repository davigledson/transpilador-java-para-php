@MinhaAnotacao(valor = "classe", prioridade = 1, tags = {"a", "b"})
public class Anotacoes {
    @MinhaAnotacao(valor = "metodo")
    public static void main(String[] args) {
        System.out.println("anotacoes ok");
    }
}

@interface MinhaAnotacao {
    String valor() default "";

    int prioridade() default 0;

    String[] tags() default {};
}
