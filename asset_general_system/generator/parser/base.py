from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import GenerateRequest, RPGMapSpec


class PromptParser(ABC):
    @abstractmethod
    def parse(self, request: GenerateRequest) -> RPGMapSpec:
        raise NotImplementedError
