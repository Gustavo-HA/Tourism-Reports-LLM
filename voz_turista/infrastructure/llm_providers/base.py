from abc import ABC, abstractmethod
from typing import Any, Dict, List
from langchain_core.messages import BaseMessage


class LLMProvider(ABC):
    """
    Interfaz base para proveedores de LLM.
    Permite desacoplar la lógica de negocio del proveedor específico (OpenAI, Anthropic, Local, etc.).
    """

    @abstractmethod
    def generate(self, messages: List[BaseMessage], **kwargs) -> str:
        """
        Genera una respuesta de texto basada en una lista de mensajes.
        """
        pass

    @abstractmethod
    def generate_structured(
        self, messages: List[BaseMessage], schema: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Genera una respuesta estructurada (JSON) validada contra un esquema.
        """
        pass
