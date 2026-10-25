"""Built-in tools deliberately avoid unrestricted shell execution."""

from __future__ import annotations

import ast
import csv
import json
import operator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


class CalculatorTool:
    tool_id = "calculator"
    description = "Evaluate a bounded arithmetic expression."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        expression = str(payload.get("expression", ""))
        if len(expression) > 200:
            raise ValueError("expression too long")
        tree = ast.parse(expression, mode="eval")
        return {"value": _safe_eval(tree.body)}


def _safe_eval(node: ast.AST) -> float | int:
    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in operations:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("exponent exceeds limit")
        return operations[type(node.op)](left, right)
    raise ValueError("only bounded arithmetic is allowed")


class FileReaderTool:
    tool_id = "file_reader"
    description = "Read a text file under an explicitly configured root."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", ""))).resolve()
        root = Path(str(payload.get("root", Path.cwd()))).resolve()
        if root not in path.parents and path != root:
            raise ValueError("path is outside the allowed root")
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("file is unavailable or exceeds the limit")
        return {"text": path.read_text(encoding="utf-8", errors="replace"), "name": path.name}


class JsonReaderTool:
    tool_id = "json_reader"
    description = "Parse a JSON file under an explicitly configured root."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = FileReaderTool().execute(payload)
        return {"value": json.loads(result["text"]), "name": result["name"]}


class CsvAnalyzerTool:
    tool_id = "csv_analyzer"
    description = "Summarize CSV columns and row counts."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = FileReaderTool().execute(payload)
        rows = list(csv.DictReader(result["text"].splitlines()))
        return {"name": result["name"], "rows": len(rows), "columns": list(rows[0]) if rows else []}


class PdfTextExtractorTool:
    tool_id = "pdf_text_extractor"
    description = "Extract text from a PDF under an explicitly configured root."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", ""))).resolve()
        root = Path(str(payload.get("root", Path.cwd()))).resolve()
        if root not in path.parents or path.suffix.lower() != ".pdf":
            raise ValueError("PDF path is outside the allowed root or has the wrong type")
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("install the documents extra for PDF extraction") from exc
        reader = PdfReader(str(path))
        return {
            "text": "\n".join(page.extract_text() or "" for page in reader.pages),
            "pages": len(reader.pages),
        }


class DocxTextExtractorTool:
    tool_id = "docx_text_extractor"
    description = "Extract paragraph text from a DOCX under an explicitly configured root."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", ""))).resolve()
        root = Path(str(payload.get("root", Path.cwd()))).resolve()
        if root not in path.parents or path.suffix.lower() != ".docx":
            raise ValueError("DOCX path is outside the allowed root or has the wrong type")
        try:
            from docx import Document  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("install the documents extra for DOCX extraction") from exc
        document = Document(str(path))
        return {"text": "\n".join(paragraph.text for paragraph in document.paragraphs)}


class SpreadsheetAnalyzerTool:
    tool_id = "spreadsheet_analyzer"
    description = "Summarize XLSX sheets and dimensions under an explicitly configured root."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", ""))).resolve()
        root = Path(str(payload.get("root", Path.cwd()))).resolve()
        if root not in path.parents or path.suffix.lower() not in {".xlsx", ".xlsm"}:
            raise ValueError("spreadsheet path is outside the allowed root or has the wrong type")
        try:
            from openpyxl import load_workbook  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ValueError("install openpyxl for spreadsheet analysis") from exc
        workbook = load_workbook(path, read_only=True, data_only=True)
        return {
            "sheets": [
                {"name": sheet.title, "rows": sheet.max_row, "columns": sheet.max_column}
                for sheet in workbook.worksheets
            ]
        }


class SafeHttpFetchTool:
    tool_id = "safe_http_fetch"
    description = "Fetch an allowlisted HTTPS URL with bounded response size."

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = str(payload.get("url", ""))
        allowed = {str(item).lower() for item in payload.get("allowed_domains", [])}
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.hostname.lower() not in allowed
        ):
            raise ValueError("URL is not HTTPS or not allowlisted")
        response = httpx.get(url, timeout=10, follow_redirects=False)
        response.raise_for_status()
        return {"status_code": response.status_code, "text": response.text[:100_000]}
