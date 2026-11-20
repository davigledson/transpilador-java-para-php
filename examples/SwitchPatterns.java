public class SwitchPatterns {
    public static void main(String[] args) {
        Forma[] formas = new Forma[4];
        formas[0] = new Circulo(2.0);
        formas[1] = new Quadrado(3.0);
        formas[2] = null;
        formas[3] = new Circulo(0.5);

        for (Forma forma : formas) {
            descrever(forma);
        }
    }

    static void descrever(Forma forma) {
        switch (forma) {
            case Circulo c when c.raio() > 1 -> System.out.println("circulo grande");
            case Circulo c -> System.out.println("circulo " + c.raio());
            case Quadrado q -> System.out.println("quadrado " + q.lado());
            case null -> System.out.println("nulo");
            default -> System.out.println("outro");
        }

        String nome = switch (forma) {
            case Circulo c -> "C";
            case Quadrado q -> "Q";
            case null -> "N";
            default -> "?";
        };
        System.out.println(nome);
    }
}

interface Forma {
}

class Circulo implements Forma {
    private double raio;

    Circulo(double raio) {
        this.raio = raio;
    }

    double raio() {
        return raio;
    }
}

class Quadrado implements Forma {
    private double lado;

    Quadrado(double lado) {
        this.lado = lado;
    }

    double lado() {
        return lado;
    }
}
