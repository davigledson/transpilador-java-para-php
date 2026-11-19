<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de java.util.HashMap.
 *
 * Chaves escalares são comparadas por valor; objetos usam identidade
 * (spl_object_id), não equals().
 */
final class JHashMap
{
    private array $values = [];
    private array $keys = [];

    private function encodeKey(mixed $key): string
    {
        if (is_object($key)) {
            return 'o:' . spl_object_id($key);
        }
        if (is_bool($key)) {
            return 'b:' . ($key ? '1' : '0');
        }
        if ($key === null) {
            return 'n:';
        }
        if (is_int($key)) {
            return 'i:' . $key;
        }
        if (is_float($key)) {
            return 'f:' . $key;
        }
        return 's:' . $key;
    }

    public function put(mixed $key, mixed $value): mixed
    {
        $encoded = $this->encodeKey($key);
        $old = $this->values[$encoded] ?? null;
        $this->values[$encoded] = $value;
        $this->keys[$encoded] = $key;
        return $old;
    }

    public function get(mixed $key): mixed
    {
        return $this->values[$this->encodeKey($key)] ?? null;
    }

    public function containsKey(mixed $key): bool
    {
        return array_key_exists($this->encodeKey($key), $this->values);
    }

    public function containsValue(mixed $value): bool
    {
        return in_array($value, $this->values, true);
    }

    public function remove(mixed $key): mixed
    {
        $encoded = $this->encodeKey($key);
        if (!array_key_exists($encoded, $this->values)) {
            return null;
        }
        $old = $this->values[$encoded];
        unset($this->values[$encoded], $this->keys[$encoded]);
        return $old;
    }

    public function size(): int
    {
        return count($this->values);
    }

    public function isEmpty(): bool
    {
        return $this->values === [];
    }

    public function clear(): void
    {
        $this->values = [];
        $this->keys = [];
    }

    public function keySet(): JHashSet
    {
        return new JHashSet(array_values($this->keys));
    }

    public function values(): JArrayList
    {
        return new JArrayList(array_values($this->values));
    }

    public function toString(): string
    {
        $parts = [];
        foreach ($this->values as $encoded => $value) {
            $parts[] = JString::valueOf($this->keys[$encoded])
                . '=' . JString::valueOf($value);
        }
        return '{' . implode(', ', $parts) . '}';
    }
}
