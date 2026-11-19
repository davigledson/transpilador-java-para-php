<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de java.util.stream.Stream.
 *
 * Implementação eager (arrays), suficiente para o subconjunto do projeto.
 */
final class JStream implements IteratorAggregate
{
    private array $items;

    public function __construct(iterable $items = [])
    {
        if (is_array($items)) {
            $this->items = array_values($items);
        } else {
            $this->items = iterator_to_array($items, false);
        }
    }

    public function filter(callable $predicate): JStream
    {
        $result = [];
        foreach ($this->items as $item) {
            if ($predicate($item)) {
                $result[] = $item;
            }
        }
        return new self($result);
    }

    public function map(callable $mapper): JStream
    {
        $result = [];
        foreach ($this->items as $item) {
            $result[] = $mapper($item);
        }
        return new self($result);
    }

    public function forEach(callable $consumer): void
    {
        foreach ($this->items as $item) {
            $consumer($item);
        }
    }

    public function count(): int
    {
        return count($this->items);
    }

    public function anyMatch(callable $predicate): bool
    {
        foreach ($this->items as $item) {
            if ($predicate($item)) {
                return true;
            }
        }
        return false;
    }

    public function allMatch(callable $predicate): bool
    {
        foreach ($this->items as $item) {
            if (!$predicate($item)) {
                return false;
            }
        }
        return true;
    }

    public function noneMatch(callable $predicate): bool
    {
        return !$this->anyMatch($predicate);
    }

    public function limit(int $max): JStream
    {
        return new self(array_slice($this->items, 0, max(0, $max)));
    }

    public function sorted(): JStream
    {
        $copy = $this->items;
        sort($copy);
        return new self($copy);
    }

    public function toList(): JArrayList
    {
        return new JArrayList($this->items);
    }

    public function getIterator(): Iterator
    {
        return new ArrayIterator($this->items);
    }
}
