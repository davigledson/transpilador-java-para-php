public class SwitchModerno {
    public static void main(String[] args) {
        int opcao = 2;

        switch (opcao) {
            case 1 -> System.out.println("um");
            case 2 -> System.out.println("dois");
            default -> System.out.println("outro");
        }

        String nome = switch (opcao) {
            case 1 -> "um";
            case 2 -> "dois";
            default -> "outro";
        };
        System.out.println(nome);

        String comBloco = switch (opcao) {
            case 1 -> {
                System.out.println("bloco um");
                yield "UM";
            }
            default -> {
                System.out.println("bloco outro");
                yield "OUTRO";
            }
        };
        System.out.println(comBloco);

        String s = "b";
        String resultado = switch (s) {
            case "a" -> "A";
            case "b" -> "B";
            default -> "?";
        };
        System.out.println(resultado);
    }
}
