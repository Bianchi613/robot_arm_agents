import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    app_dir = str(Path(__file__).resolve().parent)
    project_root = str(Path(__file__).resolve().parents[1])
    if app_dir in sys.path:
        sys.path.remove(app_dir)
    sys.path.insert(0, project_root)

from app.chess.chess_game import ChessGame
from app.supervisor.supervisor_agent import SupervisorAgent


def main() -> None:
    command = " ".join(sys.argv[1:]).strip() or "move white pawn A2 A4"
    try:
        supervisor = SupervisorAgent.from_default_config()
    except RuntimeError as error:
        _print_result(
            command,
            {
                "status": "rejected",
                "message": str(error),
                "plan": {},
                "feedback": None,
                "chess": {},
            },
        )
        return

    chess_game = ChessGame(
        llm=supervisor.llm,
        fallback_enabled=supervisor.llm_fallback_enabled,
    )
    chess_result = chess_game.validate_command(command)
    if chess_result["status"] != "ok":
        result = {
            "status": chess_result["status"],
            "message": chess_result["message"],
            "plan": {},
            "feedback": None,
            "chess": chess_result,
        }
        _print_result(command, result)
        return

    result = _execute_chess_move(supervisor, chess_result)
    result["chess"] = chess_result
    _print_result(command, result)

    if chess_result.get("checkmate"):
        return

    try:
        agent_chess_result = chess_game.choose_agent_move()
    except RuntimeError as error:
        agent_chess_result = {
            "status": "rejected",
            "message": str(error),
        }
    if agent_chess_result["status"] != "ok":
        agent_result = {
            "status": agent_chess_result["status"],
            "message": agent_chess_result["message"],
            "plan": {},
            "feedback": None,
            "chess": agent_chess_result,
        }
        _print_result("agent response", agent_result)
        return

    agent_result = _execute_chess_move(supervisor, agent_chess_result)
    agent_result["chess"] = agent_chess_result
    _print_result("agent response", agent_result)


def _execute_chess_move(supervisor: SupervisorAgent, chess_result: dict) -> dict:
    return supervisor.handle_intention(
        {
            "action": "move_piece",
            "origin": chess_result["origin"],
            "destination": chess_result["destination"],
            "move_type": chess_result["move_type"],
            "captured_square": chess_result.get("captured_square"),
            "piece": chess_result.get("piece"),
            "piece_color": chess_result.get("piece_color"),
            "piece_type": chess_result.get("piece_type"),
            "captured_piece": chess_result.get("captured_piece"),
        }
    )


def _print_result(command: str, result: dict) -> None:
    print(f"Command: {command}")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    chess_result = result.get("chess") or {}
    if chess_result:
        print("Chess:")
        print(f"  status: {chess_result.get('status')}")
        if chess_result.get("origin"):
            print(f"  move_type: {chess_result.get('move_type')}")
            print(f"  piece: {chess_result.get('piece')}")
            print(f"  color: {chess_result.get('piece_color')}")
            print(f"  origin: {chess_result.get('origin')}")
            print(f"  destination: {chess_result.get('destination')}")
            if chess_result.get("captured_piece"):
                print(f"  captured_piece: {chess_result.get('captured_piece')}")
            if chess_result.get("decision_source"):
                print(f"  decision: {chess_result.get('decision_source')}")
                print(f"  reason: {chess_result.get('decision_reason')}")
            print(f"  check: {chess_result.get('check')}")
            print(f"  checkmate: {chess_result.get('checkmate')}")
    print("Plan:")
    joint_proposals = result.get("plan", {}).get("joint_proposals", [])
    if joint_proposals:
        llm_count = sum(1 for proposal in joint_proposals if proposal.get("llm_used"))
        print(f"  qwen_agents: {llm_count}/{len(joint_proposals)}")
    if result.get("plan", {}).get("coordinator_agent"):
        print(f"  qwen_coordinator: {result['plan']['coordinator_agent']}")
    if result.get("plan", {}).get("llm_review"):
        print(f"  qwen_review: {result['plan']['llm_review']}")
    for step in result.get("plan", {}).get("steps", []):
        target = step["target"]
        if target["type"] == "pose":
            print(f"  - {step['name']}: {target['label']}")
        elif target["type"] == "gripper":
            print(f"  - {step['name']}: {target['action']}")
    print("Feedback:")
    feedback = result.get("feedback") or {}
    print(f"  piece_moved: {feedback.get('piece_moved')}")
    print(f"  origin: {feedback.get('origin')}")
    print(f"  destination: {feedback.get('destination')}")
    print(f"  holding_piece: {feedback.get('holding_piece')}")
    print(f"  status: {feedback.get('status')}")
    if feedback.get("captured_pieces") is not None:
        print(f"  captured: {feedback.get('captured_pieces')}")
    if feedback.get("message"):
        print(f"  message: {feedback.get('message')}")
    print(f"  before: {_board_summary(feedback, 'board_before')}")
    print(f"  after: {_board_summary(feedback, 'board_after')}")


def _board_summary(feedback: dict, key: str) -> dict | None:
    board = feedback.get(key)
    origin = feedback.get("origin")
    destination = feedback.get("destination")
    if not board or not origin or not destination:
        return None
    return {
        origin: board.get(origin),
        destination: board.get(destination),
    }


if __name__ == "__main__":
    main()
