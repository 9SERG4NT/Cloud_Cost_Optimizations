"""
Agentic loop for the OmniCloud FinOps Agent.

Flow:
  1. Build message list from history + new user message
  2. Prepend Master System Prompt
  3. Call LLM (Ollama or OpenAI-compatible) with MCP tool schemas
  4. If tool_calls returned → execute via mcp_tools → feed results back
  5. If model outputs tool call as JSON in content → parse & execute it
  6. Loop until final text or MAX_TOOL_ITERATIONS
"""

import json
import re
import httpx
import logging
from typing import Optional

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYSTEM_PROMPT, MAX_TOOL_ITERATIONS, LLM_API_FORMAT, LLM_API_KEY
from backend.mcp_tools import get_tool_schemas, execute_tool

# Maximum tokens for analysis responses
_MAX_TOKENS = 4096

logger = logging.getLogger("omnicloud.agent")

# Known tool names for content-based detection
_TOOL_NAMES = None

# Detected API format (cached after first detection)
_DETECTED_API_FORMAT: Optional[str] = None


def _get_tool_names() -> set:
    """Lazily build set of registered tool names."""
    global _TOOL_NAMES
    if _TOOL_NAMES is None:
        _TOOL_NAMES = {
            t["function"]["name"] for t in get_tool_schemas()
        }
    return _TOOL_NAMES


def _extract_tool_call_from_content(content: str) -> Optional[dict]:
    """
    Detect if the model output a tool call as JSON in the content field.
    Small models (e.g. Qwen 1.5B) often do this instead of using native tool_calls.

    Returns {"name": ..., "arguments": {...}} or None.
    """
    if not content or not content.strip():
        return None

    tool_names = _get_tool_names()

    # Strategy 1: Try to find a JSON block with "name" and "arguments"
    # Look for ```json ... ``` blocks first
    json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_block_match:
        try:
            parsed = json.loads(json_block_match.group(1))
            if isinstance(parsed, dict) and parsed.get("name") in tool_names:
                return parsed
        except (json.JSONDecodeError, KeyError):
            pass

    # Strategy 2: Try to find a raw JSON object in the content
    # Look for { "name": "tool_name" ... } pattern
    json_match = re.search(r'\{\s*"name"\s*:\s*"(\w+)".*?\}', content, re.DOTALL)
    if json_match:
        tool_name_candidate = json_match.group(1)
        if tool_name_candidate in tool_names:
            # Try to parse the full JSON object
            # Find the matching closing brace
            start = json_match.start()
            brace_count = 0
            end = start
            for i, ch in enumerate(content[start:], start):
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            try:
                parsed = json.loads(content[start:end])
                if isinstance(parsed, dict) and parsed.get("name") in tool_names:
                    return parsed
            except json.JSONDecodeError:
                pass

    return None


async def _detect_api_format(client: httpx.AsyncClient) -> str:
    """
    Auto-detect whether the LLM server speaks Ollama or OpenAI-compatible API.
    Tries Ollama first (GET /api/tags), then OpenAI (GET /v1/models).
    Returns "ollama" or "openai".
    """
    global _DETECTED_API_FORMAT
    if _DETECTED_API_FORMAT:
        return _DETECTED_API_FORMAT

    # Try Ollama first
    try:
        resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            _DETECTED_API_FORMAT = "ollama"
            logger.info(f"Auto-detected Ollama API at {OLLAMA_BASE_URL}")
            return "ollama"
    except Exception:
        pass

    # Try OpenAI-compatible
    try:
        if "generativelanguage.googleapis.com" in OLLAMA_BASE_URL:
            url = f"{OLLAMA_BASE_URL}/models"
        elif OLLAMA_BASE_URL.rstrip("/").endswith("/v1"):
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/models"
        else:
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/models"
            
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            _DETECTED_API_FORMAT = "openai"
            logger.info(f"Auto-detected OpenAI-compatible API at {OLLAMA_BASE_URL}")
            return "openai"
    except Exception:
        pass

    # Default fallback to Ollama
    logger.warning(f"Could not auto-detect API format, defaulting to Ollama")
    _DETECTED_API_FORMAT = "ollama"
    return "ollama"


def _convert_tools_to_openai_format(tool_schemas: list) -> list:
    """Convert our tool schemas to OpenAI function-calling format."""
    # They should already be in the right format: {"type": "function", "function": {...}}
    return tool_schemas


