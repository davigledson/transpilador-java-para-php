public class Classes {
    public static void main(String[] args) {
        System.out.println(Conta.class);
        System.out.println(Conta.class.getSimpleName());
        System.out.println(Conta.class.getName());

        Conta c = new Conta();
        System.out.println(Conta.class.isInstance(c));

        System.out.println(int.class);
        System.out.println(String.class.getSimpleName());
    }
}

class Conta {
}
