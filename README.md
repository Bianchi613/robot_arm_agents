# Robot Arm Agents

Chess-playing robot arm simulator with Qwen-powered agents, chess validation, physical motion planning, and a mock robot executor.

![Robot Arm Agents flow](docs/robot_arm_agents.png)

Current flow:

```txt
User
  ->
main.py
  ->
ChessGame
  ->
SupervisorAgent
  ->
JointAgents
  ->
MotionCoordinatorAgent
  ->
SupervisorAgent
  ->
MockRobot
  ->
Feedback
```

## What Works

- Chess move validation with `python-chess`.
- Illegal move blocking before the robot moves.
- Required piece identity in the command, for example `move white pawn A2 A4`.
- Normal piece movement.
- Automatic black response selected by Qwen.
- Simulated capture with captured pieces moved to `CAPTURE_ZONE`.
- Step-by-step physical plan.
- Simulated physical board from `A1` to `H8`.
- Feedback with before/after board state.
- Qwen/Ollama integration with `qwen2.5-coder:7b`.

## Structure

```txt
robot_arm_agents/
|-- README.md
|-- ARCHITECTURE.md
|-- agents_config.json
|-- requirements.txt
|-- .env.example
|
`-- app/
    |-- main.py
    |-- chess/
    |   `-- chess_game.py
    |-- supervisor/
    |   `-- supervisor_agent.py
    |-- joints/
    |   |-- base_joint_agent.py
    |   |-- shoulder_joint_agent.py
    |   |-- elbow_joint_agent.py
    |   |-- wrist_joint_agent.py
    |   `-- gripper_agent.py
    |-- coordinator/
    |   `-- motion_coordinator_agent.py
    |-- robot/
    |   `-- mock_robot.py
    |-- llm/
    |   `-- ollama_client.py
    |-- config/
    |   `-- env_loader.py
    `-- data/
        `-- board_positions.json
```

## Install

```bash
pip install -r requirements.txt
```

## Configuration

```txt
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
LLM_FALLBACK_TO_RULE_PARSER=false
```

By default, agents require Qwen/Ollama. If Qwen is unavailable, the system rejects the command instead of silently using local rules as fake agents.

`LLM_FALLBACK_TO_RULE_PARSER=true` is only for emergency/simulation mode. In that mode, the system may continue with Python rules and mark `llm_used: False`.

## AI Agents

These components use Qwen when fallback is disabled:

- `BaseJointAgent`
- `ShoulderJointAgent`
- `ElbowJointAgent`
- `WristJointAgent`
- `GripperAgent`
- `MotionCoordinatorAgent`
- final plan review in `SupervisorAgent`

The output shows proof of use:

```txt
qwen_agents: 5/5
qwen_coordinator: {... 'llm_used': True ...}
qwen_review: {...}
```

## Run

Normal move:

```bash
python app/main.py "move white pawn A2 A4"
```

Expected:

```txt
Status: ok
Chess:
  move_type: normal
  piece: white_pawn
  color: white
  origin: A2
  destination: A4
piece_moved: True
before: {'A2': 'white_pawn', 'A4': None}
after: {'A2': None, 'A4': 'white_pawn'}
```

Valid command examples:

```bash
python app/main.py "move white pawn A2 A4"
python app/main.py "move white knight B1 C3"
python app/main.py "move black pawn E7 E5"
```

Wrong piece:

```bash
python app/main.py "move white knight A2 A4"
```

Expected:

```txt
Status: rejected
Message: Declared piece type mismatch: command says knight, but A2 contains white_pawn.
```

Incomplete command:

```bash
python app/main.py "move A2 A4"
```

Expected:

```txt
Status: rejected
Message: Use format: move white pawn A2 A4
```

Illegal move:

```bash
python app/main.py "move white pawn A2 A5"
```

Expected:

```txt
Status: rejected
Message: Illegal chess move: A2 -> A5
```

## Physical Map

`app/data/board_positions.json` contains:

- `HOME`
- `CAPTURE_ZONE`
- squares from `A1` to `H8`
- for each square: `ABOVE`, `PICK`, `DROP`

The current values are interpolated for simulation. Real hardware must replace them with measured calibration values.

## Next Steps

- Add an interactive mode to preserve the game between commands.
- Persist game and board state.
- Add `app/robot/arduino_robot.py`.
- Calibrate real arm positions.
- Add stronger collision and physical limit rules.
- Add automated tests.
