public class Moderno {
    @SuppressWarnings({"unchecked", "rawtypes"})
    @Deprecated(since = "9", forRemoval = false)
    private String texto = """
        linha 1
        linha 2
        """;

    public static void main(String[] args) {
        Moderno m = new Moderno();
        System.out.println(m.texto);
        System.out.println("fim");
    }
}
