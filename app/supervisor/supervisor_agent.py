import json
import os
from pathlib import Path

from app.config.env_loader import env_bool, load_env_file
from app.coordinator.motion_coordinator_agent import MotionCoordinatorAgent
from app.joints.base_joint_agent import BaseJointAgent
from app.joints.elbow_joint_agent import ElbowJointAgent
from app.joints.gripper_agent import GripperAgent
from app.joints.shoulder_joint_agent import ShoulderJointAgent
from app.joints.wrist_joint_agent import WristJointAgent
from app.llm.ollama_client import OllamaClient
from app.robot.mock_robot import MockRobot


class SupervisorAgent:
    def __init__(self, config: dict, robot: MockRobot) -> None:
        self.config = config
        self.robot = robot
        self.llm = self._build_llm_client(config.get("llm", {}))
        self.llm_fallback_enabled = config.get("llm", {}).get(
            "fallback_to_rule_parser",
            True,
        )
        self.joint_agents = [
            BaseJointAgent(config["BaseJointAgent"], self.llm, self.llm_fallback_enabled),
            ShoulderJointAgent(config["ShoulderJointAgent"], self.llm, self.llm_fallback_enabled),
            ElbowJointAgent(config["ElbowJointAgent"], self.llm, self.llm_fallback_enabled),
            WristJointAgent(config["WristJointAgent"], self.llm, self.llm_fallback_enabled),
            GripperAgent(config["GripperAgent"], self.llm, self.llm_fallback_enabled),
        ]
        self.coordinator = MotionCoordinatorAgent(
            config["MotionCoordinatorAgent"],
            config["board_positions"],
            self.llm,
            self.llm_fallback_enabled,
        )

    @classmethod
    def from_default_config(cls) -> "SupervisorAgent":
        project_root = Path(__file__).resolve().parents[2]
        load_env_file(project_root / ".env")

        config_path = project_root / "agents_config.json"
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
        board_path = project_root / "app" / "data" / "board_positions.json"
        with board_path.open("r", encoding="utf-8") as file:
            config["board_positions"] = json.load(file)
        cls._apply_env_overrides(config)
        return cls(config=config, robot=MockRobot())

    @staticmethod
    def _apply_env_overrides(config: dict) -> None:
        llm_config = config.setdefault("llm", {})
        llm_config["provider"] = "ollama"
        llm_config["enabled"] = env_bool(
            "OLLAMA_ENABLED",
            bool(llm_config.get("enabled", True)),
        )
        llm_config["base_url"] = os.environ.get(
            "OLLAMA_BASE_URL",
            llm_config.get("base_url", "http://localhost:11434"),
        )
        llm_config["model"] = os.environ.get(
            "OLLAMA_MODEL",
            llm_config.get("model", "qwen2.5-coder:7b"),
        )
        llm_config["timeout_seconds"] = float(
            os.environ.get(
                "OLLAMA_TIMEOUT_SECONDS",
                llm_config.get("timeout_seconds", 5),
            )
        )
        llm_config["fallback_to_rule_parser"] = env_bool(
            "LLM_FALLBACK_TO_RULE_PARSER",
            bool(llm_config.get("fallback_to_rule_parser", True)),
        )

    def handle_command(self, command: str) -> dict:
        try:
            intention = self._parse_command(command)
        except ValueError as error:
            return {
                "status": "rejected",
                "message": str(error),
                "plan": {},
                "feedback": None,
            }

        return self.handle_intention(intention)

    def handle_intention(self, intention: dict) -> dict:
        state = self.robot.get_state()
        proposals = [
            agent.propose(intention=intention, state=state)
            for agent in self.joint_agents
        ]
        plan = self.coordinator.build_plan(
            intention=intention,
            proposals=proposals,
            state=state,
        )

        llm_review_error = self._review_plan_with_llm(intention, plan)
        if llm_review_error:
            return {
                "status": "rejected",
                "message": llm_review_error,
                "plan": plan,
                "feedback": None,
            }

        validation_error = self._validate_plan(plan)
        if validation_error:
            return {
                "status": "rejected",
                "message": validation_error,
                "plan": plan,
                "feedback": None,
            }

        feedback = self.robot.execute(plan)
        if feedback.get("status") != "ok":
            return {
                "status": feedback.get("status", "warning"),
                "message": feedback.get("message", "Execucao simulada nao concluida."),
                "plan": plan,
                "feedback": feedback,
            }

        return {
            "status": "ok",
            "message": "Plano executado no MockRobot.",
            "plan": plan,
            "feedback": feedback,
        }

    def _build_llm_client(self, llm_config: dict) -> OllamaClient | None:
        if not llm_config.get("enabled"):
            return None
        if llm_config.get("provider") != "ollama":
            return None
        client = OllamaClient(
            base_url=llm_config.get("base_url", "http://localhost:11434"),
            model=llm_config.get("model", "qwen2.5-coder:7b"),
            timeout=float(llm_config.get("timeout_seconds", 5)),
        )
        if client.is_available():
            return client
        if llm_config.get("fallback_to_rule_parser", True):
            return None
        raise RuntimeError("Ollama/Qwen nao esta disponivel e fallback esta desativado.")

    def _review_plan_with_llm(self, intention: dict, plan: dict) -> str | None:
        if not self.llm:
            if self.llm_fallback_enabled:
                return None
            return "Qwen/Ollama nao esta disponivel para revisar o plano."

        review = self.llm.review_motion_plan(intention=intention, plan=plan)
        if not review:
            if self.llm_fallback_enabled:
                return None
            return "Qwen/Ollama nao respondeu a revisao do plano."

        plan["llm_review"] = review
        if review.get("approved") is False:
            return review.get("reason", "Qwen rejeitou o plano.")
        return None

    def _parse_command(self, command: str) -> dict:
        llm_intention = self._parse_with_llm(command)
        if llm_intention:
            return llm_intention

        parts = command.strip().upper().split()
        if len(parts) != 3 or parts[0] != "MOVER":
            raise ValueError("Use o formato: mover A2 A4")

        origin = parts[1]
        destination = parts[2]
        self._validate_square(origin)
        self._validate_square(destination)

        return {
            "action": "move_piece",
            "origin": origin,
            "destination": destination,
        }

    def _parse_with_llm(self, command: str) -> dict | None:
        if not self.llm:
            return None

        parsed = self.llm.parse_robot_command(command)
        if not parsed:
            return None

        if parsed.get("action") != "move_piece":
            return None

        origin = str(parsed.get("origin", "")).upper()
        destination = str(parsed.get("destination", "")).upper()
        try:
            self._validate_square(origin)
            self._validate_square(destination)
        except ValueError:
            return None

        return {
            "action": "move_piece",
            "origin": origin,
            "destination": destination,
        }

    def _validate_square(self, square: str) -> None:
        if len(square) != 2:
            raise ValueError(f"Casa invalida: {square}")

        column = square[0]
        row = square[1]
        if column < "A" or column > "H" or row < "1" or row > "8":
            raise ValueError(f"Casa fora do tabuleiro: {square}")

    def _validate_plan(self, plan: dict) -> str | None:
        if plan["status"] != "ready":
            return plan["message"]

        for step in plan["steps"]:
            target = step["target"]
            if target["type"] == "gripper":
                if not 0 <= target["angle"] <= 180:
                    return f"Angulo inseguro em {step['name']}: {target['angle']}"
                continue

            for joint, angle in target["servos"].items():
                if not 0 <= angle <= 180:
                    return f"Angulo inseguro em {step['name']}:{joint}: {angle}"

        return None
