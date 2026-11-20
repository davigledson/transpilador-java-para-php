import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

public class Biblioteca21 {
    public static void main(String[] args) {
        List<String> nomes = List.of("Ana", "Bia");
        System.out.println(nomes.size());
        System.out.println(nomes.get(1));

        Set<String> tags = Set.of("a", "b");
        System.out.println(tags.size());

        var idades = Map.of("Ana", 30, "Bia", 25);
        System.out.println(idades.get("Bia"));

        Optional<String> nome = Optional.of("Ana");
        System.out.println(nome.isPresent());
        System.out.println(nome.get());
        System.out.println(nome.orElse("padrao"));

        Optional<String> vazio = Optional.empty();
        System.out.println(vazio.isEmpty());
        System.out.println(vazio.orElse("padrao"));

        List<String> maiusculas = nomes.stream()
            .map(n -> n.toUpperCase())
            .toList();
        System.out.println(maiusculas.get(0));

        System.out.println("   ".isBlank());
        System.out.println("  ana  ".strip());
        System.out.println("ab".repeat(3));
        System.out.println("%s tem %d".formatted("Ana", 3));

        System.out.println(Math.clamp(15, 0, 10));
        System.out.println(Math.floorDiv(7, 2));
        System.out.println(Math.floorMod(7, 2));
        System.out.println(Math.ceilDiv(7, 2));
        System.out.println(Math.signum(-5));
    }
}
