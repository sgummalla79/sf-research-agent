"""
API key validation — makes a lightweight call to each provider to confirm
the key is authentic before it is stored.

All validators run in a ThreadPoolExecutor so they can be awaited from async code.
Returns a dict of {key_name: error_string} for any key that fails; empty = all valid.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor


def _validate_anthropic(key: str) -> str | None:
    try:
        import anthropic
        anthropic.Anthropic(api_key=key).models.list()
        return None
    except anthropic.AuthenticationError:
        return "Invalid Anthropic API key — check your key at console.anthropic.com."
    except Exception as e:
        msg = str(e)
        if any(x in msg for x in ("401", "403", "Unauthorized", "Forbidden")):
            return "Anthropic API key rejected."
        return f"Could not reach Anthropic to verify key: {msg[:120]}"


def _validate_perplexity(key: str) -> str | None:
    try:
        from openai import OpenAI, AuthenticationError
        client = OpenAI(api_key=key, base_url="https://api.perplexity.ai")
        client.models.list()
        return None
    except Exception as e:
        msg = str(e)
        if any(x in msg for x in ("401", "403", "Unauthorized", "AuthenticationError", "invalid_api_key")):
            return "Invalid Perplexity API key — check your key at perplexity.ai/settings/api."
        return f"Could not reach Perplexity to verify key: {msg[:120]}"


def _validate_google(key: str) -> str | None:
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        list(genai.list_models())
        return None
    except Exception as e:
        msg = str(e)
        if any(x in msg for x in ("API_KEY_INVALID", "400", "401", "403", "invalid")):
            return "Invalid Google API key — check your key at aistudio.google.com."
        return f"Could not reach Google to verify key: {msg[:120]}"


_VALIDATORS = {
    "anthropic":  _validate_anthropic,
    "perplexity": _validate_perplexity,
    "google":     _validate_google,
}


async def validate_keys(keys: dict[str, str]) -> dict[str, str]:
    """
    Validate each key that is present in `keys`.
    Returns {key_name: error_message} for failures; empty dict = all valid.
    """
    loop = asyncio.get_event_loop()
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            name: loop.run_in_executor(executor, fn, keys[name])
            for name, fn in _VALIDATORS.items()
            if keys.get(name)
        }
        for name, future in futures.items():
            error = await future
            if error:
                errors[name] = error

    return errors
