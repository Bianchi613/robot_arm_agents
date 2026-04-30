class GripperAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def propose(self, intention: dict, state: dict) -> dict:
        return {
            "joint": "gripper",
            "sequence": [
                {"action": "open", "angle": self.config["limits"]["open_angle"]},
                {"action": "close", "angle": self.config["limits"]["closed_angle"]},
                {"action": "open", "angle": self.config["limits"]["open_angle"]},
            ],
            "speed": 0.25,
            "reason": "Abrir, segurar a peca, mover e soltar no destino.",
        }
