# Architecture

![Robot Arm Agents flow](docs/robot_arm_agents.png)

## Overview

The project separates chess rules, AI agent planning, physical motion coordination, and robot execution.

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

## Responsibilities

`ChessGame`

- validates commands such as `move white pawn A2 A4`
- requires piece type, color, origin, and destination
- validates chess legality with `python-chess`
- checks that declared piece identity matches the origin square
- detects normal moves, captures, check, and checkmate
- does not move servos
- does not talk to Arduino

`SupervisorAgent`

- receives a chess-validated intention
- reads the robot state
- calls the joint agents
- receives the coordinated plan
- asks Qwen to review the final plan
- validates final safety constraints
- sends the plan to the robot
- receives feedback

`JointAgents`

- `BaseJointAgent`: horizontal rotation
- `ShoulderJointAgent`: main lift/lower motion
- `ElbowJointAgent`: arm reach
- `WristJointAgent`: gripper alignment
- `GripperAgent`: open and close gripper

`MotionCoordinatorAgent`

- receives joint proposals
- detects simple conflicts
- asks Qwen to review technical coordination
- uses `board_positions.json`
- builds normal move plans
- builds capture plans

`MockRobot`

- simulates servos
- simulates the physical board
- simulates pick and drop
- simulates captured-piece disposal in `CAPTURE_ZONE`
- returns verifiable feedback

## Required AI Mode

Default configuration:

```txt
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5-coder:7b
LLM_FALLBACK_TO_RULE_PARSER=false
```

Components with `Agent` in the name must use Qwen/Ollama:

```txt
SupervisorAgent
BaseJointAgent
ShoulderJointAgent
ElbowJointAgent
WristJointAgent
GripperAgent
MotionCoordinatorAgent
```

If Qwen is unavailable, the system must fail clearly. Local Python rules remain as safety validation and emergency fallback only when fallback is manually enabled.

## Normal Move

Command:

```txt
move white pawn A2 A4
```

Flow:

```txt
1. main.py receives the command
2. ChessGame validates the move
3. ChessGame returns:
   origin = A2
   destination = A4
   move_type = normal
   piece = white_pawn
   color = white
4. SupervisorAgent receives the intention
5. JointAgents propose movements with Qwen
6. MotionCoordinatorAgent coordinates the plan with Qwen
7. SupervisorAgent reviews the plan with Qwen
8. MockRobot executes
9. Feedback confirms before/after state
```

Physical plan:

```txt
go_home
move_to_source_above
open_gripper
move_to_source_pick
close_gripper
lift_piece
move_to_destination_above
move_to_destination_drop
open_gripper
clear_destination
go_home
```

## Invalid Move

Command:

```txt
move white pawn A2 A5
```

Result:

```txt
ChessGame rejects the move
SupervisorAgent is not called
MockRobot does not move
```

If the command is missing piece identity, for example `move A2 A4`, `ChessGame` rejects it before the robot moves.

## Capture

Example sequence in a persistent game process:

```txt
move white pawn E2 E4
move black pawn D7 D5
move white pawn E4 D5
```

For `E4 -> D5`, `ChessGame` identifies a capture.

The physical plan does two jobs:

```txt
1. remove the captured piece from D5
2. move the captured piece to CAPTURE_ZONE
3. pick the attacking piece from E4
4. move the attacking piece to D5
```

Capture plan:

```txt
go_home
move_to_captured_above
open_gripper
move_to_captured_pick
close_gripper
lift_captured_piece
move_to_capture_zone
release_captured_piece
move_to_source_above
move_to_source_pick
close_gripper
lift_piece
move_to_destination_above
move_to_destination_drop
open_gripper
clear_destination
go_home
```

Expected feedback:

```txt
before: {'E4': 'white_pawn', 'D5': 'black_pawn'}
after: {'E4': None, 'D5': 'white_pawn'}
captured: ['black_pawn']
```

## Physical Map

File:

```txt
app/data/board_positions.json
```

Contains:

```txt
HOME
CAPTURE_ZONE
A1_ABOVE / A1_PICK / A1_DROP
...
H8_ABOVE / H8_PICK / H8_DROP
```

Current values are simulation approximations. Real hardware must replace them with measured calibration values.