async def _call_llm_ollama(
    client: httpx.AsyncClient,
    messages: list,
    tool_schemas: list,
) -> dict:
    """Call Ollama's native /api/chat endpoint."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "tools": tool_schemas,
        "stream": False,
    }

    resp = await client.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()

    assistant_msg = data.get("message", {})
    return {
        "role": assistant_msg.get("role", "assistant"),
        "content": assistant_msg.get("content", ""),
        "tool_calls": assistant_msg.get("tool_calls", None),
    }


async def _call_llm_openai(
    client: httpx.AsyncClient,
    messages: list,
    tool_schemas: list,
) -> dict:
    """Call an OpenAI-compatible /v1/chat/completions endpoint."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": _MAX_TOKENS,
    }

    # Only add tools if we have them
    if tool_schemas:
        payload["tools"] = _convert_tools_to_openai_format(tool_schemas)
        payload["tool_choice"] = "auto"

    try:
        # Gemini OpenAI-compatible base URL already ends with /openai
        # so just append /chat/completions; other providers need /v1/chat/completions
        if "generativelanguage.googleapis.com" in OLLAMA_BASE_URL:
            url = f"{OLLAMA_BASE_URL}/chat/completions"
        elif OLLAMA_BASE_URL.rstrip("/").endswith("/v1"):
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/chat/completions"
        else:
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"

        resp = await client.post(
            url,
            json=payload,
        )
        logger.info(f"LLM response: URL={url}, status={resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"LLM non-200 response body: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_body = ""
        try:
            error_body = e.response.text[:500]
        except Exception:
            pass
        logger.error(f"LLM HTTP {status_code}: {error_body}")

        if status_code == 429:
            return {
                "role": "assistant",
                "content": "⚠️ **Rate Limit Exceeded:** Your Gemini API free-tier quota has been exhausted. Please wait a minute and try again, or upgrade to a paid plan at https://ai.google.dev.",
                "tool_calls": None,
            }
        elif status_code == 402:
            return {
                "role": "assistant",
                "content": "⚠️ **Payment Required:** Your API credits have been exhausted. Please check your billing at https://ai.google.dev.",
                "tool_calls": None,
            }
        elif status_code == 401:
            return {
                "role": "assistant",
                "content": "⚠️ **Unauthorized:** Please check your GEMINI_API_KEY in the `.env` file.",
                "tool_calls": None,
            }
        elif status_code == 404:
            return {
                "role": "assistant",
                "content": f"⚠️ **Model Not Found:** The model `{OLLAMA_MODEL}` may not be available. Please verify the model name in your `.env` file.",
                "tool_calls": None,
            }
        else:
            return {
                "role": "assistant",
                "content": f"⚠️ **LLM API Error:** Server returned {status_code} on {url}. {error_body[:200]}",
                "tool_calls": None,
            }
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return {
            "role": "assistant",
            "content": "⚠️ **Connection Error:** Could not connect to the LLM agent provider.",
            "tool_calls": None,
        }

    # Parse OpenAI response format
    choices = data.get("choices", [])
    if not choices:
        return {"role": "assistant", "content": "", "tool_calls": None}

    msg = choices[0].get("message", {})
    content = msg.get("content", "") or ""

    raw_tool_calls = msg.get("tool_calls", None)

    return {
        "role": msg.get("role", "assistant"),
        "content": content,
        "tool_calls": raw_tool_calls,
    }


async def run_agent(
    messages: list[dict],
    user_message: str,
    session_id: Optional[str] = None,
) -> dict:
    """
    Run the agentic loop.

    Args:
        messages:      Prior conversation messages [{role, content}, ...]
        user_message:  The new user message
        session_id:    Optional session ID for logging

    Returns:
        {
            "response": str,           # Final assistant text
            "tool_calls_made": list,   # [{tool, args, result}, ...]
        }
    """
    # -------------------------------------------------------------------
    # LLM Agentic Loop — always use OpenRouter to synthesize real data
    # -------------------------------------------------------------------
    # Build the full message history for the LLM
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    full_messages.extend(messages)
    full_messages.append({"role": "user", "content": user_message})

    tool_schemas = get_tool_schemas()
    tool_calls_made = []
    iterations = 0

    # Build headers — include Bearer token when a Groq/OpenAI key is set
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    async with httpx.AsyncClient(timeout=180.0, headers=headers) as client:
        # Determine which API format to use
        if LLM_API_FORMAT == "auto":
            api_format = await _detect_api_format(client)
        else:
            api_format = LLM_API_FORMAT

        logger.info(f"[{session_id}] Using {api_format} API at {OLLAMA_BASE_URL}")

        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            logger.info(f"[{session_id}] Agent iteration {iterations}")

            # Call LLM
            try:
                if api_format == "openai":
                    result = await _call_llm_openai(client, full_messages, tool_schemas)
                else:
                    result = await _call_llm_ollama(client, full_messages, tool_schemas)

                role = result["role"]
                content = result["content"]
                tool_calls = result["tool_calls"]

            except httpx.HTTPStatusError as e:
                logger.error(f"LLM HTTP error: {e}")
                return {
                    "response": "I apologize, but I'm having trouble connecting to the AI engine. Please try again.",
                    "tool_calls_made": tool_calls_made,
                }
            except Exception as e:
                logger.error(f"LLM connection error: {e}")
                return {
                    "response": f"I apologize, but the AI engine is not available at {OLLAMA_BASE_URL}. Please check your GEMINI_API_KEY and network connection.",
                    "tool_calls_made": tool_calls_made,
                }

            # ----------------------------------------------------------
            # Path A: Native tool_calls from the LLM
            # ----------------------------------------------------------
            if tool_calls:
                # Ensure tool_calls arguments are strings for the message history
                history_tool_calls = []
                for tc in tool_calls:
                    tc_copy = dict(tc)
                    fn_copy = dict(tc.get("function", {}))
                    args = fn_copy.get("arguments", "")
                    if isinstance(args, dict):
                        fn_copy["arguments"] = json.dumps(args)
                    elif not isinstance(args, str):
                        fn_copy["arguments"] = str(args)
                    tc_copy["function"] = fn_copy
                    history_tool_calls.append(tc_copy)

                full_messages.append({
                    "role": role,
                    "content": content,
                    "tool_calls": history_tool_calls,
                })

                for tc in tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "unknown")
                    tool_args = fn.get("arguments", {})
                    tc_id = tc.get("id")

                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}

                    logger.info(f"[{session_id}] Calling tool (native): {tool_name}({tool_args})")
                    result = execute_tool(tool_name, tool_args)

                    tool_calls_made.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result[:2000],
                    })

                    tool_msg = {
                        "role": "tool",
                        "content": result,
                    }
                    if tc_id:
                        tool_msg["tool_call_id"] = tc_id
                        tool_msg["name"] = tool_name
                    
                    full_messages.append(tool_msg)

                # Continue the loop to get the synthesized response
                continue

            # ----------------------------------------------------------
            # Path B: Tool call embedded in content (small models)
            # ----------------------------------------------------------
            parsed_tool = _extract_tool_call_from_content(content)

            if parsed_tool:
                tool_name = parsed_tool.get("name", "unknown")
                tool_args = parsed_tool.get("arguments", {})

                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        tool_args = {}

                logger.info(f"[{session_id}] Calling tool (from content): {tool_name}({tool_args})")
                result = execute_tool(tool_name, tool_args)

                tool_calls_made.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result[:2000],
                })

                # Extract any surrounding text the model wrote (outside the JSON)
                surrounding_text = content
                # Remove the JSON block from the content
                json_block = re.search(r'```(?:json)?\s*\{.*?\}\s*```', content, re.DOTALL)
                if json_block:
                    surrounding_text = content[:json_block.start()] + content[json_block.end():]
                else:
                    # Remove raw JSON
                    raw_json = re.search(r'\{[^{}]*"name"\s*:.*?\}(?:\s*\})?', content, re.DOTALL)
                    if raw_json:
                        surrounding_text = content[:raw_json.start()] + content[raw_json.end():]

                # Feed the tool result back and ask for a synthesized response
                full_messages.append({
                    "role": "assistant",
                    "content": f"I'll use the {tool_name} tool to answer this question.",
                })
                full_messages.append({
                    "role": "tool",
                    "content": result,
                })

                # Add a nudge to synthesize the results
                full_messages.append({
                    "role": "user",
                    "content": (
                        "The tool has returned the data above. Now synthesize this into a clear, "
                        "professional executive summary with actionable recommendations. "
                        "Do NOT output any JSON or tool calls. Just provide the analysis in markdown."
                    ),
                })

                # Continue the loop to get the final synthesized response
                continue

            # ----------------------------------------------------------
            # Path C: No tool calls → final text response
            # ----------------------------------------------------------
            logger.info(f"[{session_id}] Agent finished with text response")
            return {
                "response": content,
                "tool_calls_made": tool_calls_made,
            }

    # Exceeded max iterations — provide safety fallback
    logger.warning(f"[{session_id}] Max iterations ({MAX_TOOL_ITERATIONS}) reached")
    return {
        "response": (
            "I've gathered extensive data through multiple tool calls. "
            "Here is a summary of my findings so far:\n\n"
            + "\n".join(
                f"- **{tc['tool']}**: {tc['result'][:200]}..."
                for tc in tool_calls_made
            )
        ),
        "tool_calls_made": tool_calls_made,
    }
