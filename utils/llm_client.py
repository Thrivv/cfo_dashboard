import runpod
import os
import re
try:
    from .config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID
except ImportError:
    from config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID

runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(RUNPOD_ENDPOINT_ID)


def clean_output(text: str) -> str:
    """Cleans raw LLM output and extracts structured content from generated_text."""
    if not text:
        return "No valid response received from LLM."

    # Extract content from generated_text if present
    generated_text_match = re.search(r"'generated_text':\s*\"([^\"]*)\"", text)
    if generated_text_match:
        content = generated_text_match.group(1)
        # Unescape newlines and other escape sequences
        content = content.replace('\\n', '\n').replace('\\t', '\t')
        return content.strip()
    
    # Try single quotes pattern as fallback
    generated_text_match = re.search(r"'generated_text':\s*'([^']*)'", text)
    if generated_text_match:
        content = generated_text_match.group(1)
        # Unescape newlines and other escape sequences
        content = content.replace('\\n', '\n').replace('\\t', '\t')
        return content.strip()

    # Fallback: clean the raw text
    # Remove repeated "User Question:" / "Answer:" blocks
    cleaned = re.sub(r"(User Question:.*?Answer:)", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Strip technical junk like raw tokens output
    cleaned = re.sub(r"'tokens':\s*\[.*?\]", "", cleaned, flags=re.DOTALL)

    # Normalize whitespace
    cleaned = cleaned.strip()

    # Remove duplicate lines, preserving order
    lines = cleaned.split('\n')
    seen = set()
    unique_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            unique_lines.append(line)

    cleaned = '\n'.join(unique_lines)
    return cleaned if cleaned else "No valid response received from LLM."


def call_vllm(prompt: str, max_tokens: int = 512) -> str:
    """Calls the vLLM endpoint on Runpod, polls for completion, and returns a cleaned output."""
    try:
        run_request = endpoint.run_sync(
            {
                "prompt": prompt,
                "application": "RAG",
                "sampling_params": {
                    "temperature": 0,
                    "max_tokens": max_tokens,
                    "repetition_penalty": 1.2
                }
            },
            timeout=300,  # Timeout in seconds (5 minutes)
        )
        
        if not run_request:
            return "Error: No output from LLM."

        try:
            # Primary expected format: [{'choices': [{'tokens': ['...']}]}]
            if isinstance(run_request, list) and run_request:
                first_item = run_request[0]
                if isinstance(first_item, dict) and 'choices' in first_item:
                    choices = first_item.get('choices')
                    if isinstance(choices, list) and choices:
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            tokens = first_choice.get('tokens')
                            if isinstance(tokens, list):
                                response_text = "".join(str(token) for token in tokens).strip()
                                return clean_output(response_text)

            # Fallback for simpler string or dict outputs
            if isinstance(run_request, str):
                return clean_output(run_request)

            # If all else fails, stringify and clean
            return clean_output(str(run_request))

        except Exception as e:
            return f"Error parsing LLM response: {e}"

    except TimeoutError:
        return "Error: LLM request timed out after 5 minutes."
    except Exception as e:
        return f"Error communicating with LLM service: {e}"
