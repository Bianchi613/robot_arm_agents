from app.joints.qwen_joint_agent import QwenJointAgent


class BaseJointAgent(QwenJointAgent):
    def __init__(self, config: dict, llm=None, fallback_enabled: bool = True) -> None:
        super().__init__(config=config, llm=llm, fallback_enabled=fallback_enabled)

    def propose(self, intention: dict, state: dict) -> dict:
        limits = self.config["limits"]
        qwen_proposal = self._require_or_fallback(
            self._qwen_propose(
                agent_name="BaseJointAgent",
                joint="base",
                intention=intention,
                state=state,
                limits=limits,
            )
        )
        if qwen_proposal:
            return qwen_proposal

        destination = intention["destination"]
        column_index = ord(destination[0]) - ord("A")
        angle = 25 + round(column_index * (130 / 7))

        return {
            "joint": "base",
            "angle": self._clamp(angle),
            "speed": 0.45,
            "reason": "Alinhar base com a coluna de destino.",
            "llm_used": False,
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))
