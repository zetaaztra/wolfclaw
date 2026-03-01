import os
import time
import json
import threading
from pathlib import Path

# Try to import pynput, fail gracefully if not installed
try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

MACRO_DIR = Path.home() / "wolfclaw_macros"
MACRO_DIR.mkdir(exist_ok=True)

class MacroRecorder:
    def __init__(self):
        self.is_recording = False
        self.session_id = None
        self.session_dir = None
        self.actions = []
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.last_key_time = 0
        self.key_buffer = []

    def start_recording(self):
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput is not installed. Please install it to use the macro recorder.")
        
        if self.is_recording:
            return "Already recording."
            
        self.session_id = str(int(time.time()))
        self.session_dir = MACRO_DIR / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        self.actions = []
        self.is_recording = True
        
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
        # Take an initial screenshot
        self.capture_step("Session Started")
        
        return f"Recording started (Session: {self.session_id})"

    def stop_recording(self):
        if not self.is_recording:
            return "Not currently recording."
            
        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            
        # Flush key buffer
        if self.key_buffer:
            self.flush_keys()
            
        # Save actions list
        manifest_path = self.session_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump({"session_id": self.session_id, "actions": self.actions}, f, indent=2)
            
        res = self.session_dir
        self.session_id = None
        self.session_dir = None
        
        return f"Recording stopped. Saved to {res}"

    def capture_step(self, description, action_type="info", metadata=None):
        ts = int(time.time() * 1000)
        img_filename = f"step_{ts}.png"
        img_path = str(self.session_dir / img_filename) if self.session_dir else None
        
        if PIL_AVAILABLE and img_path:
            try:
                # Capture the screen
                img = ImageGrab.grab()
                img.save(img_path)
            except Exception:
                img_path = None
                
        action = {
            "timestamp": ts,
            "type": action_type,
            "description": description,
            "image": img_filename if img_path else None,
            "metadata": metadata or {}
        }
        self.actions.append(action)

    def on_click(self, x, y, button, pressed):
        if pressed:
            if self.key_buffer:
                self.flush_keys()
            
            # Capture Anchor (100x100 crop)
            ts = int(time.time() * 1000)
            anchor_filename = f"anchor_{ts}.png"
            anchor_path = self.session_dir / anchor_filename if self.session_dir else None
            
            if PIL_AVAILABLE and anchor_path:
                try:
                    # Capture 100x100 around the click
                    bbox = (int(x)-50, int(y)-50, int(x)+50, int(y)+50)
                    anchor_img = ImageGrab.grab(bbox=bbox)
                    anchor_img.save(anchor_path)
                except Exception:
                    anchor_filename = None

            self.capture_step(
                f"Clicked {button} at ({int(x)}, {int(y)})", 
                "click", 
                {
                    "x": int(x), 
                    "y": int(y), 
                    "button": str(button),
                    "anchor_image": anchor_filename
                }
            )

    def on_press(self, key):
        current_time = time.time()
        
        # If it's been a while since the last keypress, or it's a special key, flush
        if current_time - self.last_key_time > 2.0 and self.key_buffer:
            self.flush_keys()
            
        try:
            self.key_buffer.append(key.char)
        except AttributeError:
            # Special key (like Enter, Backspace)
            if self.key_buffer:
                self.flush_keys()
            self.capture_step(f"Pressed special key: {key}", "hotkey", {"key": str(key)})
            
        self.last_key_time = current_time

    def flush_keys(self):
        if not self.key_buffer:
            return
        typed_string = "".join(self.key_buffer)
        
        # Security filter for passwords/tokens
        import re
        if len(typed_string) >= 6 and " " not in typed_string and re.search(r'[A-Za-z]', typed_string) and (re.search(r'[0-9]', typed_string) or re.search(r'[^A-Za-z0-9\s]', typed_string)):
            display_text = "***[HIDDEN FOR SECURITY]***"
            self.capture_step("Typed secure text (Password/Token)", "type", {"text": display_text, "secure": True})
        else:
            self.capture_step(f"Typed: '{typed_string}'", "type", {"text": typed_string})
            
        self.key_buffer = []

# Global singleton
recorder = MacroRecorder()
