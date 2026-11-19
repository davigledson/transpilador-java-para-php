public class Casts {
    public static void main(String[] args) {
        int i = (int) 3.9;
        double d = (double) 3;
        char c = (char) 65;
        int codigo = (int) 'a';

        System.out.println("i=" + i);
        System.out.println("d=" + d);
        System.out.println("c=" + c);
        System.out.println("codigo=" + codigo);

        Animal a = new Cachorro("Rex");
        System.out.println(a instanceof Cachorro);
        System.out.println(a instanceof Gato);

        Cachorro c2 = (Cachorro) a;
        System.out.println(c2.falar());
    }
}

class Animal {
    protected String nome;

    public Animal(String nome) {
        this.nome = nome;
    }

    public String falar() {
        return "...";
    }
}

class Cachorro extends Animal {
    public Cachorro(String nome) {
        super(nome);
    }

    @Override
    public String falar() {
        return nome + ": au au";
    }
}

class Gato extends Animal {
    public Gato(String nome) {
        super(nome);
    }

    @Override
    public String falar() {
        return nome + ": miau";
    }
}
