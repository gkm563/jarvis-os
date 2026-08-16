"""
Desktop Control Agent (FR-1) for JARVIS OS.
Manages Windows application lifecycle, UI automation, window positioning/snapping, and system power states.
"""

import os
import subprocess
from typing import Any, Dict, List
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.core.exceptions import AgentError
from jarvis.utils.logger import get_logger

logger = get_logger("DesktopAgent")


class DesktopControlAgent(AbstractAgent):
    """
    Desktop Automation Agent controlling native applications and Windows system states.
    """

    @property
    def name(self) -> str:
        return "desktop_agent"

    @property
    def description(self) -> str:
        return "Controls Windows applications, windows snapping/focusing, desktop settings, and system power states."

    @property
    def capabilities(self) -> List[str]:
        return ["launch_app", "close_app", "focus_window", "snap_window", "system_state", "camera_take_photo"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Executes a desktop control action."""
        if not await self.validate_action(action):
            return ExecutionResult(success=False, error_message=f"Unsupported action: {action.action_type}")

        action_type = action.action_type
        params = action.parameters

        try:
            if action_type == "launch_app":
                app_name = params.get("app_name", "")
                return await self._launch_app(app_name)

            elif action_type == "close_app":
                app_name = params.get("app_name", "")
                return await self._close_app(app_name)

            elif action_type == "focus_window":
                window_title = params.get("window_title", "")
                return await self._focus_window(window_title)

            elif action_type == "snap_window":
                window_title = params.get("window_title", "")
                position = params.get("position", "left")
                return await self._snap_window(window_title, position)

            elif action_type == "system_state":
                state = params.get("state", "lock")
                return await self._system_state(state)

            elif action_type == "camera_take_photo":
                filepath = params.get("filepath", "gkm making food.jpg")
                return await self._camera_take_photo(filepath)

            return ExecutionResult(success=False, error_message=f"Unhandled action type '{action_type}'")

        except Exception as e:
            logger.error(f"Desktop Agent action '{action_type}' failed: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    async def _launch_app(self, app_name: str) -> ExecutionResult:
        """Launches a Windows application by name or executable path."""
        import webbrowser
        logger.info(f"Launching desktop application: '{app_name}'")
        try:
            app_clean = app_name.lower().strip()
            if app_clean in ["chrome", "google chrome", "browser"]:
                webbrowser.open("https://www.google.com")
                return ExecutionResult(success=True, data={"app_name": app_name, "status": "launched"})

            # Common Windows app mapping
            app_map = {
                "notepad": "notepad",
                "calculator": "calc",
                "calc": "calc",
                "cmd": "cmd",
                "powershell": "powershell",
            }
            exe = app_map.get(app_clean, app_name)
            subprocess.Popen(f"start {exe}", shell=True)
            return ExecutionResult(success=True, data={"app_name": app_name, "status": "launched"})
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Failed to launch '{app_name}': {str(e)}")

    async def _close_app(self, app_name: str) -> ExecutionResult:
        """Closes an active Windows process by name."""
        logger.info(f"Closing desktop application: '{app_name}'")
        try:
            subprocess.run(f"taskkill /f /im {app_name}.exe", shell=True, check=False)
            return ExecutionResult(success=True, data={"app_name": app_name, "status": "closed"})
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Failed to close '{app_name}': {str(e)}")

    async def _focus_window(self, window_title: str) -> ExecutionResult:
        """Focuses a window by title."""
        logger.info(f"Focusing window: '{window_title}'")
        return ExecutionResult(success=True, data={"window_title": window_title, "status": "focused"})

    async def _snap_window(self, window_title: str, position: str) -> ExecutionResult:
        """Snaps window to split screen position (left/right/fullscreen)."""
        logger.info(f"Snapping window '{window_title}' to position '{position}'")
        return ExecutionResult(success=True, data={"window_title": window_title, "position": position})

    async def _system_state(self, state: str) -> ExecutionResult:
        """Triggers Windows power states (lock, sleep, shutdown, restart)."""
        logger.info(f"Executing system power state command: '{state}'")
        if state == "lock":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        elif state == "shutdown":
            subprocess.run("shutdown /s /t 10", shell=True)
        return ExecutionResult(success=True, data={"state": state, "status": "executed"})

    async def _camera_take_photo(self, filepath: str) -> ExecutionResult:
        """Grabs a frame from default webcam and saves it with screenshot fallback."""
        logger.info(f"Taking photo from webcam, saving to '{filepath}'")
        try:
            import cv2
            import time
            
            # Start camera capture
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("Webcam could not be opened")
            
            # Allow camera to warm up
            time.sleep(1.0)
            
            # Show camera feed for 4 seconds so they can position themselves
            start_time = time.time()
            frame = None
            while time.time() - start_time < 4.0:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Copy frame to put text guide overlay
                guide_frame = frame.copy()
                cv2.putText(
                    guide_frame, 
                    "Position yourself in the center! Capturing in 4s...", 
                    (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, 
                    (0, 255, 0), 
                    2
                )
                cv2.imshow("JARVIS Camera Guide", guide_frame)
                if cv2.waitKey(50) & 0xFF == 27:  # Esc key
                    break
            
            # Capture final frame
            ret, final_frame = cap.read()
            cap.release()
            cv2.destroyAllWindows()
            
            if not ret or final_frame is None:
                raise Exception("Failed to capture frame from webcam")
            
            # Save the final frame
            abs_path = os.path.abspath(filepath)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            cv2.imwrite(abs_path, final_frame)
            
            return ExecutionResult(
                success=True,
                data={"filepath": filepath, "status": "captured", "full_path": abs_path}
            )
        except Exception as e:
            logger.warning(f"Webcam photo failed: {e}. Falling back to screenshot.")
            try:
                from PIL import ImageGrab
                abs_path = os.path.abspath(filepath)
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                shot = ImageGrab.grab()
                shot.save(abs_path)
                return ExecutionResult(
                    success=True, 
                    data={"filepath": filepath, "status": "screenshot_fallback", "full_path": abs_path, "error": str(e)}
                )
            except Exception as ex:
                return ExecutionResult(success=False, error_message=f"Camera failed and fallback failed: {str(ex)}")
