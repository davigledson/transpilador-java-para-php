<?php
declare(strict_types=1);

/**
 * Emula os comportamentos de java.lang.String que diferem do PHP:
 * conversão para texto, concatenação, charAt, substring, indexOf e split.
 */
final class JString
{
    public static function valueOf(mixed $value): string
    {
        if ($value === null) {
            return 'null';
        }
        if (is_bool($value)) {
            return $value ? 'true' : 'false';
        }
        if (is_float($value)) {
            if (is_nan($value)) {
                return 'NaN';
            }
            if (is_infinite($value)) {
                return $value > 0 ? 'Infinity' : '-Infinity';
            }
            $text = (string) $value;
            if (!str_contains($text, '.') && !str_contains($text, 'e') && !str_contains($text, 'E')) {
                $text .= '.0';
            }
            return $text;
        }
        if (is_object($value)) {
            if ($value instanceof \UnitEnum) {
                return $value->name;
            }
            if (method_exists($value, '__toString')) {
                return (string) $value;
            }
            return get_class($value) . '@' . spl_object_id($value);
        }
        if (is_array($value)) {
            // Java imprime algo como [I@hash; não tentamos reproduzir.
            return 'Array';
        }
        return (string) $value;
    }

    public static function concat(mixed $left, mixed $right): string
    {
        return self::valueOf($left) . self::valueOf($right);
    }

    public static function charAt(string $text, int $index): string
    {
        if ($index < 0 || $index >= strlen($text)) {
            throw new RuntimeException('StringIndexOutOfBoundsException: ' . $index);
        }
        return $text[$index];
    }

    public static function substring(string $text, int $begin, ?int $end = null): string
    {
        $length = strlen($text);
        $end ??= $length;
        if ($begin < 0 || $end > $length || $begin > $end) {
            throw new RuntimeException('StringIndexOutOfBoundsException');
        }
        return substr($text, $begin, $end - $begin);
    }

    public static function indexOf(string $text, string $needle): int
    {
        $position = strpos($text, $needle);
        return $position === false ? -1 : $position;
    }

    public static function isBlank(string $text): bool
    {
        return preg_match('/^\s*$/u', $text) === 1;
    }

    public static function strip(string $text): string
    {
        return preg_replace('/^\s+|\s+$/u', '', $text) ?? $text;
    }

    public static function stripLeading(string $text): string
    {
        return preg_replace('/^\s+/u', '', $text) ?? $text;
    }

    public static function stripTrailing(string $text): string
    {
        return preg_replace('/\s+$/u', '', $text) ?? $text;
    }

    public static function repeat(string $text, int $count): string
    {
        if ($count < 0) {
            throw new RuntimeException('IllegalArgumentException: repeat negativo');
        }
        return str_repeat($text, $count);
    }

    public static function formatted(string $format, mixed ...$args): string
    {
        $format = str_replace('%n', PHP_EOL, $format);
        return vsprintf($format, $args);
    }

    /**
     * Java usa regex em String.split; mantemos a mesma ideia com PCRE.
     */
    public static function split(string $text, string $regex): array
    {
        $delimiter = '~' . str_replace('~', '\~', $regex) . '~';
        $parts = preg_split($delimiter, $text);
        return $parts === false ? [$text] : $parts;
    }
}
