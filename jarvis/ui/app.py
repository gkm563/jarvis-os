"""
JARVIS OS Desktop GUI Interface.
Built with CustomTkinter for modern dark-mode aesthetic, DAG plan visualizer,
agent ecosystem monitor, human confirmation approval gate, and live voice/text controls.
"""

import sys
import os
import asyncio
import threading
import time
from typing import Optional

import customtkinter as ctk

# Register all agents before GUI starts
import jarvis.agents as agents_module
from jarvis.agents import agent_registry

from jarvis.brain.planner import TaskPlanner
from jarvis.orchestration.executor import ExecutionManager
from jarvis.core.models import Plan, Step, StepStatus, PlanStatus, AgentAction
from jarvis.security import sensitive_gate
from jarvis.utils.logger import get_logger

logger = get_logger("JarvisGUI")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class JarvisOSGUI(ctk.CTk):
    """
    Main Modern Desktop Operating Interface for JARVIS OS.
    """

    def __init__(self):
        super().__init__()

        self.title("JARVIS OS - Enterprise AI Desktop Operating Agent")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # Core Engines
        self.planner = TaskPlanner()
        self.executor = ExecutionManager()
        self.current_plan: Optional[Plan] = None
        self.loop = asyncio.new_event_loop()

        # Start Async Event Loop in Background Thread
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()

        # Build UI Layout
        self._create_sidebar()
        self._create_header()
        self._create_main_content()
        self._create_footer()

        logger.info("JARVIS OS Desktop GUI initialized")

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _create_sidebar(self):
        """Creates the left navigation sidebar with Agent status grid."""
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🤖 JARVIS OS",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#3B82F6",
        )
        logo_label.pack(padx=20, pady=(20, 10))

        subtitle = ctk.CTkLabel(
            self.sidebar,
            text="AI Desktop Operating Layer\nVersion 1.0.0 Enterprise",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
        )
        subtitle.pack(padx=20, pady=(0, 20))

        self.status_badge = ctk.CTkButton(
            self.sidebar,
            text="🟢 SYSTEM ONLINE",
            fg_color="#166534",
            hover_color="#15803D",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
        )
        self.status_badge.pack(padx=20, pady=(0, 20), fill="x")

        agent_count = len(agent_registry._agents)
        agent_label = ctk.CTkLabel(
            self.sidebar,
            text=f"SPECIALIZED AGENTS ({agent_count})",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        agent_label.pack(padx=20, pady=(10, 5), fill="x")

        self.agent_frame = ctk.CTkScrollableFrame(self.sidebar, height=350)
        self.agent_frame.pack(padx=15, pady=5, fill="both", expand=True)

        for name in agent_registry._agents.keys():
            card = ctk.CTkFrame(self.agent_frame, fg_color="#1E293B", corner_radius=6)
            card.pack(fill="x", padx=2, pady=3)
            lbl = ctk.CTkLabel(
                card,
                text=f"⚡ {name}",
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
            )
            lbl.pack(padx=8, pady=4, side="left")

    def _create_header(self):
        """Top Header section with quick action controls."""
        self.header = ctk.CTkFrame(self, height=60, fg_color="#0F172A", corner_radius=0)
        self.header.pack(side="top", fill="x", padx=0, pady=0)

        title = ctk.CTkLabel(
            self.header,
            text="JARVIS Command Center",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(side="left", padx=20, pady=15)

        self.voice_btn = ctk.CTkButton(
            self.header,
            text="🎙️ Voice Input (Hey Jarvis)",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            width=180,
            command=self._on_voice_click,
        )
        self.voice_btn.pack(side="right", padx=20, pady=15)

    def _create_main_content(self):
        """Main workspace containing Natural Language Prompt Box, Plan Visualizer, and Execution Logs."""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. Natural Language Instruction Input Bar
        input_frame = ctk.CTkFrame(self.main_container, fg_color="#1E293B", corner_radius=10)
        input_frame.pack(fill="x", padx=0, pady=(0, 15))

        prompt_label = ctk.CTkLabel(
            input_frame,
            text="Ask JARVIS to execute any task on Windows:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        prompt_label.pack(anchor="w", padx=15, pady=(10, 5))

        input_box_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        input_box_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.prompt_entry = ctk.CTkEntry(
            input_box_frame,
            placeholder_text="e.g. Open Chrome, search AKTU results, download marksheet, and organize Downloads folder...",
            font=ctk.CTkFont(size=13),
            height=42,
        )
        self.prompt_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.prompt_entry.bind("<Return>", lambda e: self._on_execute_click())

        self.exec_btn = ctk.CTkButton(
            input_box_frame,
            text="🚀 Run Workflow",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            width=140,
            command=self._on_execute_click,
        )
        self.exec_btn.pack(side="right")

        # 2. Plan Visualizer and Execution Log Tabs
        self.tabview = ctk.CTkTabview(self.main_container, height=380)
        self.tabview.pack(fill="both", expand=True)

        self.tab_dag = self.tabview.add("📊 Multi-Agent Plan DAG")
        self.tab_logs = self.tabview.add("📜 System Audit Logs")

        # DAG Visualizer Frame
        self.dag_scroll = ctk.CTkScrollableFrame(self.tab_dag, fg_color="#0F172A")
        self.dag_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Log Output Box
        self.log_text = ctk.CTkTextbox(self.tab_logs, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self._append_log("JARVIS OS Kernel initialized. Ready for user commands.")
        self._append_log(f"Registered {len(agent_registry._agents)} domain agents.")

    def _create_footer(self):
        """Footer bar displaying operational security policy."""
        self.footer = ctk.CTkFrame(self, height=30, fg_color="#0F172A", corner_radius=0)
        self.footer.pack(side="bottom", fill="x")

        lbl = ctk.CTkLabel(
            self.footer,
            text="🔒 Security Mode: Zero-Trust Vault Active | Human Confirmation: Mandatory for Sensitive Actions",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
        )
        lbl.pack(side="left", padx=20, pady=5)

    def _append_log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")

    def _on_voice_click(self):
        """Triggers voice input simulation."""
        self._append_log("🎙️ Voice input triggered...")
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak("Yes, I am listening. Please type your command.")
        except Exception:
            pass
        self.prompt_entry.delete(0, "end")
        self.prompt_entry.insert(0, "Open Chrome and search AKTU results 2026")
        self.prompt_entry.focus()

    def _on_execute_click(self):
        user_prompt = self.prompt_entry.get().strip()
        if not user_prompt:
            return

        self._append_log(f"📝 Received instruction: '{user_prompt}'")
        self.exec_btn.configure(state="disabled", text="⏳ Planning...")

        # Clear DAG step display
        for widget in self.dag_scroll.winfo_children():
            widget.destroy()

        # Submit task planning to async loop
        asyncio.run_coroutine_threadsafe(self._process_plan_async(user_prompt), self.loop)

    async def _process_plan_async(self, goal: str):
        try:
            self.after(0, lambda: self._append_log("🧠 AI Planner decomposing goal into tasks..."))
            plan = await self.planner.create_plan(goal)
            self.current_plan = plan

            self.after(0, self._render_plan_steps, plan)
            self.after(0, lambda: self._append_log(f"✅ DAG Plan generated: {len(plan.steps)} step(s)"))

            # Execute Plan
            self.after(0, lambda: self._append_log("⚙️ Executing plan steps..."))
            await self.executor.execute_plan(plan)
            self.after(0, self._on_plan_completed, plan)

        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}")
            self.after(0, lambda: self._append_log(f"❌ ERROR: {str(e)}"))
            self.after(0, lambda: self.exec_btn.configure(state="normal", text="🚀 Run Workflow"))

    def _render_plan_steps(self, plan: Plan):
        for idx, step in enumerate(plan.steps, 1):
            step_card = ctk.CTkFrame(self.dag_scroll, fg_color="#1E293B", corner_radius=8)
            step_card.pack(fill="x", padx=10, pady=6)

            header = ctk.CTkFrame(step_card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(8, 4))

            title = ctk.CTkLabel(
                header,
                text=f"Step {idx}: {step.description}",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            )
            title.pack(side="left")

            is_sensitive = getattr(step.action, "is_sensitive", False)
            status_color = "#EF4444" if is_sensitive else "#3B82F6"

            badge = ctk.CTkLabel(
                header,
                text=f"Agent: {step.action.agent_name} | {step.action.action_type.upper()}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=status_color,
            )
            badge.pack(side="right")

            if is_sensitive:
                token = sensitive_gate.create_confirmation_request(step)
                self.after(0, lambda s=step, t=token: self._show_approval_dialog(s, t))

    def _show_approval_dialog(self, step: Step, token: str):
        """Displays human confirmation dialog for sensitive actions."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Human Confirmation Required")
        dialog.geometry("480x240")
        dialog.attributes("-topmost", True)

        lbl = ctk.CTkLabel(
            dialog,
            text="⚠️ SENSITIVE ACTION SECURITY GATE",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#EF4444",
        )
        lbl.pack(pady=(20, 10))

        msg = ctk.CTkLabel(
            dialog,
            text=f"Agent '{step.action.agent_name}' requests permission for:\n\n'{step.description}'",
            font=ctk.CTkFont(size=13),
            wraplength=420,
        )
        msg.pack(pady=10)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)

        def approve():
            sensitive_gate.confirm_action(token)
            self._append_log(f"✅ APPROVED sensitive token for step '{step.step_id}'")
            dialog.destroy()

        def reject():
            dialog.destroy()
            self._append_log(f"🚫 REJECTED sensitive action for step '{step.step_id}'")

        ctk.CTkButton(btn_frame, text="✅ Approve & Execute", fg_color="#166534", hover_color="#15803D", command=approve).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Deny Action", fg_color="#991B1B", hover_color="#7F1D1D", command=reject).pack(side="right", padx=10)

    def _on_plan_completed(self, plan: Plan):
        self.exec_btn.configure(state="normal", text="🚀 Run Workflow")
        status = plan.status.value.upper()
        self._append_log(f"🏁 Plan completed with status: {status}")
        # Speak result aloud
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(f"Task completed. Status: {status}")
        except Exception:
            pass


def launch_gui():
    app = JarvisOSGUI()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
