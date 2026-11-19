<?php
declare(strict_types=1);

/**
 * Equivalente mínimo de java.util.Scanner para stdin.
 *
 * Lê de STDIN sob demanda, com suporte a tokens e linhas.
 */
final class JScanner
{
    private string $buffer = '';
    private int $pos = 0;
    private bool $eof = false;

    public function __construct()
    {
    }

    private function readMore(): bool
    {
        if ($this->eof) {
            return false;
        }
        $line = fgets(STDIN);
        if ($line === false) {
            $this->eof = true;
            return false;
        }
        $this->buffer .= $line;
        return true;
    }

    private function skipWhitespace(): void
    {
        while (true) {
            $this->pos = min($this->pos, strlen($this->buffer));
            $length = strlen($this->buffer);
            while ($this->pos < $length && ctype_space($this->buffer[$this->pos])) {
                $this->pos++;
            }
            if ($this->pos < strlen($this->buffer) || $this->eof) {
                return;
            }
            if (!$this->readMore()) {
                return;
            }
        }
    }

    private function token(): string
    {
        $this->skipWhitespace();
        $length = strlen($this->buffer);
        if ($this->pos >= $length) {
            throw new RuntimeException('NoSuchElementException');
        }
        $start = $this->pos;
        while ($this->pos < $length && !ctype_space($this->buffer[$this->pos])) {
            $this->pos++;
        }
        return substr($this->buffer, $start, $this->pos - $start);
    }

    public function next(): string
    {
        return $this->token();
    }

    public function nextInt(): int
    {
        return (int) $this->token();
    }

    public function nextDouble(): float
    {
        return (float) $this->token();
    }

    public function nextLine(): string
    {
        if (!$this->eof && $this->pos >= strlen($this->buffer)) {
            $this->readMore();
        }
        if ($this->pos >= strlen($this->buffer) && $this->eof) {
            return '';
        }

        $newline = strpos($this->buffer, "\n", $this->pos);
        while ($newline === false && !$this->eof) {
            if (!$this->readMore()) {
                break;
            }
            $newline = strpos($this->buffer, "\n", $this->pos);
        }

        if ($newline === false) {
            $line = substr($this->buffer, $this->pos);
            $this->pos = strlen($this->buffer);
            return $line;
        }

        $line = substr($this->buffer, $this->pos, $newline - $this->pos);
        $this->pos = $newline + 1;
        return rtrim($line, "\r");
    }

    public function hasNext(): bool
    {
        if ($this->pos >= strlen($this->buffer) && !$this->eof) {
            $this->readMore();
        }
        $this->skipWhitespace();
        return $this->pos < strlen($this->buffer);
    }

    public function hasNextInt(): bool
    {
        $this->skipWhitespace();
        $rest = substr($this->buffer, $this->pos);
        return preg_match('/^[+-]?\d+/', $rest) === 1;
    }

    public function hasNextDouble(): bool
    {
        $this->skipWhitespace();
        $rest = substr($this->buffer, $this->pos);
        return preg_match('/^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?/', $rest) === 1;
    }

    public function close(): void
    {
    }
}
