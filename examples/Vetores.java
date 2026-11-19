public class Vetores {
    public static void main(String[] args) {
        int[] numeros = new int[5];
        for (int i = 0; i < numeros.length; i++) {
            numeros[i] = i * i;
        }
        int soma = 0;
        for (int i = 0; i < numeros.length; i++) {
            soma += numeros[i];
        }
        System.out.println("soma=" + soma);
        for (int n : numeros) {
            System.out.println(n);
        }
    }
}
