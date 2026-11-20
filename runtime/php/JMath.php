<?php
declare(strict_types=1);

/** Funções de Math que não têm equivalente direto em PHP. */
final class JMath
{
    public static function floorDiv(int|float $a, int|float $b): int|float
    {
        return (int) floor($a / $b);
    }

    public static function floorMod(int $a, int $b): int
    {
        return $a - self::floorDiv($a, $b) * $b;
    }

    public static function ceilDiv(int $a, int $b): int
    {
        return (int) ceil($a / $b);
    }

    public static function signum(int|float $value): float
    {
        return (float) ($value <=> 0);
    }

    public static function clamp(int|float $value, int|float $min, int|float $max): int|float
    {
        return max($min, min($max, $value));
    }
}
