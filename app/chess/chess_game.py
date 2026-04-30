from __future__ import annotations

import chess


class ChessGame:
    def __init__(self, llm=None, fallback_enabled: bool = True) -> None:
        self.board = chess.Board()
        self.llm = llm
        self.fallback_enabled = fallback_enabled

    def validate_command(self, command: str) -> dict:
        try:
            qwen_parsed = self._parse_command_with_qwen(command)
            if qwen_parsed:
                origin, destination, expected_piece_type, expected_piece_color = qwen_parsed
            else:
                origin, destination, expected_piece_type, expected_piece_color = self._parse_command(command)
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
        actual_piece_type = self._piece_type(moving_piece)
        if expected_piece_type and expected_piece_type != actual_piece_type:
            return {
                "status": "rejected",
                "message": (
                    f"Peca declarada nao confere: voce informou {expected_piece_type}, "
                    f"mas em {origin} existe {self._piece_label(moving_piece)}."
                ),
            }
        actual_piece_color = self._piece_color(moving_piece)
        if expected_piece_color != actual_piece_color:
            return {
                "status": "rejected",
                "message": (
                    f"Cor declarada nao confere: voce informou {expected_piece_color}, "
                    f"mas em {origin} existe {self._piece_label(moving_piece)}."
                ),
            }

        return self._apply_move(
            move=move,
            normal_message="Lance normal validado pelo ChessGame.",
            capture_message="Captura validada pelo ChessGame.",
        )

    def choose_agent_move(self) -> dict:
        if self.board.is_game_over():
            return {
                "status": "rejected",
                "message": "A partida ja terminou.",
            }

        move, decision_source, decision_reason = self._select_agent_move()
        result = self._apply_move(
            move=move,
            normal_message="Jogada de resposta escolhida pelo ChessGame.",
            capture_message="Captura de resposta escolhida pelo ChessGame.",
        )
        result["decision_source"] = decision_source
        result["decision_reason"] = decision_reason
        return result

    def _select_agent_move(self) -> tuple[chess.Move, str, str]:
        legal_moves = list(self.board.legal_moves)
        qwen_move, qwen_reason = self._select_qwen_agent_move(legal_moves)
        if qwen_move:
            return qwen_move, "qwen2.5-coder:7b", qwen_reason
        if not self.fallback_enabled:
            raise RuntimeError("Qwen/Ollama nao escolheu jogada e fallback esta desativado.")

        preferred_moves = [
            "e7e5",
            "d7d5",
            "g8f6",
            "b8c6",
            "c7c5",
            "e7e6",
            "d7d6",
            "a7a6",
        ]
        legal_by_uci = {move.uci(): move for move in legal_moves}
        for move_uci in preferred_moves:
            if move_uci in legal_by_uci:
                return legal_by_uci[move_uci], "fallback_rule", "Primeira jogada preferida disponivel."
        return (
            sorted(legal_moves, key=lambda legal_move: legal_move.uci())[0],
            "fallback_rule",
            "Primeira jogada legal em ordem alfabetica.",
        )

    def _select_qwen_agent_move(self, legal_moves: list[chess.Move]) -> tuple[chess.Move | None, str]:
        if not self.llm:
            return None, ""

        legal_by_uci = {move.uci(): move for move in legal_moves}
        response = self.llm.choose_chess_move(
            board_fen=self.board.fen(),
            legal_moves=list(legal_by_uci.keys()),
        )
        if not response:
            return None, ""

        move_uci = str(response.get("move", "")).lower()
        return legal_by_uci.get(move_uci), response.get("reason", "Jogada escolhida pelo Qwen.")

    def _parse_command_with_qwen(self, command: str) -> tuple[str, str, str, str] | None:
        if not self.llm:
            return None

        parsed = self.llm.generate_json(
            "Voce e um agente interpretador de comandos de xadrez. "
            "Converta o comando em JSON puro, sem markdown. "
            "Formato obrigatorio: {\"origin\":\"A2\",\"destination\":\"A4\","
            "\"piece_type\":\"pawn\",\"piece_color\":\"white\"}. "
            "piece_type pode ser pawn, knight, bishop, rook, queen, king. "
            "piece_color pode ser white ou black. "
            "Se o comando nao informar tipo e cor da peca, responda {\"error\":\"missing_piece_identity\"}. "
            f"Comando: {command}"
        )
        if not parsed:
            return None
        if parsed.get("error"):
            return None

        origin = str(parsed.get("origin", "")).upper()
        destination = str(parsed.get("destination", "")).upper()
        expected_piece_type = str(parsed.get("piece_type", "")).lower()
        expected_piece_color = str(parsed.get("piece_color", "")).lower()
        if expected_piece_type not in {"pawn", "knight", "bishop", "rook", "queen", "king"}:
            return None
        if expected_piece_color not in {"white", "black"}:
            return None

        self._validate_square(origin)
        self._validate_square(destination)
        return origin, destination, expected_piece_type, expected_piece_color

    def _apply_move(
        self,
        move: chess.Move,
        normal_message: str,
        capture_message: str,
    ) -> dict:
        origin = chess.square_name(move.from_square).upper()
        destination = chess.square_name(move.to_square).upper()
        moving_piece = self.board.piece_at(move.from_square)
        captured_piece = self.board.piece_at(move.to_square)
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
                    "message": capture_message,
                    "captured_square": destination,
                    "captured_piece_color": self._piece_color(captured_piece),
                    "captured_piece_type": self._piece_type(captured_piece),
                    "captured_piece": self._piece_label(captured_piece),
                }
            )
            return result

        result["message"] = normal_message
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

    def _parse_command(self, command: str) -> tuple[str, str, str, str]:
        parts = command.strip().upper().split()
        if len(parts) == 5 and parts[0] == "MOVER":
            expected_piece_type = self._normalize_piece_name(parts[1])
            expected_piece_color = self._normalize_color_name(parts[2])
            origin, destination = parts[3], parts[4]
        else:
            raise ValueError("Use o formato: mover peao branco A2 A4")

        self._validate_square(origin)
        self._validate_square(destination)
        return origin, destination, expected_piece_type, expected_piece_color

    def _normalize_piece_name(self, piece_name: str) -> str:
        names = {
            "PEAO": "pawn",
            "PEÃO": "pawn",
            "PAWN": "pawn",
            "CAVALO": "knight",
            "KNIGHT": "knight",
            "BISPO": "bishop",
            "BISHOP": "bishop",
            "TORRE": "rook",
            "ROOK": "rook",
            "RAINHA": "queen",
            "DAMA": "queen",
            "QUEEN": "queen",
            "REI": "king",
            "KING": "king",
        }
        if piece_name not in names:
            raise ValueError(f"Tipo de peca desconhecido: {piece_name}")
        return names[piece_name]

    def _normalize_color_name(self, color_name: str) -> str:
        names = {
            "BRANCO": "white",
            "BRANCA": "white",
            "WHITE": "white",
            "PRETO": "black",
            "PRETA": "black",
            "BLACK": "black",
        }
        if color_name not in names:
            raise ValueError(f"Cor de peca desconhecida: {color_name}")
        return names[color_name]

    def _validate_square(self, square: str) -> None:
        if len(square) != 2:
            raise ValueError(f"Casa invalida: {square}")

        column = square[0]
        row = square[1]
        if column < "A" or column > "H" or row < "1" or row > "8":
            raise ValueError(f"Casa fora do tabuleiro: {square}")
