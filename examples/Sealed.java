public class Sealed {
    public static void main(String[] args) {
        Forma circulo = new Circulo(2.0);
        System.out.println(circulo.area());

        Forma quadrado = new Quadrado(3.0);
        System.out.println(quadrado.area());

        Animal cachorro = new Cachorro();
        System.out.println(cachorro.som());

        Animal gato = new Gato();
        System.out.println(gato.som());
    }
}

sealed interface Forma permits Circulo, Quadrado {
    double area();
}

final class Circulo implements Forma {
    private double raio;

    Circulo(double raio) {
        this.raio = raio;
    }

    public double area() {
        return 3.0 * raio * raio;
    }
}

final class Quadrado implements Forma {
    private double lado;

    Quadrado(double lado) {
        this.lado = lado;
    }

    public double area() {
        return lado * lado;
    }
}

sealed abstract class Animal permits Cachorro, Gato {
    abstract String som();
}

non-sealed class Cachorro extends Animal {
    String som() {
        return "latido";
    }
}

final class Gato extends Animal {
    String som() {
        return "miau";
    }
}
