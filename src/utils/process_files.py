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


extractor = PDFTextExtractor(
    ExtractionMode.TABLE_IMAGE_LINKS, print_page_number=True, remove_header_footer=False
)


def process_uploaded_pdfs(
    file_paths: List[str], extract_metadata: bool = False
):  # -> List[Document]:
    """
    Process the uploaded PDFs. Extracts Markdown text from PDFs and saves it along with metadata
    """
    all_docs = []
    for file_path in file_paths:
        filename = os.path.basename(file_path).split(".")[0]
        folder = os.sep.join(file_path.split(os.sep)[:-1])
        text_folder = os.path.join(folder, filename)
        image_folder = os.path.join(text_folder, "images")
        os.makedirs(text_folder, exist_ok=True)
        # os.makedirs(image_folder, exist_ok=True)

        # markdown = pymupdf4llm.to_markdown(
        #     file_path,
        #     write_images=True,
        #     table_strategy="lines_strict",
        #     image_path=image_folder,  # Folder where images will be saved
        #     image_format="png",
        # )

        markdown = extractor.extract(file_path, image_folder=image_folder)

        # all_docs.extend(mark)
        save_file(os.path.join(text_folder, filename + ".md"), markdown)
        if extract_metadata:
            get_metadata(file_path, markdown)
        os.remove(file_path)
    logger.info("Successfully processed input PDFs")
    return all_docs


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
    response = Settings.llm.invoke(messages)

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
