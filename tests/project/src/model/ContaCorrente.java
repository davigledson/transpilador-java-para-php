package model;

public class ContaCorrente extends Conta {
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
