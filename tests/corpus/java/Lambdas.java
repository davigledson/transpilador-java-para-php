import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class Lambdas {
    public static void main(String[] args) {
        List<String> nomes = new ArrayList<>();
        nomes.add("Ana");
        nomes.add("Bia");
        nomes.add("Caio");

        nomes.forEach(n -> System.out.println(n.toUpperCase()));

        List<String> longos = nomes.stream()
            .filter(n -> n.length() > 3)
            .collect(Collectors.toList());

        for (String n : longos) {
            System.out.println("longo=" + n);
        }

        List<String> maiusculos = nomes.stream()
            .map(n -> n.toUpperCase())
            .collect(Collectors.toList());

        for (String n : maiusculos) {
            System.out.println("map=" + n);
        }

        long total = nomes.stream().count();
        boolean temBia = nomes.stream().anyMatch(n -> n.equals("Bia"));
        System.out.println("total=" + total + " temBia=" + temBia);

        nomes.removeIf(n -> n.startsWith("B"));
        System.out.println("restantes=" + nomes.size());
    }
}
