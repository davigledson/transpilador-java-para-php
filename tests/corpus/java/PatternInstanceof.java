public class PatternInstanceof {
    public static void main(String[] args) {
        Forma f = new Circulo(2.0);
        if (f instanceof Circulo c) {
            System.out.println("circulo " + c.raio());
        } else {
            System.out.println("nao e circulo");
        }

        Forma q = new Quadrado(3.0);
        if (q instanceof Quadrado qd && qd.lado() > 2) {
            System.out.println("quadrado grande " + qd.lado());
        }

        Forma outra = new Circulo(1.0);
        if (outra instanceof Quadrado qd2) {
            System.out.println(qd2.lado());
        } else {
            System.out.println("sem lado");
        }
    }
}

interface Forma {
}

class Circulo implements Forma {
    private double raio;

    public Circulo(double raio) {
        this.raio = raio;
    }

    public double raio() {
        return raio;
    }
}

class Quadrado implements Forma {
    private double lado;

    public Quadrado(double lado) {
        this.lado = lado;
    }

    public double lado() {
        return lado;
    }
}
