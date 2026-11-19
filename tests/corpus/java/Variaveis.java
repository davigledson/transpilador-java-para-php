public class Variaveis {
    public static void main(String[] args) {
        var x = 10;
        var nome = "Ana";
        var numeros = new int[3];

        for (var i = 0; i < numeros.length; i++) {
            numeros[i] = i + x;
        }

        for (var n : numeros) {
            System.out.println(n);
        }

        var pessoa = new Pessoa("Bia");
        System.out.println(nome + " / " + pessoa.getNome());
    }
}

class Pessoa {
    private String nome;

    public Pessoa(String nome) {
        this.nome = nome;
    }

    public String getNome() {
        return nome;
    }
}
