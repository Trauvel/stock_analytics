"""Value Objects для рекомендаций."""

from .action import Action, ActionType
from .confidence import Confidence, ConfidenceLevel

__all__ = ["Action", "ActionType", "Confidence", "ConfidenceLevel"]
