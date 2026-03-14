# panier/notifications/factory.py
from __future__ import annotations

from typing import Any, Callable, Dict

from .base import BaseNotification
from .email import EmailNotification
from .sms import SMSNotification


class NotificationFactory:
    """Fabrique de canaux de notifications."""

    def __init__(
        self,
        *,
        email_client: Any,
        sms_client: Any,
    ) -> None:
        # On prépare un registre de constructeurs pour chaque canal
        self._registry: Dict[str, Callable[[], BaseNotification]] = {
            "email": lambda: EmailNotification(email_client),
            "sms": lambda: SMSNotification(sms_client),
        }

    def register(self, channel: str, builder: Callable[[], BaseNotification]) -> None:
        """Permet d'ajouter d'autres canaux (push, slack, etc.)."""
        self._registry[channel] = builder

    def create(self, channel: str) -> BaseNotification:
        try:
            builder = self._registry[channel]
        except KeyError:
            raise ValueError(f"Canal de notification inconnu: {channel!r}")
        return builder()
