<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de java.lang.Class.
 * Não há reflection completa: só nome, nome simples e isInstance.
 */
final class JClass
{
    private const PRIMITIVES = [
        'int',
        'double',
        'boolean',
        'char',
        'void',
        'long',
        'float',
        'byte',
        'short',
    ];

    private string $name;

    public function __construct(string $name)
    {
        $this->name = ltrim($name, '\\');
    }

    public static function of(string $name): self
    {
        return new self($name);
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function getCanonicalName(): string
    {
        return $this->name;
    }

    public function getSimpleName(): string
    {
        $position = strrpos($this->name, '\\');
        if ($position === false) {
            return $this->name;
        }
        return substr($this->name, $position + 1);
    }

    public function isInstance(mixed $value): bool
    {
        if (in_array($this->name, self::PRIMITIVES, true)) {
            return false;
        }
        if ($this->name === 'String') {
            return is_string($value);
        }
        if ($this->name === 'array') {
            return is_array($value);
        }
        $class = $this->name;
        return $value instanceof $class;
    }

    public function toString(): string
    {
        if (in_array($this->name, self::PRIMITIVES, true)) {
            return $this->name;
        }
        return 'class ' . $this->name;
    }

    public function __toString(): string
    {
        return $this->toString();
    }
}
