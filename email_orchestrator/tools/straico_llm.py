import os
import requests
from typing import AsyncGenerator, Dict, Any
from dotenv import load_dotenv
from email_orchestrator.tools.trace_manager import TRACE
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part  # Might be needed depending on ADK version

load_dotenv()

class StraicoLLM(BaseLlm):
    model: str

    def __init__(self, *, model: str, api_key: str = None, base_url: str = "https://api.straico.com/v2"):
        super().__init__(model=model)
        self._api_key = api_key or os.getenv("STRAICO_API_KEY")
        if not self._api_key:
            raise ValueError("STRAICO_API_KEY not set")
        self._base_url = base_url.rstrip("/")

    @classmethod
    def supported_models(cls) -> list[str]:
        return [
            "openai/gpt-4-turbo-2024-04-09",
            "openai/gpt-4o-2024-08-06",
            "openai/gpt-4o-mini",
            "amazon/nova-micro-v1",
            # add more if you like
        ]

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        model_id = llm_request.model

        # Build messages list
        messages = []
        for m in llm_request.contents:
            m_dict = m.dict()
            if "parts" in m_dict:
                content = "".join(part.get("text", "") for part in m_dict["parts"])
            else:
                content = m_dict.get("content", "")
            messages.append({"role": m_dict.get("role", "user"), "content": content})

        # Handle temperature and max_tokens defaults
        temperature = getattr(llm_request.config, "temperature", None)
        if temperature is None:
            temperature = 1.0
        max_tokens = getattr(llm_request.config, "max_output_tokens", None)
        if max_tokens is None:
            max_tokens = 512

        body = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        url = f"{self._base_url}/chat/completions"   # updated path
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # DEBUG logs
        #print("STRAICO REQUEST → URL:", url)
        #print("STRAICO REQUEST → HEADERS:", headers)
        #print("STRAICO REQUEST → BODY:", body)
        TRACE.log_llm_request(agent=self.model, messages=messages)
        resp = requests.post(url, headers=headers, json=body)

        #print("STRAICO RESPONSE → status:", resp.status_code)
        try:
            resp_json = resp.json()
        except ValueError:
            resp_json = None
        #print("STRAICO RESPONSE → json:", resp_json)

        if resp.status_code == 404:
            raise RuntimeError(f"Straico 404 error: model '{model_id}' may not exist or account lacks access")

        resp.raise_for_status()

        # Parse the response to extract the assistant's message
        if resp_json and "choices" in resp_json and len(resp_json["choices"]) > 0:
            # … inside your generate_content_async method …
            assistant_text = resp_json["choices"][0]["message"]["content"]
            TRACE.log_llm_response(agent=self.model, content=assistant_text)

            # Build Content object
            content_obj = Content(
                parts=[Part(text=assistant_text)],  # may vary if you want more fields
                role="assistant",
            )

            # Build the response
            llm_resp = LlmResponse(
                content=content_obj
            )
            yield llm_resp
