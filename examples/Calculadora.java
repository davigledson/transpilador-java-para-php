public class Calculadora {
    static int soma(int a, int b) {
        return a + b;
    }

    static int fatorial(int n) {
        if (n <= 1) {
            return 1;
        }
        return n * fatorial(n - 1);
    }

    public static void main(String[] args) {
        int x = 10;
        int y = 3;
        System.out.println("soma=" + soma(x, y));
        System.out.println("divisao=" + (x / y));
        System.out.println("resto=" + (x % y));
        System.out.println("fatorial=" + fatorial(5));
    }
}
