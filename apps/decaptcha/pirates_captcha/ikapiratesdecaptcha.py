"""
Ikariam pirate-fortress captcha solver.

Backed by a small CRNN (CNN + BiLSTM + CTC, ~1.66M params) trained on a
mix of ~65k synthetic and ~11k pseudo-labeled real captchas. Beats the
previous YOLOv8n model by 16 points of full-sequence accuracy on the
original validation set with a smaller model file (6.4 MB vs 12 MB).

Loaded via OpenCV's cv2.dnn — no new dependencies vs the previous
implementation. Public API (`get_captcha_string`) is preserved.

Model and training code: https://github.com/Mahrkeenerh/iKaptcha
"""

import os

import cv2.dnn
import numpy as np

current_directory = os.path.dirname(__file__)
onnx_model = os.path.join(current_directory, "ikaptcha.onnx")

model: cv2.dnn.Net = cv2.dnn.readNetFromONNX(onnx_model)

# 28-character vocabulary the captcha actually uses (the game server excludes
# visually ambiguous glyphs: 0, 1, 6, 8, 9, I, O, Z). Index 0 is the CTC blank.
CHARSET = "abcdefghjklmnpqrstuvwxy23457"
BLANK = 0
IDX_TO_CHAR = {i + 1: c for i, c in enumerate(CHARSET)}

IMG_H, IMG_W = 48, 256
MEAN = np.array([0.5, 0.5, 0.5], dtype=np.float32)
STD = np.array([0.5, 0.5, 0.5], dtype=np.float32)


def _preprocess(file_bytes: bytes) -> np.ndarray:
    """Decode -> resize 48x256 -> [-1, 1] normalize -> NCHW float32 batch."""
    arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)        # BGR HxWx3
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (IMG_W, IMG_H), interpolation=cv2.INTER_LINEAR)
    img = img.astype(np.float32) / 255.0
    img = (img - MEAN) / STD
    img = img.transpose(2, 0, 1)                     # CHW
    return img[None, ...].astype(np.float32)         # NCHW


def _greedy_ctc_decode(logits_tbc: np.ndarray) -> str:
    """CTC greedy decode on (T, 1, C) logits — collapse repeats, drop blanks."""
    indices = logits_tbc[:, 0, :].argmax(axis=1)     # (T,)
    chars = []
    prev = None
    for idx in indices.tolist():
        if idx != prev and idx != BLANK:
            chars.append(IDX_TO_CHAR[idx])
        prev = idx
    return "".join(chars)


def get_captcha_string(input_image) -> str:
    """Run inference on the input image and return the captcha string.

    Parameters
    ----------
    input_image : file-like
        Captcha image file object (anything with .read()).

    Returns
    -------
    captcha : str
        Predicted captcha string in uppercase, e.g. "K4PLB57A".
    """
    file_bytes = input_image.read()
    assert len(file_bytes) <= 50000, "File is too large"  # 50 KB max

    blob = _preprocess(file_bytes)
    model.setInput(blob)
    logits = model.forward()                          # (T, 1, C)
    return _greedy_ctc_decode(logits).upper()
