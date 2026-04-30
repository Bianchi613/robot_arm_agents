class MockRobot:
    def __init__(self) -> None:
        self.servos = {
            "base": 90,
            "shoulder": 90,
            "elbow": 90,
            "wrist": 90,
            "gripper": 80,
        }
        self.current_label = "HOME"
        self.current_square = None
        self.current_height = None
        self.holding_piece = False
        self.held_piece_origin = None
        self.held_piece = None
        self.captured_pieces = []
        self.board = self._build_initial_board()

    def _build_initial_board(self) -> dict:
        board = {
            f"{column}{row}": None
            for column in "ABCDEFGH"
            for row in range(1, 9)
        }
        back_rank = {
            "A": "rook",
            "B": "knight",
            "C": "bishop",
            "D": "queen",
            "E": "king",
            "F": "bishop",
            "G": "knight",
            "H": "rook",
        }
        for column in "ABCDEFGH":
            board[f"{column}1"] = f"white_{back_rank[column]}"
            board[f"{column}2"] = "white_pawn"
            board[f"{column}7"] = "black_pawn"
            board[f"{column}8"] = f"black_{back_rank[column]}"
        return board

    def get_state(self) -> dict:
        return {
            "mode": "mock",
            "servos": self.servos.copy(),
            "position": {
                "label": self.current_label,
                "square": self.current_square,
                "height": self.current_height,
            },
            "sensors": {
                "collision": False,
                "holding_piece": self.holding_piece,
            },
            "board": self.board.copy(),
            "captured_pieces": list(self.captured_pieces),
        }

    def execute(self, plan: dict) -> dict:
        board_before = self.board.copy()
        preflight_error = self._preflight(plan)
        if preflight_error:
            return {
                "executed": False,
                "executed_steps": [],
                "history": [],
                "peca_movida": False,
                "origem": plan.get("origin"),
                "destino": plan.get("destination"),
                "holding_piece": self.holding_piece,
                "status": "blocked",
                "message": preflight_error,
                "board_before": board_before,
                "board_after": self.board.copy(),
                "captured_pieces": list(self.captured_pieces),
                "state": self.get_state(),
            }

        executed_steps = []
        history = []

        for step in plan["steps"]:
            target = step["target"]
            if target["type"] == "pose":
                self._move_to_pose(target)
                executed_steps.append(target["label"])
                history.append(self._snapshot(step["name"]))
                continue

            if target["type"] == "gripper":
                self._move_gripper(target, plan)
                executed_steps.append(f"gripper:{target['action']}")
                history.append(self._snapshot(step["name"]))

        origin = plan.get("origin")
        destination = plan.get("destination")
        piece_moved = bool(
            origin
            and destination
            and self.board.get(origin) is None
            and self.board.get(destination) is not None
            and not self.holding_piece
        )
        return {
            "executed": True,
            "executed_steps": executed_steps,
            "history": history,
            "peca_movida": piece_moved,
            "origem": origin,
            "destino": destination,
            "holding_piece": self.holding_piece,
            "status": "ok" if piece_moved else "warning",
            "board_before": board_before,
            "board_after": self.board.copy(),
            "captured_pieces": list(self.captured_pieces),
            "state": self.get_state(),
        }

    def _preflight(self, plan: dict) -> str | None:
        origin = plan.get("origin")
        destination = plan.get("destination")
        if origin not in self.board:
            return f"Origem ausente no tabuleiro simulado: {origin}"
        if destination not in self.board:
            return f"Destino ausente no tabuleiro simulado: {destination}"
        if self.board.get(origin) is None:
            return f"Nao existe peca na origem: {origin}"
        if plan.get("move_type") == "capture":
            if self.board.get(destination) is None:
                return f"Nao existe peca para capturar em: {destination}"
            return None
        if self.board.get(destination) is not None:
            return f"Destino ocupado: {destination}"
        return None

    def _move_to_pose(self, target: dict) -> None:
        for joint, angle in target["servos"].items():
            self.servos[joint] = angle
        self.current_label = target["label"]
        self.current_square = target.get("square")
        self.current_height = target.get("height")

    def _move_gripper(self, target: dict, plan: dict) -> None:
        self.servos["gripper"] = target["angle"]
        if target["action"] == "close":
            self._try_pick_piece(plan)
        elif target["action"] == "open":
            self._try_drop_piece(plan.get("destination"))

    def _try_pick_piece(self, plan: dict) -> None:
        square = plan.get("origin")
        if plan.get("move_type") == "capture" and self.current_square == plan.get("destination"):
            square = plan.get("destination")

        if self.current_square != square or self.current_height != "PICK":
            return
        if self.board.get(square) is None:
            return
        self.held_piece_origin = square
        self.held_piece = self.board[square]
        self.board[square] = None
        self.holding_piece = True

    def _try_drop_piece(self, destination: str | None) -> None:
        if not self.holding_piece:
            return
        if self.current_label == "CAPTURE_ZONE":
            self.captured_pieces.append(self.held_piece)
            self.holding_piece = False
            self.held_piece_origin = None
            self.held_piece = None
            return
        if self.current_square != destination or self.current_height != "DROP":
            return
        self.board[destination] = getattr(self, "held_piece", "piece")
        self.holding_piece = False
        self.held_piece_origin = None
        self.held_piece = None

    def _snapshot(self, step_name: str) -> dict:
        return {
            "step": step_name,
            "position": self.current_label,
            "holding_piece": self.holding_piece,
            "board": self.board.copy(),
        }
