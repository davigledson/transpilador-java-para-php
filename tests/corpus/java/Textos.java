public class Textos {
    public static void main(String[] args) {
        String s = "  Transpilador Java  ";
        System.out.println(s.trim());
        System.out.println(s.trim().toUpperCase());
        System.out.println("tamanho=" + s.length());
        System.out.println(s.indexOf("Java"));
        System.out.println(s.contains("PHP"));
        System.out.println(s.substring(2, 14));
    }
}
