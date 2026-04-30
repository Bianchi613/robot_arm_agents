class WristJointAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def propose(self, intention: dict, state: dict) -> dict:
        shoulder_angle = state["servos"].get("shoulder", 90)
        elbow_angle = state["servos"].get("elbow", 90)
        angle = 180 - round((shoulder_angle + elbow_angle) / 2)

        return {
            "joint": "wrist",
            "angle": self._clamp(angle),
            "speed": 0.35,
            "reason": "Compensar ombro e cotovelo para manter a garra alinhada.",
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))
