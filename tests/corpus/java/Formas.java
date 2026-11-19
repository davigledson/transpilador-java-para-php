interface Forma {
    double area();
    String nome();
}

abstract class Figura implements Forma {
    protected String nome;

    public Figura(String nome) {
        this.nome = nome;
    }

    public String nome() {
        return nome;
    }
}

class Circulo extends Figura {
    private double raio;

    public Circulo(double raio) {
        super("Círculo");
        this.raio = raio;
    }

    public double area() {
        return 3.14159 * raio * raio;
    }
}

class Quadrado extends Figura {
    private double lado;

    public Quadrado(double lado) {
        super("Quadrado");
        this.lado = lado;
    }

    public double area() {
        return lado * lado;
    }
}

public class Formas {
    public static void main(String[] args) {
        Forma[] formas = new Forma[3];
        formas[0] = new Circulo(2.0);
        formas[1] = new Quadrado(3.0);
        formas[2] = new Circulo(1.0);

        double total = 0.0;
        for (int i = 0; i < formas.length; i++) {
            System.out.println(formas[i].nome() + ": " + formas[i].area());
            total += formas[i].area();
        }
        System.out.println("Total: " + total);
    }
}
