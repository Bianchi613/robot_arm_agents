# Robot Arm Agents

Simulador de um braco robotico para jogar xadrez, com uma camada de regras antes da camada fisica.

![Robot Arm Agents flow](docs/robot_arm_agents.png)

O fluxo atual e:

```txt
Usuario
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

## O Que Funciona

- Validacao de lances com `python-chess`.
- Bloqueio de lances ilegais antes do braco se mexer.
- Movimento normal de uma peca.
- Resposta automatica do agente adversario com uma jogada legal.
- Captura simulada com remocao da peca capturada para `CAPTURE_ZONE`.
- Plano fisico por etapas.
- Tabuleiro fisico simulado com casas `A1` ate `H8`.
- Feedback com estado antes/depois da origem e destino.
- Configuracao opcional de LLM local via Ollama com `qwen2.5-coder:7b`.

## Estrutura

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
    |
    |-- chess/
    |   `-- chess_game.py
    |
    |-- supervisor/
    |   `-- supervisor_agent.py
    |
    |-- joints/
    |   |-- base_joint_agent.py
    |   |-- shoulder_joint_agent.py
    |   |-- elbow_joint_agent.py
    |   |-- wrist_joint_agent.py
    |   `-- gripper_agent.py
    |
    |-- coordinator/
    |   `-- motion_coordinator_agent.py
    |
    |-- robot/
    |   `-- mock_robot.py
    |
    |-- llm/
    |   `-- ollama_client.py
    |
    |-- config/
    |   `-- env_loader.py
    |
    `-- data/
        `-- board_positions.json
```

## Instalar

```bash
pip install -r requirements.txt
```

## Configuracao

Copie `.env.example` para `.env` ou mantenha o `.env` atual:

```txt
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
LLM_FALLBACK_TO_RULE_PARSER=false
```

Por padrao, os agentes exigem Qwen/Ollama. Se o Qwen nao responder, o sistema rejeita em vez de fingir que um agente decidiu por regra local.

`LLM_FALLBACK_TO_RULE_PARSER=true` deve ser usado apenas como modo de emergencia/simulacao. Nesse modo, o sistema pode continuar com regras Python e marcar `llm_used: False`.

## Agentes de IA

Estes componentes usam Qwen quando o fallback esta desligado:

- `BaseJointAgent`
- `ShoulderJointAgent`
- `ElbowJointAgent`
- `WristJointAgent`
- `GripperAgent`
- `MotionCoordinatorAgent`
- revisao final do `SupervisorAgent`
- jogada de resposta do agente adversario no `ChessGame`

A saida mostra a prova de uso:

```txt
agentes_qwen: 5/5
coordenador_qwen: {... 'llm_used': True ...}
revisao_qwen: {...}
decisao: qwen2.5-coder:7b
```

## Rodar

Movimento normal:

```bash
python app/main.py "mover peao branco A2 A4"
```

Esperado:

```txt
Status: ok
Xadrez:
  tipo: normal
  peca: white_pawn
  cor: white
  origem: A2
  destino: A4
peca_movida: True
antes: {'A2': 'white_pawn', 'A4': None}
depois: {'A2': None, 'A4': 'white_pawn'}

Comando: resposta do agente
peca: black_pawn
origem: E7
destino: E5
depois: {'E7': None, 'E5': 'black_pawn'}
```

Exemplos de comandos validos:

```bash
python app/main.py "mover peao branco A2 A4"
python app/main.py "mover cavalo branco B1 C3"
```

O comando precisa informar peca e cor:

```txt
mover peao branco A2 A4
mover cavalo branco B1 C3
mover peao preto E7 E5
```

Se a peca informada nao bater com a casa de origem, o `ChessGame` rejeita antes do braco se mexer:

```bash
python app/main.py "mover cavalo branco A2 A4"
```

Esperado:

```txt
Status: rejected
Mensagem: Peca declarada nao confere: voce informou knight, mas em A2 existe white_pawn.
```

Comando incompleto:

```bash
python app/main.py "mover A2 A5"
```

Esperado:

```txt
Status: rejected
Mensagem: Use o formato: mover peao branco A2 A4
```

Lance ilegal com identidade completa:

```bash
python app/main.py "mover peao branco A2 A5"
```

Esperado:

```txt
Status: rejected
Mensagem: Lance invalido no xadrez: A2 -> A5
```

## Captura

A captura funciona no simulador quando a partida e mantida no mesmo processo.

Exemplo de sequencia:

```txt
mover E2 E4
mover D7 D5
mover E4 D5
```

Resultado esperado da captura:

```txt
antes: {'E4': 'white_pawn', 'D5': 'black_pawn'}
depois: {'E4': None, 'D5': 'white_pawn'}
capturadas: ['black_pawn']
```

Observacao: executar `python app/main.py "..."` sempre cria uma partida nova. Para testar sequencias completas, use o mesmo `ChessGame` e o mesmo `SupervisorAgent` no mesmo processo.

## Mapa Fisico

`app/data/board_positions.json` contem:

- `HOME`
- `CAPTURE_ZONE`
- casas `A1` ate `H8`
- para cada casa: `ABOVE`, `PICK`, `DROP`

Os valores atuais sao interpolados para simulacao. No braco real, devem ser substituidos por calibracao medida.

## Proximos Passos

- Criar um modo interativo para manter a partida entre varios comandos.
- Persistir estado da partida e do tabuleiro em arquivo.
- Adicionar `app/robot/arduino_robot.py`.
- Calibrar posicoes reais do braco.
- Adicionar regras de colisao e limites fisicos mais fortes.
- Criar testes automatizados.
