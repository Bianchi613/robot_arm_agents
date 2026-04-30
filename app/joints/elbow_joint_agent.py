class ElbowJointAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def propose(self, intention: dict, state: dict) -> dict:
        row_index = int(intention["destination"][1]) - 1
        angle = 60 + round(row_index * (70 / 7))

        return {
            "joint": "elbow",
            "angle": self._clamp(angle),
            "speed": 0.4,
            "reason": "Regular extensao do braco para o alcance.",
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))
