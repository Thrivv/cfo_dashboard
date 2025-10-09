import requests
import time
import os
import re

try:
    from .config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID
except ImportError:
    from config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"
headers = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json",
}


def clean_output(text: str) -> str:
    """Cleans raw LLM output and extracts structured content from generated_text."""
    if not text:
        return "No valid response received from LLM."

    # Extract content from generated_text if present
    generated_text_match = re.search(r"'generated_text':\s*\"([^\"]*)\"", text)
    if generated_text_match:
        content = generated_text_match.group(1)
        # Unescape newlines and other escape sequences
        content = content.replace("\\n", "\n").replace("\\t", "\t")
        return content.strip()

    # Try single quotes pattern as fallback
    generated_text_match = re.search(r"'generated_text':\s*'([^']*)'", text)
    if generated_text_match:
        content = generated_text_match.group(1)
        # Unescape newlines and other escape sequences
        content = content.replace("\\n", "\n").replace("\\t", "\t")
        return content.strip()

    # Fallback: clean the raw text
    # Remove repeated "User Question:" / "Answer:" blocks
    cleaned = re.sub(
        r"(User Question:.*?Answer:)", "", text, flags=re.IGNORECASE | re.DOTALL
    )

    # Strip technical junk like raw tokens output
    cleaned = re.sub(r"'tokens':\s*\[.*?\]", "", cleaned, flags=re.DOTALL)

    # Normalize whitespace
    cleaned = cleaned.strip()

    # Remove duplicate lines, preserving order
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


def call_vllm(prompt: str, max_tokens: int = 1024) -> str:
    """Calls the vLLM endpoint on Runpod, polls for completion, and returns a cleaned output."""
    data = {
        "input": {
            "prompt": prompt,
            "application": "RAG",
            "sampling_params": {
                "temperature": 0,
                "max_tokens": max_tokens,
                "repetition_penalty": 1.2,
            },
        }
    }

    try:
        # Step 1: Submit the job
        response = requests.post(
            f"{BASE_URL}/run", headers=headers, json=data, timeout=30
        )
        response.raise_for_status()
        job = response.json()
        job_id = job.get("id")
        if not job_id:
            return "Error: Failed to submit job to LLM."

        # Step 2: Poll for the result with timeout
        max_attempts = 100  # ~300 seconds total (5 minutes)
        attempts = 0
        while attempts < max_attempts:
            try:
                status_response = requests.get(
                    f"{BASE_URL}/status/{job_id}", headers=headers, timeout=10
                )
                status_response.raise_for_status()
                status_json = status_response.json()

                if status_json["status"] == "COMPLETED":
                    output = status_json.get("output")
                    if not output:
                        return "Error: No output from LLM."

                    try:
                        # Primary expected format: [{'choices': [{'tokens': ['...']}]}]
                        if isinstance(output, list) and output:
                            first_item = output[0]
                            if isinstance(first_item, dict) and "choices" in first_item:
                                choices = first_item.get("choices")
                                if isinstance(choices, list) and choices:
                                    first_choice = choices[0]
                                    if isinstance(first_choice, dict):
                                        tokens = first_choice.get("tokens")
                                        if isinstance(tokens, list):
                                            response_text = "".join(
                                                str(token) for token in tokens
                                            ).strip()
                                            return clean_output(response_text)

                        # Fallback for simpler string or dict outputs
                        if isinstance(output, str):
                            return clean_output(output)

                        # If all else fails, stringify and clean
                        return clean_output(str(output))

                    except Exception as e:
                        return f"Error parsing LLM response: {e}"

                elif status_json["status"] == "FAILED":
                    return "Error: LLM job failed."
                else:
                    attempts += 1
                    time.sleep(3)

            except requests.exceptions.Timeout:
                attempts += 1
                if attempts >= max_attempts:
                    return "Error: LLM request timed out."
                time.sleep(3)

            except requests.exceptions.RequestException as e:
                return f"Error checking LLM status: {e}"

        return "Error: LLM request timed out after 300 seconds (5 minutes)."

    except requests.exceptions.RequestException as e:
        return f"Error communicating with LLM service: {e}"

    except Exception as e:
        return f"An unexpected error occurred: {e}"
