public class Enums {
    public static void main(String[] args) {
        Status s = Status.ATIVO;
        System.out.println(s);

        switch (s) {
            case ATIVO:
                System.out.println("ativo");
                break;
            case BLOQUEADO:
                System.out.println("bloqueado");
                break;
        }

        Status t = Status.BLOQUEADO;
        System.out.println(t == Status.BLOQUEADO);
        System.out.println(t != Status.ATIVO);
    }
}

enum Status {
    ATIVO,
    BLOQUEADO
}
