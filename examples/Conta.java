public class Conta {
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

    public static void main(String[] args) {
        Conta c = new Conta("Ana", 100.0);
        c.depositar(10.0);
        System.out.println(c.getTitular() + ": " + c.getSaldo());
    }
}
