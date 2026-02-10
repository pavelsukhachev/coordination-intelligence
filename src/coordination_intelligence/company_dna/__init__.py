"""Company DNA configuration and decision engine.

The Company DNA encodes organizational values, decision principles,
authority thresholds, and communication preferences. The DecisionEngine
evaluates proposed actions against this DNA to ensure alignment.
"""

from coordination_intelligence.company_dna.engine import DecisionEngine
from coordination_intelligence.company_dna.schema import CompanyDNA

__all__ = ["CompanyDNA", "DecisionEngine"]
