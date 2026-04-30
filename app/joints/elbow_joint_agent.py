class ElbowJointAgent:
    def __init__(self, config: dict, llm=None, fallback_enabled: bool = False) -> None:
        self.config = config
        self.llm = llm
        self.fallback_enabled = fallback_enabled

    def propose(self, intention: dict, state: dict) -> dict:
        limits = self.config["limits"]
        qwen_proposal = self._require_or_fallback(
            self._qwen_propose(
                agent_name="ElbowJointAgent",
                joint="elbow",
                intention=intention,
                state=state,
                limits=limits,
            )
        )
        if qwen_proposal:
            return qwen_proposal

        row_index = int(intention["destination"][1]) - 1
        angle = 60 + round(row_index * (70 / 7))

        return {
            "joint": "elbow",
            "angle": self._clamp(angle),
            "speed": 0.4,
            "reason": "Regular extensao do braco para o alcance.",
            "llm_used": False,
        }

    def _clamp(self, angle: int) -> int:
        limits = self.config["limits"]
        return max(limits["min_angle"], min(limits["max_angle"], angle))

    def _qwen_propose(self, agent_name: str, joint: str, intention: dict, state: dict, limits: dict) -> dict | None:
        if not self.llm:
            return None
        proposal = self.llm.propose_joint_move(agent_name, intention, state, limits)
        if not proposal:
            return None
        try:
            angle = int(proposal["angle"])
            speed = float(proposal.get("speed", 0.4))
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "joint": joint,
            "angle": max(limits["min_angle"], min(limits["max_angle"], angle)),
            "speed": max(0.05, min(1.0, speed)),
            "reason": proposal.get("reason", "Proposta gerada pelo Qwen."),
            "llm_agent": agent_name,
            "llm_used": True,
        }

    def _require_or_fallback(self, proposal: dict | None) -> dict | None:
        if proposal or self.fallback_enabled:
            return proposal
        raise RuntimeError("Qwen/Ollama nao respondeu e fallback esta desativado.")
