from app.joints.qwen_joint_agent import QwenJointAgent


class WristJointAgent(QwenJointAgent):
    def __init__(self, config: dict, llm=None, fallback_enabled: bool = True) -> None:
        super().__init__(config=config, llm=llm, fallback_enabled=fallback_enabled)

    def propose(self, intention: dict, state: dict) -> dict:
        limits = self.config["limits"]
        qwen_proposal = self._require_or_fallback(
            self._qwen_propose(
                agent_name="WristJointAgent",
                joint="wrist",
                intention=intention,
                state=state,
                limits=limits,
            )
        )
        if qwen_proposal:
            return qwen_proposal

        shoulder_angle = state["servos"].get("shoulder", 90)
        elbow_angle = state["servos"].get("elbow", 90)
        angle = 180 - round((shoulder_angle + elbow_angle) / 2)

        return {
            "joint": "wrist",
            "angle": self._clamp(angle),
            "speed": 0.35,
            "reason": "Compensar ombro e cotovelo para manter a garra alinhada.",
            "llm_used": False,
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))
