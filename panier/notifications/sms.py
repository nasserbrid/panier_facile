# panier/notifications/sms.py
from __future__ import annotations

from typing import Mapping, Any

from .base import BaseNotification, NotificationData, NotificationError


class SMSNotification(BaseNotification):
    """Implémentation concrète pour l'envoi de SMS."""

    def __init__(self, sms_client: Any) -> None:
        self._sms_client = sms_client

    def send(self, data: NotificationData | Mapping[str, Any]) -> None:
        body = getattr(data, "body", None) or data["body"]
        to_phone = getattr(data, "to_phone", None) or data["to_phone"]
        
        #vérification que le numéro de téléphone est présent
        if not to_phone:
            raise NotificationError("Erreur SMS impossible car le Numéro de téléphone est manquant pour l'envoi du SMS")

        try:
            
            self._sms_client.send_sms(
                to=to_phone,
                message=body,
            )
        except Exception as exc:
            raise NotificationError(f"Erreur d'envoi SMS vers {to_phone}") from exc
