import java.util.ArrayList;
import java.util.List;

public class BancoLista {
    public static void main(String[] args) {
        List<Conta> contas = new ArrayList<>();
        contas.add(new Conta("Ana", 100.0));
        contas.add(new Conta("Bia", 250.0));
        contas.add(new ContaCorrente("Caio", 300.0, 100.0));

        double total = 0.0;
        for (Conta c : contas) {
            c.depositar(10.0);
            total += c.getSaldo();
            System.out.println(c.getTitular() + ": " + c.getSaldo());
        }
        System.out.println("Total: " + total + " / contas=" + contas.size());
    }
}

class Conta {
    protected String titular;
    protected double saldo;

    public Conta(String titular, double saldo) {
        this.titular = titular;
        this.saldo = saldo;
    }

    public void depositar(double valor) {
        this.saldo += valor;
    }

    public String getTitular() {
        return this.titular;
    }

    public double getSaldo() {
        return this.saldo;
    }
}

class ContaCorrente extends Conta {
    private double limite;

    public ContaCorrente(String titular, double saldo, double limite) {
        super(titular, saldo);
        this.limite = limite;
    }
}
