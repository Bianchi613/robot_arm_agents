import json
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        request = urllib.request.Request(
            f"{self.base_url}/api/tags",
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status == 200
        except urllib.error.URLError:
            return False

    def parse_robot_command(self, command: str) -> dict | None:
        prompt = (
            "Convert the user command into pure JSON for a robot arm. "
            "Return only JSON, without markdown. "
            "Expected format: "
            "{\"action\":\"move_piece\",\"origin\":\"A2\",\"destination\":\"A4\"}. "
            f"Command: {command}"
        )
        response = self._generate(prompt)
        if not response:
            return None

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def generate_json(self, prompt: str) -> dict | None:
        response = self._generate(prompt)
        if not response:
            return None

        response = response.strip()
        if response.startswith("```"):
            response = response.strip("`")
            response = response.removeprefix("json").strip()

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(response[start:end + 1])
            except json.JSONDecodeError:
                return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def propose_joint_move(self, agent_name: str, intention: dict, state: dict, limits: dict) -> dict | None:
        prompt = (
            "You are a joint agent for a chess-playing robot arm. "
            "Return only pure JSON, without markdown. "
            "Create a safe proposal for this joint. "
            "Required fields: joint, angle, speed, reason. "
            f"Agent: {agent_name}. "
            f"Limits: {json.dumps(limits)}. "
            f"Intention: {json.dumps(intention)}. "
            f"State: {json.dumps(state)}."
        )
        return self.generate_json(prompt)

    def choose_chess_move(self, board_fen: str, legal_moves: list[str]) -> dict | None:
        prompt = (
            "You are the chess opponent agent for a robot arm. "
            "Choose exactly one move from legal_moves. "
            "Return only pure JSON, without markdown. "
            "Format: {\"move\":\"e7e5\",\"reason\":\"...\"}. "
            f"FEN: {board_fen}. "
            f"legal_moves: {json.dumps(legal_moves)}."
        )
        return self.generate_json(prompt)

    def review_motion_plan(self, intention: dict, plan: dict) -> dict | None:
        prompt = (
            "You are a safety supervisor for a robot arm. "
            "Review the physical plan below and return only pure JSON. "
            "Format: {\"approved\":true,\"reason\":\"...\"}. "
            f"Intention: {json.dumps(intention)}. "
            f"Plan: {json.dumps(plan)}."
        )
        return self.generate_json(prompt)

    def coordinate_motion_plan(
        self,
        intention: dict,
        proposals: list[dict],
        step_names: list[str],
    ) -> dict | None:
        compact_proposals = [
            {
                "joint": proposal.get("joint"),
                "angle": proposal.get("angle"),
                "speed": proposal.get("speed"),
                "llm_used": proposal.get("llm_used"),
                "reason": proposal.get("reason"),
            }
            for proposal in proposals
        ]
        prompt = (
            "You are the MotionCoordinatorAgent for a chess-playing robot arm. "
            "Your job is to review the technical coordination between joint proposals "
            "and physical steps. Do not invent new squares or servos. "
            "Return only pure JSON, without markdown. "
            "Format: {\"approved\":true,\"reason\":\"...\",\"risk\":\"low|medium|high\"}. "
            f"Intention: {json.dumps(intention)}. "
            f"Proposals: {json.dumps(compact_proposals)}. "
            f"Steps: {json.dumps(step_names)}."
        )
        return self.generate_json(prompt)

    def _generate(self, prompt: str) -> str | None:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode("utf-8")
            except Exception:
                body = str(error)
            print(f"Ollama HTTP error {error.code}: {body}")
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            print(f"Ollama request error: {error}")
            return None

        return body.get("response")
