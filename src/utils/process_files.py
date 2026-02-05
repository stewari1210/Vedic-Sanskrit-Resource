from typing import List, Dict, Any
import os

# import pymupdf4llm
import json
import fitz

from pydantic import BaseModel, Field
from helper import logger
from utils.file_ops import save_file

from settings import Settings

from pdf_text_extractor.src import PDFTextExtractor, ExtractionMode


class Metadata(BaseModel):
    title: str = Field(default="")
    author: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    subject: str = Field(default="")
    doi: str = Field(default="")
    year: str = Field(default="")
    month: str = Field(default="")
    keywords: list[str] = Field(default_factory=list)
    summary: str = Field(default="")


def _create_pdf_extractor():
    """
    Create PDF extractor with appropriate extraction mode.
    Falls back to simpler modes if OCR dependencies are not available.
    """
    try:
        # Try OCR mode for scanned PDFs first
        logger.info("Initializing PDF extractor with OCR_UNSTRUCTURED mode")
        return PDFTextExtractor(
            ExtractionMode.OCR_UNSTRUCTURED, 
            print_page_number=True, 
            remove_header_footer=False
        )
    except ImportError as e:
        if "ocr_unstructured" in str(e):
            logger.warning("OCR dependencies not available, falling back to TABLE_IMAGE_LINKS mode")
            try:
                return PDFTextExtractor(
                    ExtractionMode.TABLE_IMAGE_LINKS,
                    print_page_number=True,
                    remove_header_footer=False
                )
            except ImportError:
                logger.warning("TABLE_IMAGE_LINKS mode also failed, falling back to BASIC mode")
                return PDFTextExtractor(
                    ExtractionMode.BASIC,
                    print_page_number=True,
                    remove_header_footer=False
                )
        raise

# Initialize extractor with fallback handling
extractor = _create_pdf_extractor()


def process_uploaded_pdfs(
    file_paths: List[str], extract_metadata: bool = False
):  # -> List[Document]:
    """
    Process uploaded PDFs and TXT files.
    - PDFs: Extracts text/markdown using PDF extractor (with fallback to PyMuPDF)
    - TXT files: Converts to markdown format directly
    Saves as markdown along with metadata.
    """
    all_docs = []
    for file_path in file_paths:
        filename = os.path.basename(file_path).split(".")[0]
        file_ext = os.path.splitext(file_path)[1].lower()
        folder = os.sep.join(file_path.split(os.sep)[:-1])
        text_folder = os.path.join(folder, filename)
        image_folder = os.path.join(text_folder, "images")
        os.makedirs(text_folder, exist_ok=True)

        # Handle different file types
        if file_ext == '.txt':
            logger.info(f"Processing TXT file: {filename}")
            # Read text file and convert to markdown format
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()

            # Simple conversion: add page markers if needed
            # Split by form feed or keep as is
            if '\f' in text_content:
                # Split by form feed (page break)
                pages = text_content.split('\f')
                markdown = '\n\n'.join([f"## Page {i+1}\n\n{page.strip()}"
                                       for i, page in enumerate(pages) if page.strip()])
            else:
                # No page breaks, use as single document
                markdown = text_content

            logger.info(f"TXT file converted to markdown: {len(markdown)} chars")

        elif file_ext == '.pdf':
            logger.info(f"Processing PDF file: {filename}")
            try:
                # Try primary extractor (with OCR fallback)
                markdown = extractor.extract(file_path, image_folder=image_folder)
                logger.info(f"PDF extracted to markdown using pdf_text_extractor: {len(markdown)} chars")
            except Exception as e:
                logger.warning(f"pdf_text_extractor failed: {e}. Falling back to PyMuPDF...")
                try:
                    # Fallback to PyMuPDF for simple text extraction
                    markdown = _extract_pdf_with_pymupdf(file_path)
                    logger.info(f"PDF extracted to markdown using PyMuPDF: {len(markdown)} chars")
                except Exception as e2:
                    logger.error(f"Both extraction methods failed: {e2}")
                    continue
        else:
            logger.warning(f"Unsupported file type: {file_ext} for {filename}")
            continue

        # Save markdown
        save_file(os.path.join(text_folder, filename + ".md"), markdown)

        # Extract metadata if requested
        if extract_metadata:
            get_metadata(file_path, markdown)

        # Remove original file after processing
        os.remove(file_path)

    logger.info(f"Successfully processed {len(file_paths)} input file(s)")
    return all_docs


