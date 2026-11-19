import java.util.HashMap;
import java.util.Map;

public class MapaBanco {
    public static void main(String[] args) {
        Map<String, Conta> contas = new HashMap<>();
        contas.put("Ana", new Conta("Ana", 100.0));
        contas.put("Bia", new Conta("Bia", 250.0));
        contas.put("Ana", new Conta("Ana", 150.0));

        System.out.println("tamanho=" + contas.size());
        System.out.println("temBia=" + contas.containsKey("Bia"));
        System.out.println("saldoAna=" + contas.get("Ana").getSaldo());
        System.out.println("removida=" + contas.remove("Bia").getTitular());
        System.out.println("tamanhoFinal=" + contas.size());
    }
}

class Conta {
    private String titular;
    private double saldo;

    public Conta(String titular, double saldo) {
        this.titular = titular;
        this.saldo = saldo;
    }

    public String getTitular() {
        return titular;
    }

    public double getSaldo() {
        return saldo;
    }
}
