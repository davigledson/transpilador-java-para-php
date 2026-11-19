<?php
declare(strict_types=1);

interface AutoCloseable
{
    public function close(): void;
}

interface Closeable extends AutoCloseable
{
}
