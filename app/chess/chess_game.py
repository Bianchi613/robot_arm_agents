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

        moving_piece = self.board.piece_at(chess.parse_square(origin.lower()))
        captured_piece = self.board.piece_at(chess.parse_square(destination.lower()))
        is_capture = self.board.is_capture(move)
        self.board.push(move)
        result = {
            "status": "ok",
            "origin": origin,
            "destination": destination,
            "move_type": "capture" if is_capture else "normal",
            "piece_color": self._piece_color(moving_piece),
            "piece_type": self._piece_type(moving_piece),
            "piece": self._piece_label(moving_piece),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "check": self.board.is_check(),
            "checkmate": self.board.is_checkmate(),
        }

        if is_capture:
            result.update(
                {
                    "message": "Captura validada pelo ChessGame.",
                    "captured_square": destination,
                    "captured_piece_color": self._piece_color(captured_piece),
                    "captured_piece_type": self._piece_type(captured_piece),
                    "captured_piece": self._piece_label(captured_piece),
                }
            )
            return result

        result["message"] = "Lance normal validado pelo ChessGame."
        return result

    def _piece_label(self, piece: chess.Piece | None) -> str | None:
        if piece is None:
            return None
        return f"{self._piece_color(piece)}_{self._piece_type(piece)}"

    def _piece_color(self, piece: chess.Piece | None) -> str | None:
        if piece is None:
            return None
        return "white" if piece.color == chess.WHITE else "black"

    def _piece_type(self, piece: chess.Piece | None) -> str | None:
        if piece is None:
            return None
        names = {
            chess.PAWN: "pawn",
            chess.KNIGHT: "knight",
            chess.BISHOP: "bishop",
            chess.ROOK: "rook",
            chess.QUEEN: "queen",
            chess.KING: "king",
        }
        return names[piece.piece_type]

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
