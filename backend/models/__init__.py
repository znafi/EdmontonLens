"""ORM model exports. Importing this module registers all tables on Base.metadata."""

from backend.models.neighbourhoods import (
    DelayPrediction,
    Neighbourhood,
    NeighbourhoodKpi,
)
from backend.models.parks import Park
from backend.models.transit import (
    TransitPerformance,
    TransitRoute,
    TransitStop,
    TransitStopDelay,
)
from backend.models.waste import WasteSchedule

__all__ = [
    "TransitRoute",
    "TransitStop",
    "TransitPerformance",
    "TransitStopDelay",
    "Park",
    "WasteSchedule",
    "Neighbourhood",
    "NeighbourhoodKpi",
    "DelayPrediction",
]
