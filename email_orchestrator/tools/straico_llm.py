import os
import json
import asyncio
import aiohttp
from typing import AsyncGenerator, Dict, Any

from dotenv import load_dotenv

from google.adk.models.base_llm import BaseLlm  # type: ignore
from google.adk.models.llm_request import LlmRequest  # type: ignore
from google.adk.models.llm_response import LlmResponse  # type: ignore

from google.genai import types as genai_types  # type: ignore

from pathlib import Path

# Load environment variables from the .env file located in the email_orchestrator package (two levels up)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class StraicoLLM(BaseLlm):
    """
    ADK BaseLlm implementation that talks to Straico's OpenAI-compatible API.

    Responsibilities:
    - Convert ADK's LlmRequest (contents + config + tools) into an OpenAI-style
      /chat/completions request for Straico.
    - Forward tools (AgentTool, FunctionTool, etc.) via the OpenAI "tools" field.
    - Parse tool_calls from Straico and emit FunctionCall parts so ADK can
      route them to the correct tools.
    """

    model: str

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://api.straico.com/v2",
    ) -> None:
        super().__init__(model=model)
        self._api_key = api_key or os.getenv("STRAICO_API_KEY")
        if not self._api_key:
            raise ValueError("STRAICO_API_KEY not set in environment")
        self._base_url = base_url.rstrip("/")

    # ---- ADK-required method ----
    @classmethod
    def supported_models(cls) -> list[str]:  # type: ignore[override]
        return [
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "openai/gpt-4o-2024-08-06",
            "openai/gpt-4-turbo-2024-04-09",
            "openai/gpt-5-chat",
            "anthropic/claude-3-5-sonnet-20240620",
            "amazon/nova-micro-v1",
        ]

    # ---- Helper: map ADK contents → OpenAI messages ----
    def _build_messages(self, llm_request: LlmRequest) -> list[Dict[str, Any]]:
        """
        llm_request.contents is a list of google.genai.types.Content.

        For now we:
        - Concatenate all text parts.
        - Ignore function_call / function_response history for simplicity.
        ADK will still handle tool calls via FunctionCall parts we emit later.
        """
        messages: list[Dict[str, Any]] = []

        # Add system instruction if present
        sys_content = getattr(llm_request, "system_instruction", None)
        if not sys_content and getattr(llm_request, "config", None):
            sys_content = getattr(llm_request.config, "system_instruction", None)

        if sys_content:
            sys_text = ""
            if isinstance(sys_content, str):
                sys_text = sys_content
            elif hasattr(sys_content, "parts"):
                sys_text = "".join([p.text for p in sys_content.parts if p.text])
            
            if sys_text:
                messages.append({"role": "system", "content": sys_text})

        for content in llm_request.contents:
            c = content.model_dump()
            role = c.get("role", "user")
            text_parts: list[str] = []

            for part in c.get("parts", []):
                if "text" in part and part["text"]:
                    text_parts.append(part["text"])

            text = "".join(text_parts).strip()
            if not text:
                continue

            messages.append({"role": role, "content": text})

        if not messages:
            messages.append({"role": "user", "content": ""})

        return messages

    # ---- Helper: map ADK tools → OpenAI tools schema ----
    def _build_tools(self, llm_request: LlmRequest) -> list[Dict[str, Any]]:
        """
        Convert ADK BaseTool map to OpenAI \"tools\" list.
        """
        tools_payload: list[Dict[str, Any]] = []
        tools_map: Dict[str, Any] = getattr(llm_request, "tools_dict", {}) or {}

        if not tools_map:
            return tools_payload

        for tool_name, tool in tools_map.items():
            fn_decl = None
            try:
                fn_decl = tool.declaration()
            except Exception:
                fn_decl = None

            if fn_decl is not None:
                fn = fn_decl
                params: Dict[str, Any] = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
                try:
                    if getattr(fn, "parameters", None) is not None:
                        params = fn.parameters.model_dump()
                        
                        def clean_schema(node):
                            if isinstance(node, dict):
                                clean_node = {}
                                if "properties" in node and isinstance(node["properties"], dict):
                                    clean_props = {}
                                    for prop_name, prop_def in node["properties"].items():
                                        clean_props[prop_name] = clean_schema(prop_def)
                                    clean_node["properties"] = clean_props
                                
                                if "items" in node and node["items"] is not None:
                                    clean_node["items"] = clean_schema(node["items"])

                                allowed_keys = {"type", "required", "description", "enum", "format"}
                                for k, v in node.items():
                                    if k in allowed_keys and v is not None:
                                        if k == "type" and isinstance(v, str):
                                            clean_node[k] = v.lower()
                                        else:
                                            clean_node[k] = v
                                            
                                return clean_node
                            elif isinstance(node, list):
                                return [clean_schema(item) for item in node]
                            else:
                                return node
                        
                        params = clean_schema(params)
                        
                        if "required" in params and params["required"] is None:
                            del params["required"]
                except Exception:
                    pass

                tools_payload.append({
                    "type": "function",
                    "function": {
                        "name": fn.name,
                        "description": getattr(fn, "description", "") or "",
                        "parameters": params,
                    },
                })
            else:
                tools_payload.append({
                    "type": "function",
                    "function": {
                        "name": getattr(tool, "name", tool_name),
                        "description": getattr(tool, "description", "") or "",
                    },
                })

        return tools_payload


    # ---- Helper: map Straico response → ADK LlmResponse ----
    def _build_llm_response_from_openai(self, resp_json: Dict[str, Any]) -> LlmResponse:
        """
        Convert a single OpenAI-style chat completion into an ADK LlmResponse.
        """
        choices = resp_json.get("choices", [])
        if not choices:
            content_obj = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            return LlmResponse(content=content_obj)

        message = choices[0].get("message", {})
        parts: list[genai_types.Part] = []

        # 1) Tool calls
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            print(f"[StraicoLLM] Native tool calls detected: {[tc.get('function', {}).get('name') for tc in tool_calls]}")
            for tc in tool_calls:
                fn = tc.get("function", {}) or {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")

                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {"_raw": raw_args}

                fc = genai_types.FunctionCall(
                    name=name,
                    args=args,
                    id=tc.get("id"),
                )
                parts.append(genai_types.Part(function_call=fc))

        # 2) Assistant text (if any)
        text_content = message.get("content", "")
        
        # Workaround: Check for manual JSON tool call pattern if no native tool calls
        if not tool_calls and text_content:
            text_content = text_content.strip()
            if '"tool":' in text_content:
                print(f"[StraicoLLM] Manual JSON tool call detected in text")
                try:
                    clean_text = text_content.replace("```json", "").replace("```", "").strip()
                    
                    try:
                        data = json.loads(clean_text)
                    except json.JSONDecodeError:
                        import re
                        json_match = re.search(r'(\{[\s\S]*"tool":[\s\S]*\})', clean_text)
                        if json_match:
                            data = json.loads(json_match.group(1))
                        else:
                            raise ValueError("No JSON object found")

                    if "tool" in data and "arguments" in data:
                        print(f"[StraicoLLM] Parsed manual tool call: {data['tool']}")
                        fc = genai_types.FunctionCall(
                            name=data["tool"],
                            args=data["arguments"],
                            id="manual_call_" + os.urandom(4).hex()
                        )
                        parts.append(genai_types.Part(function_call=fc))
                        if len(text_content) < len(clean_text) + 20:
                            text_content = ""
                except Exception as e:
                    print(f"[StraicoLLM] Failed to parse manual tool call: {e}")

        if text_content:
            print(f"[StraicoLLM] Text content: {text_content[:200]}...")
            parts.append(genai_types.Part(text=text_content))

        if not parts:
            parts.append(genai_types.Part(text=""))

        content_obj = genai_types.Content(
            role="assistant",
            parts=parts,
        )

        return LlmResponse(content=content_obj)


    # ---- Main ADK entrypoint ----
    async def generate_content_async(  # type: ignore[override]
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        """
        Core bridge:
        - Receive ADK LlmRequest
        - Call Straico /chat/completions
        - Yield an ADK LlmResponse (with FunctionCall parts if tools were used)
        """

        if stream:
            print("[StraicoLLM] Streaming not implemented, falling back to single response.")

        model_id = llm_request.model
        messages = self._build_messages(llm_request)

        # Config → temperature / max_tokens
        temperature: float = 1.0
        max_tokens: int = 512

        cfg = llm_request.config
        if cfg is not None:
            t = getattr(cfg, "temperature", None)
            if t is not None:
                temperature = t
            mt = getattr(cfg, "max_output_tokens", None)
            if mt is not None:
                max_tokens = mt

        # Tools
        tools = self._build_tools(llm_request)

        body: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            body["tools"] = tools
            # Use "required" to force the model to call a tool when tools are available
            # This prevents the model from generating text instead of calling tools
            body["tool_choice"] = "required"
            print(f"[StraicoLLM] Sending {len(tools)} tools to API:")
            for tool in tools:
                print(f"  - {tool.get('function', {}).get('name', 'unknown')}")


        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        print(f"[StraicoLLM] Calling {model_id} with {len(messages)} messages, {len(tools)} tools")

        # Use aiohttp for async HTTP requests with extended timeout
        timeout = aiohttp.ClientTimeout(total=300, connect=60, sock_read=60)  # 5 min total, 1 min connect/read
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=body) as resp:
                    print(f"[StraicoLLM] Response status: {resp.status}")
                    
                    if resp.status == 404:
                        raise RuntimeError(
                            f"Straico 404 error: model '{model_id}' may not exist or account lacks access"
                        )
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"[StraicoLLM] Error response: {error_text}")
                        raise RuntimeError(f"Straico API error {resp.status}: {error_text}")
                    
                    resp_json = await resp.json()
                    print(f"[StraicoLLM] Received response with {len(resp_json.get('choices', []))} choices")
                    
                    # Debug: print the full response to see what we're getting
                    import json as json_lib
                    print(f"[StraicoLLM] Full response: {json_lib.dumps(resp_json, indent=2)[:1000]}...")
                    
        except asyncio.CancelledError:
            print("[StraicoLLM] Request was cancelled (likely timeout or user interrupt)")
            empty_content = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            yield LlmResponse(content=empty_content)
            return
        except asyncio.TimeoutError:
            print("[StraicoLLM] Request timed out")
            empty_content = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            yield LlmResponse(content=empty_content)
            return
        except aiohttp.ClientError as e:
            print(f"[StraicoLLM] HTTP error: {e}")
            empty_content = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            yield LlmResponse(content=empty_content)
            return
        except Exception as e:
            print(f"[StraicoLLM] Unexpected error: {type(e).__name__}: {e}")
            empty_content = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            yield LlmResponse(content=empty_content)
            return

        if not resp_json:
            empty_content = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            yield LlmResponse(content=empty_content)
            return

        llm_resp = self._build_llm_response_from_openai(resp_json)
        yield llm_resp

