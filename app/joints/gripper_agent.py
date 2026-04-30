class GripperAgent:
    def __init__(self, config: dict, llm=None, fallback_enabled: bool = False) -> None:
        self.config = config
        self.llm = llm
        self.fallback_enabled = fallback_enabled

    def propose(self, intention: dict, state: dict) -> dict:
        reason = "Open, hold the piece, move it, and release it at the destination."
        llm_used = False
        if self.llm:
            response = self.llm.generate_json(
                "You are the GripperAgent for a chess robot arm. "
                "Return only pure JSON. "
                "Format: {\"reason\":\"...\"}. "
                f"Intention: {intention}. State: {state}."
            )
            if response and response.get("reason"):
                reason = response["reason"]
                llm_used = True
            elif not self.fallback_enabled:
                raise RuntimeError("Qwen/Ollama did not answer GripperAgent.")

        return {
            "joint": "gripper",
            "sequence": [
                {"action": "open", "angle": self.config["limits"]["open_angle"]},
                {"action": "close", "angle": self.config["limits"]["closed_angle"]},
                {"action": "open", "angle": self.config["limits"]["open_angle"]},
            ],
            "speed": 0.25,
            "reason": reason,
            "llm_agent": "GripperAgent",
            "llm_used": llm_used,
        }
