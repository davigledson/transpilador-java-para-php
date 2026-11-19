package model;

import error.SaldoInsuficienteException;

public class Conta {
    protected String titular;
    protected double saldo;

    public Conta(String titular, double saldo) {
        this.titular = titular;
        this.saldo = saldo;
    }

    public void sacar(double valor) throws SaldoInsuficienteException {
        if (valor > saldo) {
            throw new SaldoInsuficienteException("saldo insuficiente para " + titular);
        }
        saldo -= valor;
    }

    public String descricao() {
        return titular + ": " + saldo;
    }
}
