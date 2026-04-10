"""
Client HTTP pour l'endpoint /api/send-message.
"""

import base64
import json
from pathlib import Path
from PIL import Image
import io
import requests

from .exceptions import APIError
from .models import SendMessageResult


class MessagePlugin:
    """
    Client Python pour l'endpoint POST /api/send-message.

    Exemple d'utilisation rapide :
        from ms_sms import MessagePlugin, APIError

        plugin = MessagePlugin(
            base_url="https://monapi.com",
            bearer_token="mon_token",
            sender_id="MonApp",
        )

        # SMS simple
        result = plugin.send(recipient="0634058195", text="Bonjour !")
        print(result)

        # SMS + image JPEG
        result = plugin.send(
            recipient="0634058195",
            text="Voici une photo",
            image_path="photo.jpg",
        )

        # Gestion des erreurs
        try:
            result = plugin.send(recipient="0634058195", text="Test")
        except APIError as e:
            print(e.error)   # message d'erreur de l'API
            print(e.code)    # code applicatif (ou None)
            print(e.status)  # code HTTP
    """

    def __init__(
        self,
        base_url: str,
        bearer_token: str,
        sender_id: str = "",
        timeout: int = 30,
    ):
        """
        Initialise le client.

        Args:
            base_url      : URL de base de l'API (ex: "https://monapi.com")
            bearer_token  : Token d'authentification Bearer
            sender_id     : Identifiant de l'expéditeur (senderId)
            timeout       : Timeout des requêtes HTTP en secondes (défaut 30)
        """
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/send-message"
        self.sender_id = sender_id
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Méthode publique
    # ------------------------------------------------------------------

    def send(
        self,
        recipient: str,
        text: str,
        image_path: str = None,
    ) -> SendMessageResult:
        """
        Envoie un SMS avec ou sans image JPEG.

        Args:
            recipient  : Numéro du destinataire (ex: "0634058195")
            text       : Texte du message
            image_path : Chemin local vers un fichier JPEG (optionnel)

        Returns:
            SendMessageResult

        Raises:
            ValueError           : recipient ou text vide
            FileNotFoundError    : Fichier image introuvable
            TypeError            : Le fichier n'est pas un JPEG
            APIError             : L'API retourne success=false ou HTTP 4xx/5xx
            requests.Timeout     : Délai de connexion dépassé
            requests.ConnectionError : Serveur inaccessible
        """
        if not recipient:
            raise ValueError("Le numéro de destinataire est obligatoire.")
        if not text:
            raise ValueError("Le texte du message est obligatoire.")

        payload = {
            "senderId":   self.sender_id,
            "recipient":  recipient,
            "text":       text,
            "base64Jpeg": self._encode_image(image_path) if image_path else "",
        }

        return self._post(payload)

    # ------------------------------------------------------------------
    # Encodage de l'image
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(image_path: str) -> str:
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Fichier image introuvable : {image_path}")

        if path.suffix.lower() not in (".jpg", ".jpeg"):
            raise TypeError(
                f"Seuls les fichiers JPEG sont acceptés (reçu : '{path.suffix}')."
            )

        def encode_and_check(img_bytes):
            encoded = base64.b64encode(img_bytes).decode("utf-8")
            if len(encoded.encode("utf-8")) > 614400:
                return None
            return encoded

        # Première tentative avec l'image d'origine
        with open(path, "rb") as f:
            img_bytes = f.read()
            encoded = encode_and_check(img_bytes)
            if encoded:
                return encoded

        # Si trop gros, on tente de réduire la taille et la qualité
        with Image.open(path) as img:
            for quality in [85, 70, 50, 30]:
                img_copy = img.copy()
                # Réduction de la taille max, proportions conservées
                img_copy.thumbnail((1024, 1024), Image.LANCZOS)
                buffer = io.BytesIO()
                img_copy.save(buffer, format="JPEG", quality=quality, optimize=True)
                encoded = encode_and_check(buffer.getvalue())
                if encoded:
                    return encoded

            # Dernière tentative : réduire encore la taille
            min_width, min_height = 200, 200
            img_copy = img.copy()
            while img_copy.width > min_width and img_copy.height > min_height:
                new_width = max(min_width, int(img_copy.width * 0.8))
                new_height = max(min_height, int(img_copy.height * 0.8))
                img_copy = img_copy.resize((new_width, new_height), Image.LANCZOS)
                buffer = io.BytesIO()
                img_copy.save(buffer, format="JPEG", quality=30, optimize=True)
                encoded = encode_and_check(buffer.getvalue())
                if encoded:
                    return encoded

        raise ValueError("Impossible de réduire l'image à moins de 600 Ko en base64.")

    # ------------------------------------------------------------------
    # Appel HTTP + gestion des erreurs
    # ------------------------------------------------------------------

    def _post(self, payload: dict) -> SendMessageResult:
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise requests.Timeout(
                f"Le serveur n'a pas répondu dans le délai imparti ({self.timeout}s)."
            )
        except requests.ConnectionError:
            raise requests.ConnectionError(
                f"Impossible de joindre le serveur : {self.base_url}"
            )

        data = self._parse_json(response)

        if data is not None:
            if not data.get("success", True):
                raise APIError(
                    error=data.get("error", "Erreur inconnue retournée par l'API"),
                    code=data.get("code"),
                    timestamp=data.get("timestamp", 0),
                    status=response.status_code,
                    raw=data,
                )
            return SendMessageResult.from_dict(data)

        if not response.ok:
            raise APIError(
                error=self._http_fallback_message(response.status_code),
                code=response.status_code,
                status=response.status_code,
                raw={"raw_text": response.text},
            )

        raise APIError(
            error="Réponse inattendue du serveur (pas de JSON valide).",
            status=response.status_code,
            raw={"raw_text": response.text},
        )

    @staticmethod
    def _parse_json(response: requests.Response):
        try:
            return response.json()
        except Exception:
            return None

    @staticmethod
    def _http_fallback_message(status: int) -> str:
        messages = {
            400: "Requête invalide (400 Bad Request).",
            401: "Authentification requise ou token invalide (401 Unauthorized).",
            403: "Accès refusé (403 Forbidden).",
            404: "Endpoint introuvable (404 Not Found).",
            408: "Délai de la requête dépassé côté serveur (408 Request Timeout).",
            422: "Données invalides rejetées par le serveur (422 Unprocessable Entity).",
            429: "Trop de requêtes, limite de débit atteinte (429 Too Many Requests).",
            500: "Erreur interne du serveur (500 Internal Server Error).",
            502: "Mauvaise passerelle (502 Bad Gateway).",
            503: "Service temporairement indisponible (503 Service Unavailable).",
        }
        return messages.get(status, f"Erreur HTTP inattendue ({status}).")
