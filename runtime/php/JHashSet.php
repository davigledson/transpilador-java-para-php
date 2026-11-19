<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de java.util.HashSet.
 * Mantém a ordem de inserção, o que é mais previsível que o Java.
 */
final class JHashSet implements IteratorAggregate
{
    private array $items = [];

    public function __construct(array $items = [])
    {
        foreach ($items as $item) {
            $this->add($item);
        }
    }

    public function add(mixed $value): bool
    {
        if ($this->contains($value)) {
            return false;
        }
        $this->items[] = $value;
        return true;
    }

    public function contains(mixed $value): bool
    {
        return in_array($value, $this->items, true);
    }

    public function remove(mixed $value): bool
    {
        foreach ($this->items as $index => $item) {
            if ($item === $value) {
                array_splice($this->items, $index, 1);
                return true;
            }
        }
        return false;
    }

    public function size(): int
    {
        return count($this->items);
    }

    public function isEmpty(): bool
    {
        return $this->items === [];
    }

    public function clear(): void
    {
        $this->items = [];
    }

    public function toString(): string
    {
        $parts = array_map(
            static fn (mixed $item): string => JString::valueOf($item),
            $this->items,
        );
        return '[' . implode(', ', $parts) . ']';
    }

    public function getIterator(): Iterator
    {
        return new ArrayIterator($this->items);
    }
}
