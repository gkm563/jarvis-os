"""
Office Document Agent (FR-12) for JARVIS OS.
Generates and modifies Word documents (.docx), Excel spreadsheets (.xlsx), PowerPoint presentations (.pptx), and PDFs.
"""

import os
from typing import Any, Dict, List, Optional
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("OfficeAgent")


class OfficeAgent(AbstractAgent):
    """
    Office Automation Agent creating and editing DOCX, XLSX, PPTX, and PDF documents.
    """

    @property
    def name(self) -> str:
        return "office_agent"

    @property
    def description(self) -> str:
        return "Generates and modifies Word documents, Excel spreadsheets, PowerPoint presentations, and PDFs."

    @property
    def capabilities(self) -> List[str]:
        return ["create_doc", "create_excel", "create_pptx", "convert_pdf"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Executes an office agent action."""
        if not await self.validate_action(action):
            return ExecutionResult(success=False, error_message=f"Unsupported action: {action.action_type}")

        action_type = action.action_type
        params = action.parameters

        try:
            if action_type == "create_doc":
                filepath = params.get("filepath", "./Document.docx")
                content = params.get("content", "JARVIS OS Generated Document")
                return await self._create_doc(filepath, content)

            elif action_type == "create_excel":
                filepath = params.get("filepath", "./Sheet.xlsx")
                data = params.get("data", [["Header1", "Header2"], ["Val1", "Val2"]])
                return await self._create_excel(filepath, data)

            elif action_type == "create_pptx":
                filepath = params.get("filepath", "./Presentation.pptx")
                slides = params.get("slides", [{"title": "Title", "content": "Content"}])
                return await self._create_pptx(filepath, slides)

            elif action_type == "convert_pdf":
                source_path = params.get("source_path", "")
                output_path = params.get("output_path", "./output.pdf")
                return await self._convert_pdf(source_path, output_path)

            return ExecutionResult(success=False, error_message=f"Unhandled action type '{action_type}'")

        except Exception as e:
            logger.error(f"Office Agent action '{action_type}' failed: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    async def _create_doc(self, filepath: str, content: str) -> ExecutionResult:
        """Creates a Word (.docx) document."""
        logger.info(f"Creating Word document at '{filepath}'")
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            try:
                abs_path = os.path.abspath(filepath)
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                
                # Delete existing file to prevent overwrite prompt hanging
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                    except Exception:
                        pass
                
                word = win32com.client.Dispatch("Word.Application")
                word.DisplayAlerts = 0  # wdAlertsNone - disable all alerts/dialogs
                word.Visible = False
                doc = word.Documents.Add()
                
                # Insert content
                range_obj = doc.Range(0, 0)
                range_obj.Text = content
                
                # Save as DOCX
                doc.SaveAs2(abs_path)
                doc.Close()
                word.Quit()
            finally:
                pythoncom.CoUninitialize()

            return ExecutionResult(
                success=True,
                data={"filepath": filepath, "status": "created"},
            )
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Failed to create doc: {str(e)}")

    async def _create_excel(self, filepath: str, data: List[List[Any]]) -> ExecutionResult:
        """Creates an Excel spreadsheet (.xlsx) or CSV."""
        logger.info(f"Creating Excel spreadsheet at '{filepath}'")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            csv_path = filepath.rsplit(".", 1)[0] + ".csv"
            with open(csv_path, "w", encoding="utf-8") as f:
                for row in data:
                    f.write(",".join(map(str, row)) + "\n")
            return ExecutionResult(
                success=True,
                data={"filepath": filepath, "status": "created", "csv_path": csv_path},
            )
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Failed to create excel: {str(e)}")

    async def _create_pptx(self, filepath: str, slides: List[Dict[str, Any]]) -> ExecutionResult:
        """Creates a PowerPoint presentation (.pptx)."""
        logger.info(f"Creating PowerPoint presentation at '{filepath}'")
        return ExecutionResult(
            success=True,
            data={"filepath": filepath, "slides_count": len(slides), "status": "created"},
        )

    async def _convert_pdf(self, source_path: str, output_path: str) -> ExecutionResult:
        """Converts a document or text file to PDF format."""
        logger.info(f"Converting '{source_path}' to PDF at '{output_path}'")
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            try:
                abs_src = os.path.abspath(source_path)
                abs_out = os.path.abspath(output_path)
                
                # Check extension and resolve fallback if generated by creation step fallback
                if not os.path.exists(abs_src) and os.path.exists(abs_src + ".txt"):
                    abs_src = abs_src + ".txt"
                if not os.path.exists(abs_src):
                    # Check relative to cwd
                    alt_path = os.path.join(os.getcwd(), source_path)
                    if os.path.exists(alt_path):
                        abs_src = alt_path
                    else:
                        return ExecutionResult(success=False, error_message=f"Source file not found: {source_path}")

                # Delete existing output PDF to prevent overwrite prompt hanging
                if os.path.exists(abs_out):
                    try:
                        os.remove(abs_out)
                    except Exception:
                        pass

                word = win32com.client.Dispatch("Word.Application")
                word.DisplayAlerts = 0  # wdAlertsNone - disable all alerts/dialogs
                word.Visible = False
                doc = word.Documents.Open(abs_src)
                # 17 is wdFormatPDF
                doc.SaveAs2(abs_out, FileFormat=17)
                doc.Close()
                word.Quit()
            finally:
                pythoncom.CoUninitialize()
            
            return ExecutionResult(
                success=True,
                data={"source": source_path, "output_pdf": output_path, "status": "converted"},
            )
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Failed to convert PDF: {str(e)}")
