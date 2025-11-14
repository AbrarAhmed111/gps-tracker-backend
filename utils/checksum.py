import base64
import hashlib
from typing import Literal


def compute_checksum_base64(
    file_content_b64: str,
    algorithm: Literal["md5", "sha1", "sha256"] = "sha256",
) -> str:
    data = base64.b64decode(file_content_b64)
    if algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    if algorithm == "sha1":
        return hashlib.sha1(data).hexdigest()
    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    raise ValueError("Unsupported algorithm")


def checksum_text_md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()

