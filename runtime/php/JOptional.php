<?php
declare(strict_types=1);

/** Equivalente mínimo de java.util.Optional. */
final class JOptional
{
    private function __construct(
        private bool $present,
        private mixed $value,
    ) {
    }

    public static function of(mixed $value): self
    {
        if ($value === null) {
            throw new RuntimeException('NullPointerException: Optional.of(null)');
        }
        return new self(true, $value);
    }

    public static function ofNullable(mixed $value): self
    {
        return new self($value !== null, $value);
    }

    public static function empty(): self
    {
        return new self(false, null);
    }

    public function isPresent(): bool
    {
        return $this->present;
    }

    public function isEmpty(): bool
    {
        return !$this->present;
    }

    public function get(): mixed
    {
        if (!$this->present) {
            throw new RuntimeException('NoSuchElementException: Optional vazio');
        }
        return $this->value;
    }

    public function orElse(mixed $other): mixed
    {
        return $this->present ? $this->value : $other;
    }

    public function orElseThrow(): mixed
    {
        return $this->get();
    }

    public function ifPresent(callable $consumer): void
    {
        if ($this->present) {
            $consumer($this->value);
        }
    }

    public function toString(): string
    {
        return $this->present ? 'Optional[' . JString::valueOf($this->value) . ']' : 'Optional.empty';
    }

    public function __toString(): string
    {
        return $this->toString();
    }
}
