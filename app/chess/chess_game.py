import chess


class ChessGame:
    def __init__(self) -> None:
        self.board = chess.Board()

    def validate_command(self, command: str) -> dict:
        try:
            origin, destination = self._parse_command(command)
        except ValueError as error:
            return {
                "status": "rejected",
                "message": str(error),
            }

        move = chess.Move.from_uci(f"{origin.lower()}{destination.lower()}")
        if move not in self.board.legal_moves:
            return {
                "status": "rejected",
                "message": f"Lance invalido no xadrez: {origin} -> {destination}",
            }

        is_capture = self.board.is_capture(move)
        self.board.push(move)
        if is_capture:
            return {
                "status": "ok",
                "message": "Captura validada pelo ChessGame.",
                "origin": origin,
                "destination": destination,
                "move_type": "capture",
                "captured_square": destination,
                "turn": "white" if self.board.turn == chess.WHITE else "black",
                "check": self.board.is_check(),
                "checkmate": self.board.is_checkmate(),
            }

        return {
            "status": "ok",
            "message": "Lance normal validado pelo ChessGame.",
            "origin": origin,
            "destination": destination,
            "move_type": "normal",
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "check": self.board.is_check(),
            "checkmate": self.board.is_checkmate(),
        }

    def _parse_command(self, command: str) -> tuple[str, str]:
        parts = command.strip().upper().split()
        if len(parts) == 2:
            origin, destination = parts
        elif len(parts) == 3 and parts[0] == "MOVER":
            origin, destination = parts[1], parts[2]
        else:
            raise ValueError("Use o formato: mover A2 A4")

        self._validate_square(origin)
        self._validate_square(destination)
        return origin, destination

    def _validate_square(self, square: str) -> None:
        if len(square) != 2:
            raise ValueError(f"Casa invalida: {square}")

        column = square[0]
        row = square[1]
        if column < "A" or column > "H" or row < "1" or row > "8":
            raise ValueError(f"Casa fora do tabuleiro: {square}")
