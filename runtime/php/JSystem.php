<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de System.out para print/println.
 */
final class JSystem
{
    public static function print(mixed $value): void
    {
        echo JString::valueOf($value);
    }

    public static function println(mixed $value = ''): void
    {
        echo JString::valueOf($value), PHP_EOL;
    }
}
