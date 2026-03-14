# Expose uniquement run_agent pour simplifier les imports dans les vues :
# from panier.agent import run_agent
from .runner import run_agent

__all__ = ["run_agent"]
