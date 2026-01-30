"""
Pydantic models for the proactive agent.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class SignalType(str, Enum):
    """Types of detected signals in the data"""
    TREND = "trend"
    OUTLIER = "outlier"
    DOMINANCE = "dominance"
    SEASONALITY = "seasonality"
    IMBALANCE = "imbalance"


class Signal(BaseModel):
    """Represents a detected signal in the data"""
    signal_id: str
    signal_type: SignalType
    columns: List[str]
    strength: float  # 0.0-1.0
    metadata: Dict[str, Any]


class Observation(BaseModel):
    """Natural language observation derived from a signal"""
    observation_id: str
    signal_id: str
    text: str  # e.g., "Revenue shows 23% upward trend over 6 months"
    importance: str  # "high", "medium", "low"


class ExplorationChoice(BaseModel):
    """A choice for exploring an observation further"""
    choice_id: str
    observation_id: str
    text: str  # e.g., "Would you like to explore what's driving this trend?"
    suggested_chart: str  # "line_with_trendline", "pie", "scatter", etc.
    sql_template: Optional[str] = None


class ProactiveInsights(BaseModel):
    """Complete insights package for a dataset"""
    dataset_id: str
    signals: List[Signal]
    observations: List[Observation]
    choices: List[ExplorationChoice]
    computed_at: datetime


class ExplorationSession(BaseModel):
    """State of an exploration session"""
    session_id: str
    user_id: str
    dataset_id: str
    exploration_path: List[Dict[str, Any]]  # choices made
    current_state: Dict[str, Any]
    created_at: datetime


# Request/Response models for API endpoints

class ExploreRequest(BaseModel):
    """Request to start an exploration session"""
    dataset_id: str
    observation_id: Optional[str] = None  # Start from specific observation


class ChooseRequest(BaseModel):
    """Request to make a choice in exploration"""
    choice_id: str


class ExploreResponse(BaseModel):
    """Response when starting exploration"""
    session_id: str
    current_observation: Optional[Observation] = None
    available_choices: List[ExplorationChoice]
    context: Dict[str, Any]  # Additional context data


class ChooseResponse(BaseModel):
    """Response after making a choice"""
    success: bool
    sql_executed: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    result_count: int = 0
    follow_up_observation: Optional[Observation] = None
    follow_up_choices: List[ExplorationChoice] = []
    message: str = ""
