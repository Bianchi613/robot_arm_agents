class ShoulderJointAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def propose(self, intention: dict, state: dict) -> dict:
        row_index = int(intention["destination"][1]) - 1
        angle = 135 - round(row_index * (70 / 7))

        return {
            "joint": "shoulder",
            "angle": self._clamp(angle),
            "speed": 0.35,
            "reason": "Ajustar altura principal para alcancar a linha de destino.",
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))
