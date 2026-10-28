"""Shared validation for privacy-safe in-memory image uploads."""

from fastapi import UploadFile

from classsnap.config import get_settings
from classsnap.exceptions import ValidationError


async def read_image_upload(upload: UploadFile) -> bytes:
    content_type = (upload.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise ValidationError("Uploaded file must have an image media type")

    data = await upload.read()
    max_size = get_settings().max_upload_size_bytes
    if len(data) > max_size:
        raise ValidationError(
            f"Uploaded image exceeds the maximum size of {max_size} bytes"
        )
    if not data:
        raise ValidationError("Uploaded image is empty")
    return data
