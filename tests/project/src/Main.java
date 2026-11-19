package app;

import java.util.ArrayList;
import java.util.List;

import error.SaldoInsuficienteException;
import model.Conta;
import model.ContaCorrente;

public class Main {
    public static void main(String[] args) {
        List<Conta> contas = new ArrayList<>();
        contas.add(new Conta("Ana", 100.0));
        contas.add(new ContaCorrente("Bia", 200.0, 50.0));

        for (Conta c : contas) {
            System.out.println(c.descricao());
        }

        try {
            contas.get(0).sacar(150.0);
        } catch (SaldoInsuficienteException e) {
            System.out.println("erro: " + e.getMessage());
        } finally {
            System.out.println("fim");
        }
    }
}
