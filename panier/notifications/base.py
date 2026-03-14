# panier/notifications/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, Any, Mapping, Optional


@runtime_checkable
class NotificationData(Protocol):
    """Contrat minimal pour les données de notification."""
    subject: str
    body: str
    to_email: Optional[str] = None  # pour email
    to_phone: Optional[str] = None  # pour SMS


class NotificationError(Exception):
    """Erreur générale de notification."""


class BaseNotification(ABC):
    """Canal de notification abstrait (email, SMS, etc.)."""

    @abstractmethod
    def send(self, data: NotificationData | Mapping[str, Any]) -> None:
        """Envoie la notification via le canal concret."""
        raise NotImplementedError
