import os
import json
import requests
from typing import AsyncGenerator, Dict, Any

from dotenv import load_dotenv

from google.adk.models.base_llm import BaseLlm  # type: ignore
from google.adk.models.llm_request import LlmRequest  # type: ignore
from google.adk.models.llm_response import LlmResponse  # type: ignore

from google.genai import types as genai_types  # type: ignore

load_dotenv()


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
            "openai/gpt-4o-2024-08-06",
            "openai/gpt-4-turbo-2024-04-09",
            "amazon/nova-micro-v1",
            # add more here if you want to experiment
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
        # Check llm_request.system_instruction (direct) or llm_request.config.system_instruction
        sys_content = getattr(llm_request, "system_instruction", None)
        if not sys_content and getattr(llm_request, "config", None):
            sys_content = getattr(llm_request.config, "system_instruction", None)

        if sys_content:
            # sys_content is usually a Content object or string
            sys_text = ""
            if isinstance(sys_content, str):
                sys_text = sys_content
            elif hasattr(sys_content, "parts"):
                # It's a Content object
                sys_text = "".join([p.text for p in sys_content.parts if p.text])
            
            if sys_text:
                messages.append({"role": "system", "content": sys_text})

        for content in llm_request.contents:
            # Content is a Pydantic model; model_dump() is the safest way.
            c = content.model_dump()
            role = c.get("role", "user")
            text_parts: list[str] = []

            for part in c.get("parts", []):
                # We only care about plain text for the outbound request.
                if "text" in part and part["text"]:
                    text_parts.append(part["text"])

            text = "".join(text_parts).strip()
            if not text:
                # Skip purely non-text content (e.g., function_call-only parts)
                continue

            messages.append({"role": role, "content": text})

        if not messages:
            # Fallback safety: at least send something
            messages.append({"role": "user", "content": ""})

        return messages

    # ---- Helper: map ADK tools → OpenAI tools schema ----
    def _build_tools(self, llm_request: LlmRequest) -> list[Dict[str, Any]]:
        """
        Convert ADK BaseTool map to OpenAI \"tools\" list.

        Uses llm_request.tools_dict (the internal ADK mapping of tool names
        to BaseTool instances).
        """
        tools_payload: list[Dict[str, Any]] = []

        # ✅ This is the correct field in Python ADK
        tools_map: Dict[str, Any] = getattr(llm_request, "tools_dict", {}) or {}

        if not tools_map:
            # No tools for this request → no function calling
            return tools_payload

        # DEBUG
        print(f"[StraicoLLM] Extracting tools from request. Found: {list(tools_map.keys())}")

        for tool_name, tool in tools_map.items():
            # Each tool is a BaseTool (AgentTool, FunctionTool, etc.)
            # Try to get the FunctionDeclaration from the tool.
            fn_decl = None
            try:
                fn_decl = tool.declaration()
            except Exception as e:
                print(f"[StraicoLLM] Error getting declaration for tool {tool_name}: {e}")
                fn_decl = None

            if fn_decl is not None:
                # fn_decl is google.genai.types.FunctionDeclaration
                fn = fn_decl
                # Try to get a parameters schema; fallback to a generic object.
                params: Dict[str, Any] = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
                try:
                    if getattr(fn, "parameters", None) is not None:
                        # parameters is usually a Schema object with model_dump()
                        params = fn.parameters.model_dump()
                        
                        # Sanitize types to be lowercase for OpenAI (STRING -> string, OBJECT -> object)
                        # And remove null values/empty fields to keep it clean
                        def clean_schema(node):
                            if isinstance(node, dict):
                                clean_node = {}
                                
                                # 1. Handle "properties" specifically (keys are arbitrary param names)
                                if "properties" in node and isinstance(node["properties"], dict):
                                    clean_props = {}
                                    for prop_name, prop_def in node["properties"].items():
                                        clean_props[prop_name] = clean_schema(prop_def)
                                    clean_node["properties"] = clean_props
                                
                                # 2. Handle "items" (recursive schema)
                                if "items" in node and node["items"] is not None:
                                    clean_node["items"] = clean_schema(node["items"])

                                # 3. Handle other standard keys
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
                        
                        # Ensure required is a list if present
                        if "required" in params and params["required"] is None:
                            del params["required"]
                except Exception:
                    pass

                tools_payload.append(
                    {
                        "type": "function",
                        "function": {
                            "name": fn.name,
                            "description": getattr(fn, "description", "") or "",
                            "parameters": params,
                        },
                    }
                )
            else:
                # If no declaration(), still expose a minimal tool definition.
                tools_payload.append(
                    {
                        "type": "function",
                        "function": {
                            "name": getattr(tool, "name", tool_name),
                            "description": getattr(tool, "description", "") or "",
                        },
                    }
                )

        return tools_payload


    # ---- Helper: map Straico response → ADK LlmResponse ----
    def _build_llm_response_from_openai(self, resp_json: Dict[str, Any]) -> LlmResponse:
        """
        Convert a single OpenAI-style chat completion into an ADK LlmResponse.
        Supports:
        - Plain assistant text
        - Tool calls (function calling)
        """
        choices = resp_json.get("choices", [])
        if not choices:
            # Empty response – return an empty content
            content_obj = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            return LlmResponse(content=content_obj)

        message = choices[0].get("message", {})  # type: ignore[assignment]

        parts: list[genai_types.Part] = []

        # 1) Tool calls
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            print("[StraicoLLM] Tool calls from Straico:", tool_calls)

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
        # Pattern: {"tool": "tool_name", "arguments": {...}}
        if not tool_calls and text_content:
            text_content = text_content.strip()
            # Check if it contains the tool pattern
            if '"tool":' in text_content:
                try:
                    # 1. Clean markdown code blocks
                    clean_text = text_content.replace("```json", "").replace("```", "").strip()
                    
                    # 2. Try parsing the whole cleaned string
                    try:
                        data = json.loads(clean_text)
                    except json.JSONDecodeError:
                        # 3. If that fails, try regex (greedy match to catch nested objects)
                        import re
                        # Greedy match from first { to last }
                        json_match = re.search(r'(\{[\s\S]*"tool":[\s\S]*\})', clean_text)
                        if json_match:
                            data = json.loads(json_match.group(1))
                        else:
                            raise ValueError("No JSON object found")

                    if "tool" in data and "arguments" in data:
                            print(f"[StraicoLLM] Detected manual JSON tool call: {data['tool']}")
                            fc = genai_types.FunctionCall(
                                name=data["tool"],
                                args=data["arguments"],
                                id="manual_call_" + os.urandom(4).hex()
                            )
                            parts.append(genai_types.Part(function_call=fc))
                            # If we successfully parsed a tool call, we might want to suppress the text
                            # or keep it if it contains other info. 
                            # For now, if the entire content is just the JSON, suppress text.
                            if len(text_content) < len(json_str) + 20: # heuristic
                                text_content = ""
                except Exception as e:
                    print(f"[StraicoLLM] Failed to parse manual tool call: {e}")

        if text_content:
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
            # For now we don't implement streaming with Straico in this MVP.
            # ADK will still work fine; it just gets one response.
            print("[StraicoLLM] Streaming not implemented, falling back to single response.")

        model_id = llm_request.model

        # 1) Messages
        # print(f"[StraicoLLM] LlmRequest dict keys: {llm_request.__dict__.keys()}")
        # if getattr(llm_request, "append_instructions", None):
        #      print(f"[StraicoLLM] append_instructions: {llm_request.append_instructions}")
        # if getattr(llm_request, "config", None):
        #      print(f"[StraicoLLM] config: {llm_request.config}")
        
        messages = self._build_messages(llm_request)

        # 2) Config → temperature / max_tokens
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

        # 3) Tools
        tools = self._build_tools(llm_request)

        body: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            body["tools"] = tools
            # Force the model to use tools if available, or at least be very explicit
            body["tool_choice"] = "auto" 
            # Try forcing the specific tool by name to be absolutely sure
            # body["tool_choice"] = {
            #     "type": "function",
            #     "function": {
            #         "name": tools[0]["function"]["name"]
            #     }
            # }
            print(f"[StraicoLLM] Sending {len(tools)} tools to Straico: {[t['function']['name'] for t in tools]}")
            print(f"[StraicoLLM] Full tools payload: {json.dumps(tools, indent=2)}")

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # DEBUG (you can comment these out later)
        print("[StraicoLLM] REQUEST URL:", url)
        print("[StraicoLLM] REQUEST BODY:", json.dumps(body, indent=2)[:2000])

        resp = requests.post(url, headers=headers, json=body)

        print("[StraicoLLM] RESPONSE STATUS:", resp.status_code)
        try:
            resp_json = resp.json()
        except ValueError:
            resp_json = None
        print("[StraicoLLM] RESPONSE JSON (truncated):", str(resp_json)[:2000])

        if resp.status_code == 404:
            raise RuntimeError(
                f"Straico 404 error: model '{model_id}' may not exist or account lacks access"
            )

        resp.raise_for_status()

        if not resp_json:
            # Yield an empty response rather than crashing
            empty_content = genai_types.Content(
                role="assistant",
                parts=[genai_types.Part(text="")],
            )
            yield LlmResponse(content=empty_content)
            return

        llm_resp = self._build_llm_response_from_openai(resp_json)
        yield llm_resp
