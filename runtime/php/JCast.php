<?php
declare(strict_types=1);

/**
 * Casts de referência com checagem de tipo em runtime.
 */
final class JCast
{
    public static function to(mixed $value, string $class): mixed
    {
        if ($value === null) {
            return null;
        }
        if (!($value instanceof $class)) {
            throw new TypeError('ClassCastException: esperado ' . $class);
        }
        return $value;
    }

    public static function toString(mixed $value): ?string
    {
        if ($value === null) {
            return null;
        }
        if (!is_string($value)) {
            throw new TypeError('ClassCastException: esperado string');
        }
        return $value;
    }

    public static function toArray(mixed $value): array
    {
        if (!is_array($value)) {
            throw new TypeError('ClassCastException: esperado array');
        }
        return $value;
    }
}
