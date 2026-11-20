public class Records {
    public static void main(String[] args) {
        Ponto p = new Ponto(3, 4);
        System.out.println(p.x() + "," + p.y());
        System.out.println(p.soma());

        Nome n = new Nome("ana");
        System.out.println(n.valor());

        Produto produto = new Produto("caneta", 2.5);
        System.out.println(produto.descricao());

        System.out.println(Config.VERSAO);
        System.out.println(Config.criar());

        Vazio v = new Vazio();
        System.out.println("vazio");
    }
}

record Ponto(int x, int y) {
    public int soma() {
        return x + y;
    }
}

record Nome(String valor) implements Rotulo {
    public String valor() {
        return valor.toUpperCase();
    }
}

record Produto(String nome, double preco) {
    public Produto(String nome, double preco) {
        this.nome = nome;
        this.preco = preco;
    }

    public String descricao() {
        return nome + " = " + preco;
    }
}

record Vazio() {
}

record Config() {
    public static final int VERSAO = 7;

    public static String criar() {
        return "config";
    }
}

interface Rotulo {
    String valor();
}
