class BaseJointAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def propose(self, intention: dict, state: dict) -> dict:
        destination = intention["destination"]
        column_index = ord(destination[0]) - ord("A")
        angle = 25 + round(column_index * (130 / 7))

        return {
            "joint": "base",
            "angle": self._clamp(angle),
            "speed": 0.45,
            "reason": "Alinhar base com a coluna de destino.",
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))
