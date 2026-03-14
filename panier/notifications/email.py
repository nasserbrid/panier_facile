# panier/notifications/email.py
from __future__ import annotations

from typing import Mapping, Any

from .base import BaseNotification, NotificationData, NotificationError


class EmailNotification(BaseNotification):
    """Implémentation concrète pour l'envoi d'emails."""

    def __init__(self, smtp_client: Any) -> None:
        # smtp_client est injecté pour faciliter les tests (mock)
        self._smtp_client = smtp_client

    def send(self, data: NotificationData | Mapping[str, Any]) -> None:
        subject = getattr(data, "subject", None) or data["subject"]
        body = getattr(data, "body", None) or data["body"]
        to_email = getattr(data, "to_email", None) or data["to_email"]
        
        try:
            
            self._smtp_client.send_mail(
                to=to_email,  
                subject=subject,
                body=body,
            )
        except Exception as exc:  # loggue et wrappe
            raise NotificationError(f"Erreur d'envoi email vers {to_email}") from exc
