public class Excecoes {
    public static void main(String[] args) {
        Conta c = new Conta("Ana", 100.0);

        try {
            c.sacar(150.0);
            System.out.println("saque ok");
        } catch (SaldoInsuficienteException e) {
            System.out.println("erro: " + e.getMessage());
        } finally {
            System.out.println("saldo=" + c.getSaldo());
        }

        try {
            c.sacar(30.0);
            System.out.println("saque2 ok");
        } catch (RuntimeException e) {
            System.out.println("runtime: " + e.getMessage());
        } finally {
            System.out.println("fim");
        }
    }
}

class SaldoInsuficienteException extends RuntimeException {
    public SaldoInsuficienteException(String mensagem) {
        super(mensagem);
    }
}

class Conta {
    private String titular;
    private double saldo;

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

    public double getSaldo() {
        return saldo;
    }
}
