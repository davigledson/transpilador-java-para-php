public class Utilitarios {
    public static void main(String[] args) {
        String texto = String.valueOf(42);
        int numero = Integer.parseInt("123");
        double raiz = Math.sqrt(81.0);
        int absoluto = Math.abs(-7);

        System.out.println(texto + " / " + numero);
        System.out.println("raiz=" + raiz);
        System.out.println("abs=" + absoluto);

        int i = 0;
        while (i < 3) {
            System.out.println("i=" + i);
            i++;
        }

        do {
            i--;
        } while (i > 0);

        System.out.println("fim=" + i);
    }
}
