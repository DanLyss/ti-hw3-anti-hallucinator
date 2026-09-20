from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Отправляет промпт модели, возвращает сырой текстовый ответ."""
        raise NotImplementedError
