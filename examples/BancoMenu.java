import java.util.ArrayList;
import java.util.Scanner;

public class BancoMenu {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        ArrayList<Conta> contas = new ArrayList<>();
        contas.add(new Conta("Ana", 100.0));
        contas.add(new ContaCorrente("Bia", 200.0, 50.0));

        int opcao = -1;
        while (opcao != 0) {
            System.out.println("1=listar 2=sacar 0=sair");
            opcao = sc.nextInt();

            switch (opcao) {
                case 1:
                    for (Conta c : contas) {
                        System.out.println(c.descricao());
                    }
                    break;
                case 2:
                    try {
                        contas.get(0).sacar(150.0);
                    } catch (SaldoInsuficienteException e) {
                        System.out.println("erro: " + e.getMessage());
                    } finally {
                        System.out.println("fim da operacao");
                    }
                    break;
                case 0:
                    break;
                default:
                    System.out.println("opcao invalida");
            }
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

class SaldoInsuficienteException extends RuntimeException {
    public SaldoInsuficienteException(String mensagem) {
        super(mensagem);
    }
}
