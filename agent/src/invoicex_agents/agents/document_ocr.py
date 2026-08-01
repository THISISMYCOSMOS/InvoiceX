"""Free local OCR primitives used to verify image-only document evidence."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Protocol

import pypdfium2 as pdfium
from PIL import Image

from invoicex_agents.clients.base import MediaDocument

DEFAULT_OCR_LANGUAGES = ("kor", "eng")
DEFAULT_OCR_TIMEOUT_SECONDS = 30.0
DEFAULT_OCR_MIN_CONFIDENCE = 70.0
PDF_RENDER_DPI = 300


class OcrError(RuntimeError):
    """Raised when a configured local OCR engine cannot process a page safely."""


@dataclass(frozen=True, slots=True)
class OcrWord:
    """One OCR word with its page location and confidence."""

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int
    block: int
    paragraph: int
    line: int


@dataclass(frozen=True, slots=True)
class OcrLine:
    """Words grouped into one OCR line with a union bounding box."""

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class OcrPage:
    """Locally recognized text and geometry for one page."""

    words: tuple[OcrWord, ...]
    lines: tuple[OcrLine, ...]

    @property
    def text(self) -> str:
        """Return OCR lines in reading order."""

        return "\n".join(line.text for line in self.lines)


class OcrEngine(Protocol):
    """Interface for a local evidence OCR implementation."""

    min_confidence: float

    def extract_page(self, document: MediaDocument, page: int) -> OcrPage:
        """Recognize a one-based page from a supplied media document."""


def _positive_float(value: str | None, default: float, *, maximum: float) -> float:
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if 0 < parsed <= maximum else default


def _candidate_tesseract_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    configured = os.getenv("TESSERACT_CMD")
    if configured:
        paths.append(Path(configured))

    discovered = shutil.which("tesseract")
    if discovered:
        paths.append(Path(discovered))

    for environment_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        root = os.getenv(environment_name)
        if not root:
            continue
        base = Path(root)
        paths.extend(
            (
                base / "Tesseract-OCR" / "tesseract.exe",
                base / "Programs" / "Tesseract-OCR" / "tesseract.exe",
            )
        )

    workspace_local = Path.cwd() / ".data" / "tools" / "tesseract" / "tesseract.exe"
    paths.append(workspace_local)
    return tuple(dict.fromkeys(path.resolve() for path in paths))


def _available_languages(command: Path, tessdata_dir: Path | None) -> tuple[str, ...]:
    environment = os.environ.copy()
    if tessdata_dir is not None:
        environment["TESSDATA_PREFIX"] = str(tessdata_dir)
    try:
        completed = subprocess.run(
            [str(command), "--list-langs"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    lines = [line.strip() for line in completed.stdout.splitlines()]
    return tuple(line for line in lines if line and "available languages" not in line.casefold())


def _parse_languages(value: str | None) -> tuple[str, ...]:
    requested = (value or "+".join(DEFAULT_OCR_LANGUAGES)).replace(",", "+").split("+")
    return tuple(dict.fromkeys(item.strip() for item in requested if item.strip()))


def _render_page(document: MediaDocument, page: int) -> Image.Image:
    if document.mime_type == "application/pdf":
        pdf = None
        pdf_page = None
        bitmap = None
        try:
            pdf = pdfium.PdfDocument(document.data)
            if page < 1 or page > len(pdf):
                raise OcrError("OCR page exceeds the supplied PDF page count")
            pdf_page = pdf[page - 1]
            bitmap = pdf_page.render(scale=PDF_RENDER_DPI / 72)
            return bitmap.to_pil().convert("RGB")
        except OcrError:
            raise
        except Exception as exc:
            raise OcrError("PDF page could not be rendered for OCR") from exc
        finally:
            if bitmap is not None:
                bitmap.close()
            if pdf_page is not None:
                pdf_page.close()
            if pdf is not None:
                pdf.close()

    if page != 1:
        raise OcrError("image evidence can only reference page 1")
    try:
        with Image.open(BytesIO(document.data)) as image:
            return image.convert("RGB")
    except Exception as exc:
        raise OcrError("image document could not be decoded for OCR") from exc


def _parse_tsv(tsv: str) -> OcrPage:
    words: list[OcrWord] = []
    reader = csv.DictReader(StringIO(tsv), delimiter="\t")
    required_columns = {
        "level",
        "block_num",
        "par_num",
        "line_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    }
    if reader.fieldnames is None or not required_columns <= set(reader.fieldnames):
        raise OcrError("Tesseract returned an invalid TSV response")

    for row in reader:
        text = (row.get("text") or "").strip()
        if row.get("level") != "5" or not text:
            continue
        try:
            confidence = float(row["conf"])
            word = OcrWord(
                text=text,
                confidence=confidence,
                left=int(row["left"]),
                top=int(row["top"]),
                width=int(row["width"]),
                height=int(row["height"]),
                block=int(row["block_num"]),
                paragraph=int(row["par_num"]),
                line=int(row["line_num"]),
            )
        except (TypeError, ValueError) as exc:
            raise OcrError("Tesseract returned malformed word geometry") from exc
        if confidence >= 0:
            words.append(word)

    grouped: dict[tuple[int, int, int], list[OcrWord]] = defaultdict(list)
    for word in words:
        grouped[(word.block, word.paragraph, word.line)].append(word)

    lines: list[OcrLine] = []
    for line_words in grouped.values():
        ordered = sorted(line_words, key=lambda item: item.left)
        left = min(item.left for item in ordered)
        top = min(item.top for item in ordered)
        right = max(item.left + item.width for item in ordered)
        bottom = max(item.top + item.height for item in ordered)
        lines.append(
            OcrLine(
                text=" ".join(item.text for item in ordered),
                confidence=sum(item.confidence for item in ordered) / len(ordered),
                left=left,
                top=top,
                width=right - left,
                height=bottom - top,
            )
        )
    lines.sort(key=lambda item: (item.top, item.left))
    return OcrPage(words=tuple(words), lines=tuple(lines))


class TesseractOcrEngine:
    """Local Tesseract OCR invoked as a bounded subprocess."""

    def __init__(
        self,
        command: Path,
        *,
        languages: tuple[str, ...],
        tessdata_dir: Path | None = None,
        timeout_seconds: float = DEFAULT_OCR_TIMEOUT_SECONDS,
        min_confidence: float = DEFAULT_OCR_MIN_CONFIDENCE,
    ) -> None:
        if not languages:
            raise ValueError("at least one installed OCR language is required")
        self._command = command
        self._languages = languages
        self._tessdata_dir = tessdata_dir
        self._timeout_seconds = timeout_seconds
        self.min_confidence = min_confidence

    @classmethod
    def discover(cls) -> TesseractOcrEngine | None:
        """Return a configured local engine, or None when Tesseract is unavailable."""

        tessdata_value = os.getenv("TESSDATA_PREFIX")
        tessdata_dir = Path(tessdata_value).resolve() if tessdata_value else None
        requested = _parse_languages(os.getenv("OCR_LANGUAGES"))
        timeout_seconds = _positive_float(
            os.getenv("OCR_TIMEOUT_SECONDS"),
            DEFAULT_OCR_TIMEOUT_SECONDS,
            maximum=120,
        )
        min_confidence = _positive_float(
            os.getenv("OCR_MIN_CONFIDENCE"),
            DEFAULT_OCR_MIN_CONFIDENCE,
            maximum=100,
        )

        for command in _candidate_tesseract_paths():
            if not command.is_file():
                continue
            available = set(_available_languages(command, tessdata_dir))
            languages = tuple(language for language in requested if language in available)
            if languages:
                return cls(
                    command,
                    languages=languages,
                    tessdata_dir=tessdata_dir,
                    timeout_seconds=timeout_seconds,
                    min_confidence=min_confidence,
                )
        return None

    def extract_page(self, document: MediaDocument, page: int) -> OcrPage:
        """Render and OCR one evidence page without persisting source documents."""

        image = _render_page(document, page)
        environment: Mapping[str, str] = os.environ.copy()
        if self._tessdata_dir is not None:
            environment = dict(environment, TESSDATA_PREFIX=str(self._tessdata_dir))

        try:
            with tempfile.TemporaryDirectory(prefix="invoicex-ocr-") as temporary:
                image_path = Path(temporary) / "page.png"
                image.save(image_path, format="PNG")
                try:
                    completed = subprocess.run(
                        [
                            str(self._command),
                            str(image_path),
                            "stdout",
                            "-l",
                            "+".join(self._languages),
                            "--oem",
                            "1",
                            "--psm",
                            "3",
                            "tsv",
                        ],
                        capture_output=True,
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                        env=environment,
                        timeout=self._timeout_seconds,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise OcrError("local OCR exceeded its time limit") from exc
                except OSError as exc:
                    raise OcrError("local OCR could not be started") from exc
                if completed.returncode != 0:
                    raise OcrError("local OCR failed to recognize the evidence page")
                return _parse_tsv(completed.stdout)
        finally:
            image.close()
