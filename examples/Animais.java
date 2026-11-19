public class Animais {
    public static void main(String[] args) {
        Animal[] animais = new Animal[3];
        animais[0] = new Animal("Bicho");
        animais[1] = new Cachorro("Rex");
        animais[2] = new Gato("Mimi");

        for (int i = 0; i < animais.length; i++) {
            System.out.println(animais[i].falar());
        }
    }
}

class Animal {
    protected String nome;

    public Animal(String nome) {
        this.nome = nome;
    }

    public String falar() {
        return nome + ": ...";
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
