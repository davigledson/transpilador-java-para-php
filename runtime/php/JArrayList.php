<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de java.util.ArrayList.
 */
final class JArrayList implements IteratorAggregate
{
    private array $items = [];

    public function __construct(array $items = [])
    {
        $this->items = array_values($items);
    }

    public static function of(mixed ...$items): self
    {
        return new self($items);
    }

    public function add(mixed $value): bool
    {
        $this->items[] = $value;
        return true;
    }

    public function addAt(int $index, mixed $value): void
    {
        if ($index < 0 || $index > count($this->items)) {
            throw new RuntimeException('IndexOutOfBoundsException: ' . $index);
        }
        array_splice($this->items, $index, 0, [$value]);
    }

    public function get(int $index): mixed
    {
        if (!array_key_exists($index, $this->items)) {
            throw new RuntimeException('IndexOutOfBoundsException: ' . $index);
        }
        return $this->items[$index];
    }

    public function set(int $index, mixed $value): mixed
    {
        if (!array_key_exists($index, $this->items)) {
            throw new RuntimeException('IndexOutOfBoundsException: ' . $index);
        }
        $old = $this->items[$index];
        $this->items[$index] = $value;
        return $old;
    }

    public function size(): int
    {
        return count($this->items);
    }

    public function isEmpty(): bool
    {
        return $this->items === [];
    }

    public function contains(mixed $value): bool
    {
        return in_array($value, $this->items, true);
    }

    public function removeAt(int $index): mixed
    {
        if (!array_key_exists($index, $this->items)) {
            throw new RuntimeException('IndexOutOfBoundsException: ' . $index);
        }
        $removed = array_splice($this->items, $index, 1);
        return $removed[0] ?? null;
    }

    public function removeValue(mixed $value): bool
    {
        foreach ($this->items as $index => $item) {
            if ($item === $value) {
                array_splice($this->items, $index, 1);
                return true;
            }
        }
        return false;
    }

    public function clear(): void
    {
        $this->items = [];
    }

    public function indexOf(mixed $value): int
    {
        foreach ($this->items as $index => $item) {
            if ($item === $value) {
                return $index;
            }
        }
        return -1;
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

    public function stream(): JStream
    {
        return new JStream($this->items);
    }

    public function forEach(callable $consumer): void
    {
        foreach ($this->items as $item) {
            $consumer($item);
        }
    }

    public function removeIf(callable $predicate): bool
    {
        $changed = false;
        $kept = [];
        foreach ($this->items as $item) {
            if ($predicate($item)) {
                $changed = true;
            } else {
                $kept[] = $item;
            }
        }
        $this->items = $kept;
        return $changed;
    }
}
