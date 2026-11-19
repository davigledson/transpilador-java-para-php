public class HerancaConta {
    public static void main(String[] args) {
        Conta[] contas = new Conta[3];
        contas[0] = new Conta("Ana", 100.0);
        contas[1] = new ContaCorrente("Bia", 200.0, 50.0);
        contas[2] = new ContaCorrente("Caio", 300.0, 100.0);

        for (int i = 0; i < contas.length; i++) {
            contas[i].depositar(10.0);
            System.out.println(contas[i].descricao());
        }
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

    public String descricao() {
        return titular + ": " + saldo;
    }
}

class ContaCorrente extends Conta {
    private double limite;

    public ContaCorrente(String titular, double saldo, double limite) {
        super(titular, saldo);
        this.limite = limite;
    }

    @Override
    public String descricao() {
        return super.descricao() + " (limite " + limite + ")";
    }
}
