"""Erros do transpilador."""

from __future__ import annotations


class TranspileError(Exception):
    """Erro léxico, sintático ou semântico com posição no arquivo."""

    def __init__(self, message: str, line: int = 0, col: int = 0, filename: str = ""):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.filename = filename

    def with_file(self, filename: str) -> "TranspileError":
        if not self.filename:
            self.filename = filename
        return self

    def __str__(self) -> str:
        where = ""
        if self.filename:
            where += self.filename
        if self.line:
            where += f":{self.line}"
            if self.col:
                where += f":{self.col}"
        if where:
            return f"{where}: {self.message}"
        return self.message
