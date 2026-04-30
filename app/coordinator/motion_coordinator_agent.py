class MotionCoordinatorAgent:
    def __init__(
        self,
        config: dict,
        board_positions: dict,
        llm=None,
        fallback_enabled: bool = False,
    ) -> None:
        self.config = config
        self.board_positions = board_positions
        self.llm = llm
        self.fallback_enabled = fallback_enabled

    def build_plan(self, intention: dict, proposals: list[dict], state: dict) -> dict:
        position_error = self._validate_positions(intention)
        if position_error:
            return {
                "status": "blocked",
                "message": position_error,
                "steps": [],
            }

        conflicts = self._detect_conflicts(proposals)
        if conflicts:
            return {
                "status": "blocked",
                "message": "; ".join(conflicts),
                "steps": [],
            }

        origin = intention["origin"]
        destination = intention["destination"]
        if intention.get("move_type") == "capture":
            steps = self._capture_steps(origin, destination)
        else:
            steps = self._normal_steps(origin, destination)

        coordinator_review = self._coordinate_with_qwen(
            intention=intention,
            proposals=proposals,
            steps=steps,
        )
        if coordinator_review and coordinator_review.get("approved") is False:
            return {
                "status": "blocked",
                "message": coordinator_review.get("reason", "MotionCoordinatorAgent rejeitou o plano."),
                "origin": origin,
                "destination": destination,
                "move_type": intention.get("move_type", "normal"),
                "joint_proposals": proposals,
                "coordinator_agent": coordinator_review,
                "steps": [],
            }

        return {
            "status": "ready",
            "message": "Plano coordenado com sucesso.",
            "origin": origin,
            "destination": destination,
            "move_type": intention.get("move_type", "normal"),
            "joint_proposals": proposals,
            "coordinator_agent": coordinator_review or {
                "approved": True,
                "reason": "Coordenacao deterministica usada como fallback.",
                "risk": "low",
                "llm_used": False,
            },
            "steps": steps,
        }

    def _coordinate_with_qwen(
        self,
        intention: dict,
        proposals: list[dict],
        steps: list[dict],
    ) -> dict | None:
        if not self.llm:
            if self.fallback_enabled:
                return None
            return {
                "approved": False,
                "reason": "Qwen/Ollama nao esta disponivel para o MotionCoordinatorAgent.",
                "risk": "high",
                "llm_used": False,
            }

        review = self.llm.coordinate_motion_plan(
            intention=intention,
            proposals=proposals,
            step_names=[step["name"] for step in steps],
        )
        if not review:
            if self.fallback_enabled:
                return None
            return {
                "approved": False,
                "reason": "Qwen/Ollama nao respondeu ao MotionCoordinatorAgent.",
                "risk": "high",
                "llm_used": False,
            }

        review["llm_used"] = True
        review["agent"] = "MotionCoordinatorAgent"
        return review

    def _normal_steps(self, origin: str, destination: str) -> list[dict]:
        return [
            self._go_home_step(),
            self._move_to_step("move_to_source_above", origin, "ABOVE"),
            self._gripper_step("open_gripper", "open"),
            self._move_to_step("move_to_source_pick", origin, "PICK"),
            self._gripper_step("close_gripper", "close"),
            self._move_to_step("lift_piece", origin, "ABOVE"),
            self._move_to_step("move_to_destination_above", destination, "ABOVE"),
            self._move_to_step("move_to_destination_drop", destination, "DROP"),
            self._gripper_step("open_gripper", "open"),
            self._move_to_step("clear_destination", destination, "ABOVE"),
            self._go_home_step(),
        ]

    def _capture_steps(self, origin: str, destination: str) -> list[dict]:
        return [
            self._go_home_step(),
            self._move_to_step("move_to_captured_above", destination, "ABOVE"),
            self._gripper_step("open_gripper", "open"),
            self._move_to_step("move_to_captured_pick", destination, "PICK"),
            self._gripper_step("close_gripper", "close"),
            self._move_to_step("lift_captured_piece", destination, "ABOVE"),
            self._capture_zone_step(),
            self._gripper_step("release_captured_piece", "open"),
            self._move_to_step("move_to_source_above", origin, "ABOVE"),
            self._move_to_step("move_to_source_pick", origin, "PICK"),
            self._gripper_step("close_gripper", "close"),
            self._move_to_step("lift_piece", origin, "ABOVE"),
            self._move_to_step("move_to_destination_above", destination, "ABOVE"),
            self._move_to_step("move_to_destination_drop", destination, "DROP"),
            self._gripper_step("open_gripper", "open"),
            self._move_to_step("clear_destination", destination, "ABOVE"),
            self._go_home_step(),
        ]

    def _validate_positions(self, intention: dict) -> str | None:
        squares = self.board_positions["squares"]
        origin = intention["origin"]
        destination = intention["destination"]
        if origin not in squares:
            return (
                f"Posicao de origem sem calibracao: {origin}. "
                "Adicione essa casa em app/data/board_positions.json."
            )
        if destination not in squares:
            return (
                f"Posicao de destino sem calibracao: {destination}. "
                "Adicione essa casa em app/data/board_positions.json."
            )
        if intention.get("move_type") == "capture" and "CAPTURE_ZONE" not in self.board_positions:
            return "CAPTURE_ZONE sem calibracao em app/data/board_positions.json."
        return None

    def _go_home_step(self) -> dict:
        return {
            "name": "go_home",
            "target": {
                "type": "pose",
                "label": "HOME",
                "servos": self.board_positions["HOME"],
            },
        }

    def _move_to_step(self, name: str, square: str, height: str) -> dict:
        label = f"{square}_{height}"
        return {
            "name": name,
            "target": {
                "type": "pose",
                "label": label,
                "square": square,
                "height": height,
                "servos": self.board_positions["squares"][square][height],
            },
        }

    def _capture_zone_step(self) -> dict:
        return {
            "name": "move_to_capture_zone",
            "target": {
                "type": "pose",
                "label": "CAPTURE_ZONE",
                "servos": self.board_positions["CAPTURE_ZONE"],
            },
        }

    def _gripper_step(self, name: str, action: str) -> dict:
        angle = 80 if action == "open" else 25
        return {
            "name": name,
            "target": {
                "type": "gripper",
                "action": action,
                "angle": angle,
            },
        }

    def _detect_conflicts(self, proposals: list[dict]) -> list[str]:
        by_joint = {proposal["joint"]: proposal for proposal in proposals}
        conflicts = []

        shoulder = by_joint.get("shoulder", {}).get("angle")
        elbow = by_joint.get("elbow", {}).get("angle")
        if shoulder is not None and elbow is not None:
            if shoulder < 45 and elbow > 135:
                conflicts.append(
                    "Movimento bloqueado: ombro muito baixo com cotovelo muito esticado."
                )

        return conflicts
