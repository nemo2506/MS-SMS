import base64
from pathlib import Path
from PIL import Image
import io

def encode_jpeg_to_base64_max600k(image_path: str) -> str:
    """
    Encode un fichier JPEG en base64, en réduisant la taille à <=600Ko si nécessaire (proportions conservées).
    """
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

        # Nouvelle boucle : réduire encore jusqu'à <= 600 Ko ou taille min atteinte
        img_copy = img.copy()
        while True:
            buffer = io.BytesIO()
            img_copy.save(buffer, format="JPEG", quality=30, optimize=True)
            encoded = encode_and_check(buffer.getvalue())
            if encoded:
                return encoded
            # Réduire encore la taille
            if img_copy.width <= min_width or img_copy.height <= min_height:
                break
            new_width = max(min_width, int(img_copy.width * 0.9))
            new_height = max(min_height, int(img_copy.height * 0.9))
            img_copy = img_copy.resize((new_width, new_height), Image.LANCZOS)

    raise ValueError("Impossible de réduire l'image à moins de 600 Ko en base64.")
