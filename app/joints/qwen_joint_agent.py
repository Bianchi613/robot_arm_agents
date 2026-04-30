class QwenJointAgent:
    def __init__(self, config: dict, llm=None, fallback_enabled: bool = True) -> None:
        self.config = config
        self.llm = llm
        self.fallback_enabled = fallback_enabled

    def _qwen_propose(
        self,
        agent_name: str,
        joint: str,
        intention: dict,
        state: dict,
        limits: dict,
    ) -> dict | None:
        if not self.llm:
            return None

        proposal = self.llm.propose_joint_move(
            agent_name=agent_name,
            intention=intention,
            state=state,
            limits=limits,
        )
        if not proposal:
            return None

        try:
            angle = int(proposal["angle"])
            speed = float(proposal.get("speed", 0.35))
        except (KeyError, TypeError, ValueError):
            return None

        return {
            "joint": joint,
            "angle": self._clamp_angle(angle, limits),
            "speed": max(0.05, min(1.0, speed)),
            "reason": proposal.get("reason", "Proposta gerada pelo Qwen."),
            "llm_agent": agent_name,
            "llm_used": True,
        }

    def _require_or_fallback(self, proposal: dict | None) -> dict | None:
        if proposal:
            return proposal
        if self.fallback_enabled:
            return None
        raise RuntimeError("Qwen/Ollama nao respondeu e fallback esta desativado.")

    def _clamp_angle(self, angle: int, limits: dict) -> int:
        return max(limits["min_angle"], min(limits["max_angle"], angle))