def _extract_pdf_with_pymupdf(file_path: str) -> str:
    """
    Fallback PDF extraction using PyMuPDF (fitz).
    Simple text extraction without OCR.
    """
    markdown_parts = []
    try:
        with fitz.open(file_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")  # Explicitly get text format
                if isinstance(text, str) and text.strip():
                    markdown_parts.append(f"## Page {page_num + 1}\n\n{text}")
        return "\n\n".join(markdown_parts) if markdown_parts else ""
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        raise


def get_metadata(file_path: str, markdown: str):
    filename = os.path.basename(file_path).split(".")[0]
    folder = os.sep.join(file_path.split(os.sep)[:-1])
    text_folder = os.path.join(folder, filename)
    with fitz.open(file_path) as doc:
        metadata = doc.metadata
        metadata["pages"] = doc.page_count
        metadata["toc"] = doc.get_toc()
    metadata["filename"] = filename
    with open(
        os.path.join("src", "utils", "metadata_prompt.txt"), "r", encoding="utf-8"
    ) as f:
        prompt_template = f.read().strip()

    prompt = prompt_template.format(text=markdown[:9000])
    response = run_llm(prompt)

    def extract_first_json(s: str) -> str | None:
        """Extract the first balanced JSON object from a string.

        Returns the substring including the outer braces, or None if not found.
        """
        if not s or "{" not in s:
            return None
        start = s.find("{")
        brace_count = 0
        for i in range(start, len(s)):
            ch = s[i]
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    return s[start : i + 1]
        return None

    # Try to validate the full response first. If the LLM returned extra text
    # around the JSON (common), extract the JSON substring and try again.
    try:
        metadata_obj = Metadata.model_validate_json(response)
    except Exception as e:
        logger.debug("Metadata JSON validation failed: %s. Attempting to extract JSON substring.", e)
        json_sub = extract_first_json(response)
        if json_sub:
            try:
                metadata_obj = Metadata.model_validate_json(json_sub)
            except Exception:
                logger.debug("Failed to parse extracted JSON from LLM response. Falling back to empty metadata.")
                metadata_obj = None
        else:
            logger.debug("No JSON object could be extracted from LLM response. Using basic metadata only.")
            metadata_obj = None

    if metadata_obj:
        llm_metadata = json.loads(metadata_obj.model_dump_json(indent=4, exclude_none=True))
    else:
        llm_metadata = {}

    doc_metadata = merge_metadata(llm_metadata, metadata)
    doc_metadata = json.dumps(doc_metadata, indent=4)
    save_file(os.path.join(text_folder, filename + "_metadata.json"), doc_metadata)


def run_llm(prompt):
    messages = [("system", prompt)]
    # Use Settings.invoke_llm for provider compatibility (Gemini expects plain string)
    response = Settings.invoke_llm(Settings.get_llm(), messages)

    return response.content


def merge_metadata(
    existing_metadata: Dict[str, Any], new_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merges new metadata into existing metadata.
    """

    def _merge_list_and_str(existing, new):
        if isinstance(existing, list) and isinstance(new, str):
            existing.append(new)
            return existing
        elif isinstance(existing, str) and isinstance(new, list):
            return list(set(existing.split(",")).union(set(new)))
        return existing

    for key, new_value in new_metadata.items():
        if key not in existing_metadata:
            existing_metadata[key] = new_value
            continue
        existing_value = existing_metadata[key]
        if existing_value is None or existing_value == "":
            existing_metadata[key] = new_value
            continue

        merged = _merge_list_and_str(existing_value, new_value)
        if merged != existing_value:
            existing_metadata[key] = merged

    return existing_metadata
