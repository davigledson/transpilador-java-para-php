public class Escolhas {
    public static void main(String[] args) {
        for (int i = 1; i <= 4; i++) {
            switch (i) {
                case 1:
                    System.out.println("um");
                    break;
                case 2:
                case 3:
                    System.out.println("dois ou tres");
                    break;
                default:
                    System.out.println("outro");
            }
        }

        String s = "b";
        switch (s) {
            case "a":
                System.out.println("A");
                break;
            case "b":
                System.out.println("B");
                break;
            default:
                System.out.println("?");
        }
    }
}
