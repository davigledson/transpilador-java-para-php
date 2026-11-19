public class Recursos {
    public static void main(String[] args) {
        try (Recurso a = new Recurso("a"); Recurso b = new Recurso("b")) {
            System.out.println("corpo");
        }
        System.out.println("depois");

        try (var c = new Recurso("c")) {
            System.out.println("vai falhar");
            throw new RuntimeException("falhou");
        } catch (RuntimeException | Error e) {
            System.out.println("catch " + e.getMessage());
        } finally {
            System.out.println("finally");
        }
    }
}

class Recurso implements AutoCloseable {
    private String nome;

    public Recurso(String nome) {
        this.nome = nome;
    }

    public void close() {
        System.out.println("fecha " + nome);
    }
}
