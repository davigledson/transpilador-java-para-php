import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class Estoque {
    public static void main(String[] args) {
        List<Produto> lista = new ArrayList<>();
        lista.add(new Produto("Caneta", 2.5, 10));
        lista.add(new Produto("Caderno", 15.0, 3));
        lista.add(new Produto("Borracha", 1.5, 0));

        Map<String, Produto> porNome = new HashMap<>();
        porNome.put("caneta", lista.get(0));
        porNome.put("caderno", lista.get(1));
        porNome.put("borracha", lista.get(2));

        Produto p = porNome.get("caneta");
        System.out.println(p.getNome() + ": " + p.getPreco());

        List<Produto> caros = lista.stream()
            .filter(prod -> prod.getPreco() > 2.0)
            .collect(Collectors.toList());

        caros.forEach(prod -> System.out.println("caro=" + prod.getNome()));

        System.out.println("totalMapa=" + porNome.size());
        System.out.println("temCaderno=" + porNome.containsKey("caderno"));

        porNome.remove("borracha");
        System.out.println("restantes=" + porNome.size());
    }
}

class Produto {
    private String nome;
    private double preco;
    private int quantidade;

    public Produto(String nome, double preco, int quantidade) {
        this.nome = nome;
        this.preco = preco;
        this.quantidade = quantidade;
    }

    public String getNome() {
        return nome;
    }

    public double getPreco() {
        return preco;
    }

    public int getQuantidade() {
        return quantidade;
    }
}
