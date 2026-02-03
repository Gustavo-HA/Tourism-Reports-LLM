from typing import Any, Dict, List, Type, Union

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from voz_turista.infrastructure.llm_providers.base import LLMProvider


class LangChainGoogleProvider(LLMProvider):
    """
    Implementación de LLMProvider usando LangChain y Google Generative AI (Gemini).
    """

    def __init__(self, model_name: str = "gemini-2.5-pro", temperature: float = 0.0):
        # Se asume que GOOGLE_API_KEY está en las variables de entorno
        self.model = ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

    def generate(self, messages: List[BaseMessage], **kwargs) -> str:
        response = self.model.invoke(messages, **kwargs)
        return response.content

    def generate_structured(
        self,
        messages: List[BaseMessage],
        schema: Union[Type[BaseModel], Dict[str, Any]],
        **kwargs,
    ) -> Any:
        # Gemini soporta salida estructurada mediante with_structured_output
        structured_llm = self.model.with_structured_output(schema)
        return structured_llm.invoke(messages, **kwargs)
