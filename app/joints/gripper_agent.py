class GripperAgent:
    def __init__(self, config: dict, llm=None, fallback_enabled: bool = True) -> None:
        self.config = config
        self.llm = llm
        self.fallback_enabled = fallback_enabled

    def propose(self, intention: dict, state: dict) -> dict:
        reason = "Abrir, segurar a peca, mover e soltar no destino."
        llm_used = False
        if self.llm:
            response = self.llm.generate_json(
                "Voce e o GripperAgent de um braco robotico de xadrez. "
                "Responda somente JSON puro. "
                "Formato: {\"reason\":\"...\"}. "
                f"Intencao: {intention}. Estado: {state}."
            )
            if response and response.get("reason"):
                reason = response["reason"]
                llm_used = True
            elif not self.fallback_enabled:
                raise RuntimeError("Qwen/Ollama nao respondeu ao GripperAgent.")

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
