"""
Proactive Data-Visualization Agent

Automatically scans uploaded datasets to find interesting signals,
converts them to natural language observations, and offers guided exploration choices.
"""

from .models import (
    SignalType,
    Signal,
    Observation,
    ExplorationChoice,
    ProactiveInsights,
    ExplorationSession,
    ExploreRequest,
    ChooseRequest,
    ExploreResponse,
    ChooseResponse,
)
from .agent import ProactiveAgent

# Create singleton instance
proactive_agent = ProactiveAgent()

__all__ = [
    # Models
    "SignalType",
    "Signal",
    "Observation",
    "ExplorationChoice",
    "ProactiveInsights",
    "ExplorationSession",
    "ExploreRequest",
    "ChooseRequest",
    "ExploreResponse",
    "ChooseResponse",
    # Agent
    "ProactiveAgent",
    "proactive_agent",
]
