package app;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import error.SaldoInsuficienteException;
import model.Conta;
import model.ContaCorrente;

public class Main {
    public static void main(String[] args) {
        List<Conta> contas = new ArrayList<>();
        contas.add(new Conta("Ana", 100.0));
        contas.add(new ContaCorrente("Bia", 200.0, 50.0));

        for (Conta c : contas) {
            System.out.println(c.descricao());
        }

        try {
            contas.get(0).sacar(150.0);
        } catch (SaldoInsuficienteException e) {
            System.out.println("erro: " + e.getMessage());
        } finally {
            System.out.println("fim");
        }

        List<String> nomes = List.of("Ana", "Bia");
        System.out.println("nomes: " + nomes.size() + "/" + nomes.get(0));

        Set<String> tags = Set.of("a", "b");
        System.out.println("tags: " + tags.size());

        var saldos = Map.of("Ana", 100, "Bia", 200);
        System.out.println("saldos: " + saldos.get("Bia"));

        Optional<String> primeiro = Optional.of("Ana");
        System.out.println("optional: " + primeiro.isPresent() + "/" + primeiro.get());

        Optional<String> vazio = Optional.empty();
        System.out.println("vazio: " + vazio.orElse("padrao"));

        System.out.println("texto: " + "  x  ".strip());
        System.out.println("rep: " + "ab".repeat(2));
        System.out.println("fmt: " + "%s-%d".formatted("A", 3));
        System.out.println("clamp: " + Math.clamp(15, 0, 10));
    }
}
