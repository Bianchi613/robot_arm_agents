import json
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def parse_robot_command(self, command: str) -> dict | None:
        prompt = (
            "Converta o comando do usuario em JSON puro para um braco robotico. "
            "Responda somente JSON, sem markdown. "
            "Formato esperado: "
            "{\"action\":\"move_piece\",\"origin\":\"A2\",\"destination\":\"A4\"}. "
            f"Comando: {command}"
        )
        response = self._generate(prompt)
        if not response:
            return None

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def _generate(self, prompt: str) -> str | None:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        return body.get("response")
