"""LLM client utilities for AI interactions using OpenRouter."""

import re
import json
import requests

try:
    from .config import OPENROUTER_API_KEY
except ImportError:
    from config import OPENROUTER_API_KEY


def clean_output(text: str) -> str:
    """Cleans raw LLM output and extracts structured content."""
    if not text:
        return "No valid response received from LLM."

    # Try extracting from known fields like 'generated_text'
    generated_text_match = re.search(r"'generated_text':\s*\"([^\"]*)\"", text)
    if generated_text_match:
        content = generated_text_match.group(1)
        content = content.replace("\\n", "\n").replace("\\t", "\t")
        return content.strip()

    generated_text_match = re.search(r"'generated_text':\s*'([^']*)'", text)
    if generated_text_match:
        content = generated_text_match.group(1)
        content = content.replace("\\n", "\n").replace("\\t", "\t")
        return content.strip()

    # Remove "User Question:" / "Answer:" boilerplate
    cleaned = re.sub(r"(User Question:.*?Answer:)", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove token dumps and normalize whitespace
    cleaned = re.sub(r"'tokens':\s*\[.*?\]", "", cleaned, flags=re.DOTALL).strip()

    # Remove duplicate lines
    lines = cleaned.split("\n")
    seen = set()
    unique_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            unique_lines.append(line)
    cleaned = "\n".join(unique_lines)

    return cleaned if cleaned else "No valid response received from LLM."


def call_vllm(prompt: str, max_tokens: int = 700) -> str:
    """Calls the OpenRouter LLM endpoint and returns a cleaned output."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
            "repetition_penalty": 1.2,
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=300)

        if response.status_code != 200:
            return f"Error: LLM request failed ({response.status_code}): {response.text}"

        data = response.json()

        # Expected structure: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in data and len(data["choices"]) > 0:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
            return clean_output(content)

        # Fallback: attempt to stringify entire JSON
        return clean_output(json.dumps(data))

    except requests.Timeout:
        return "Error: LLM request timed out after 5 minutes."
    except Exception as e:
        return f"Error communicating with LLM service: {e}"
