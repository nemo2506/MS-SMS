from .client import MessagePlugin
from .exceptions import APIError
from .models import SendMessageResult

class MessageController:
    """
    Contrôleur pour l'envoi de messages SMS via MessagePlugin (MVC).
    """
    def __init__(self, base_url: str, bearer_token: str, sender_id: str = ""):
        self.plugin = MessagePlugin(
            base_url=base_url,
            bearer_token=bearer_token,
            sender_id=sender_id,
        )

    def send_message(self, recipient: str, text: str, image_path: str = None) -> SendMessageResult:
        """
        Envoie un message SMS (avec ou sans image) via le client plugin.
        Retourne un SendMessageResult ou lève une exception APIError/ValueError/TypeError.
        """
        return self.plugin.send(recipient=recipient, text=text, image_path=image_path)
