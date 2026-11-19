import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

interface Funcionario {
    String nome();
    double salario();
}

abstract class Pessoa implements Funcionario {
    protected String nome;

    public Pessoa(String nome) {
        this.nome = nome;
    }

    public String nome() {
        return nome;
    }
}

class Analista extends Pessoa {
    private double salarioBase;

    public Analista(String nome, double salarioBase) {
        super(nome);
        this.salarioBase = salarioBase;
    }

    @Override
    public double salario() {
        return salarioBase;
    }
}

class Gerente extends Pessoa {
    private double salarioBase;
    private double bonus;

    public Gerente(String nome, double salarioBase, double bonus) {
        super(nome);
        this.salarioBase = salarioBase;
        this.bonus = bonus;
    }

    @Override
    public double salario() {
        return salarioBase + bonus;
    }
}

public class Funcionarios {
    public static void main(String[] args) {
        List<Funcionario> equipe = new ArrayList<>();
        equipe.add(new Analista("Ana", 3000.0));
        equipe.add(new Gerente("Bia", 5000.0, 1500.0));
        equipe.add(new Analista("Caio", 4500.0));

        for (Funcionario f : equipe) {
            System.out.println(f.nome() + ": " + f.salario());
        }

        List<String> bemPagos = equipe.stream()
            .filter(f -> f.salario() > 4000.0)
            .map(f -> f.nome())
            .collect(Collectors.toList());

        bemPagos.forEach(nome -> System.out.println("bem pago=" + nome));

        double total = 0.0;
        for (Funcionario f : equipe) {
            total += f.salario();
        }
        System.out.println("total=" + total);
    }
}
