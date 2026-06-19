import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

DEFAULT_MODEL = "claude-haiku-4-5"


def call(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> str:
    """Send a single prompt to Claude and return the text response."""
    messages = [{"role": "user", "content": prompt}]
    response = _client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text
