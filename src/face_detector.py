"""Face detection with OpenCV's bundled Haar cascade.

Haar cascades are fast, CPU-only, need no download, and work well on frontal
faces. They miss strongly turned or tilted faces, which is acceptable here
because the emotion model was itself trained on roughly frontal faces.
"""
import cv2
import numpy as np

from src import config

Box = tuple[int, int, int, int]  # x, y, width, height


class FaceDetector:
    def __init__(self, cascade_file: str = config.HAAR_CASCADE_FILE):
        path = cv2.data.haarcascades + cascade_file
        self.cascade = cv2.CascadeClassifier(path)
        if self.cascade.empty():
            raise RuntimeError(f"Could not load Haar cascade from {path}. Reinstall opencv-python (4.x).")

    def detect(self, image: np.ndarray, downscale: float = 1.0) -> list[Box]:
        """Return face boxes sorted left to right.

        ``downscale`` < 1 runs detection on a smaller copy (much faster for
        webcam frames); boxes are mapped back to the original resolution.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        if downscale != 1.0:
            gray = cv2.resize(gray, None, fx=downscale, fy=downscale, interpolation=cv2.INTER_AREA)
        gray = cv2.equalizeHist(gray)  # helps under uneven lighting
        min_size = max(1, int(config.MIN_DETECT_FACE_SIZE * downscale))
        faces = self.cascade.detectMultiScale(
            gray,
            scaleFactor=config.FACE_SCALE_FACTOR,
            minNeighbors=config.FACE_MIN_NEIGHBORS,
            minSize=(min_size, min_size),
        )
        boxes = [tuple(int(round(v / downscale)) for v in face) for face in faces]
        return sorted(boxes, key=lambda b: b[0])


def crop_face(image: np.ndarray, box: Box, padding: float = config.FACE_PADDING) -> np.ndarray:
    """Crop a face with a small margin, clipped to the image borders.

    FER-2013 faces include some forehead and chin, so a little padding around
    the tighter Haar box brings the crop closer to the training distribution.
    """
    x, y, w, h = box
    pad_w, pad_h = int(w * padding), int(h * padding)
    top, left = max(0, y - pad_h), max(0, x - pad_w)
    bottom, right = min(image.shape[0], y + h + pad_h), min(image.shape[1], x + w + pad_w)
    return image[top:bottom, left:right]
