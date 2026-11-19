public class Banco {
    static final int TOTAL = 3;

    public static void main(String[] args) {
        Conta[] contas = new Conta[TOTAL];
        contas[0] = new Conta("Ana", 100.0);
        contas[1] = new Conta("Bia", 250.0);
        contas[2] = new Conta("Caio", 40.0);

        double total = 0.0;
        for (int i = 0; i < contas.length; i++) {
            contas[i].depositar(10.0);
            total += contas[i].getSaldo();
            System.out.println(contas[i].getTitular() + ": " + contas[i].getSaldo());
        }
        System.out.println("Total: " + total);
    }
}

class Conta {
    private String titular;
    private double saldo;

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
