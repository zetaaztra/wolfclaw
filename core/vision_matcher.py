import cv2
import numpy as np
import logging
from PIL import ImageGrab

logger = logging.getLogger(__name__)

class VisionMatcher:
    """
    Core engine for 'Self-Healing' macros. 
    Finds visual anchors on screen using OpenCV template matching.
    """

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def find_anchor(self, anchor_path: str) -> tuple:
        """
        Scans the current screen for the anchor image.
        Returns (x, y) center of the match, or None if not found.
        """
        if not os.path.exists(anchor_path):
            logger.error(f"Anchor image not found: {anchor_path}")
            return None

        # Load anchor (template)
        template = cv2.imread(anchor_path, cv2.IMREAD_COLOR)
        if template is None:
            return None
        
        h, w = template.shape[:2]

        # Capture current screen
        screen_pil = ImageGrab.grab()
        screen_np = np.array(screen_pil)
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        # Template Matching
        res = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= self.threshold:
            # Calculate center of the match
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            logger.info(f"Anchor found at ({center_x}, {center_y}) with confidence {max_val:.2f}")
            return (center_x, center_y)
        
        logger.warning(f"Anchor not found. Max confidence: {max_val:.2f}")
        return None

# Singleton
vision_matcher = VisionMatcher()

def get_matcher():
    return vision_matcher

import os # Required for path checks
