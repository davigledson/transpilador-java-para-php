import java.util.HashSet;
import java.util.Set;

public class Conjunto {
    public static void main(String[] args) {
        Set<String> nomes = new HashSet<>();
        System.out.println(nomes.add("Ana"));
        System.out.println(nomes.add("Bia"));
        System.out.println(nomes.add("Ana"));
        System.out.println("tamanho=" + nomes.size());
        System.out.println("temBia=" + nomes.contains("Bia"));
        System.out.println("removeuBia=" + nomes.remove("Bia"));
        System.out.println("tamanhoFinal=" + nomes.size());
        for (String nome : nomes) {
            System.out.println("restante=" + nome);
        }
    }
}
