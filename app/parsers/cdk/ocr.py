"""OCR helpers for CDK printed reports."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import cv2
import numpy as np
import pytesseract
from PIL import Image


def _load_image(source: bytes | BinaryIO) -> np.ndarray:
    if isinstance(source, bytes):
        source = BytesIO(source)
    data = np.frombuffer(source.read(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")
    return img


def preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """Enhance a phone photo of a dot-matrix printout for OCR."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    scale = 2.0 if max(gray.shape) < 2400 else 1.5
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_text(source: bytes | BinaryIO) -> str:
    """Run OCR on a single report photo."""
    img = _load_image(source)
    processed = preprocess_for_ocr(img)
    return pytesseract.image_to_string(
        processed,
        config="--psm 6 -c preserve_interword_spaces=1",
    )


def extract_text_from_images(sources: list[bytes]) -> str:
    """OCR multiple pages and join with newlines."""
    chunks: list[str] = []
    for source in sources:
        chunks.append(extract_text(source))
    return "\n".join(chunks)
