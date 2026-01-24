"""
Probabilistic Tools - Tools using probabilistic programming for AI assistance.

Modules:
- smart_router: Routes queries between expensive LLM and cheap rule-based handlers
"""

from amplifier.prob_tools.smart_router import (
    SmartRouter,
    QueryFeatures,
    RoutingDecision,
    RoutingOutcome,
    RouteTarget,
)

__all__ = [
    "SmartRouter",
    "QueryFeatures",
    "RoutingDecision",
    "RoutingOutcome",
    "RouteTarget",
]
