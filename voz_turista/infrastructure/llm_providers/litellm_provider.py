import json
from typing import Any, Dict, List, Type, Union

import litellm
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from voz_turista.infrastructure.llm_providers.base import LLMProvider


class LiteLLMProvider(LLMProvider):
    """
    Implementación de LLMProvider usando LiteLLM.
    Soporta 100+ proveedores de LLM (OpenAI, Anthropic, Google, Groq, etc.).
    Formato de modelo: "gemini/gemini-2.5-flash", "gpt-4o", "groq/llama-3.1-70b", etc.
    """

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.system_prompt = system_prompt

    def generate(self, messages: List[BaseMessage], **kwargs) -> str:
        response = litellm.completion(
            model=self.model_name,
            messages=self._convert_messages(messages),
            temperature=self.temperature,
            **kwargs,
        )
        return response.choices[0].message.content

    def generate_structured(
        self,
        messages: List[BaseMessage],
        schema: Union[Type[BaseModel], Dict[str, Any]],
        **kwargs,
    ) -> Any:
        response = litellm.completion(
            model=self.model_name,
            messages=self._convert_messages(messages),
            temperature=self.temperature,
            response_format=self._build_response_format(schema),
            **kwargs,
        )
        content = response.choices[0].message.content
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate_json(content)
        return json.loads(content)

    @staticmethod
    def _build_response_format(
        schema: Union[Type[BaseModel], Dict[str, Any]],
    ) -> Any:
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema.get("title", "response"),
                "schema": schema,
            },
        }

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        role_map = {
            HumanMessage: "user",
            SystemMessage: "system",
            AIMessage: "assistant",
        }
        converted = [
            {"role": role_map.get(type(m), "user"), "content": m.content}
            for m in messages
        ]
        if self.system_prompt and not any(m["role"] == "system" for m in converted):
            converted.insert(0, {"role": "system", "content": self.system_prompt})
        return converted
