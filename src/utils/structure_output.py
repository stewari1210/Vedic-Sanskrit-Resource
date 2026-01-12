from pydantic import BaseModel, Field
from typing import List, Optional


# Define the models for the initial LLM output
class Citation(BaseModel):
    """
    A citation for a specific piece of information.
    """

    document_name: str = Field(
        ..., description="The name of the document where the information was found."
    )
    document_number: int = Field(..., description="The number of the document.")
    page_numbers: List[int] = Field(
        ...,
        description="A list of page numbers from the document that contain the information.",
    )


class InitialRAGResponse(BaseModel):
    """
    A structured response to a user's question, including the answer and citations.
    """

    answer: str = Field(
        ..., description="The concise and accurate final answer to the user's question."
    )
    citations: List[Citation] = Field(
        ...,
        description="A list of citations from the documents used to formulate the answer.",
    )


# Simplified response for Ollama (no citations)
class SimpleRAGResponse(BaseModel):
    """
    A simplified structured response without citations (for Ollama compatibility).
    """

    answer: str = Field(
        ..., description="The concise and accurate final answer to the user's question."
    )


# Define the models for the evaluator's output
class ConfidenceScore(BaseModel):
    """
    A structured output for the confidence score evaluation.
    """

    confidence_score: int = Field(
        ...,
        description="A confidence score from 0 to 100, representing how well the AI's answer is supported by the provided documents.",
    )
    reasoning: str = Field(
        ...,
        description="A brief explanation of the reasoning behind the confidence score, citing specific evidence or lack thereof in the documents.",
    )


class RAGResponse(BaseModel):
    """
    A structured response to a user's question, including the answer and citations.
    """

    answer: str = Field(
        ..., description="The concise and accurate final answer to the user's question."
    )
    citations: List[Citation] = Field(
        ...,
        description="A list of citations from the documents used to formulate the answer.",
    )
    # This field now holds the nested model
    confidence: Optional[ConfidenceScore] = Field(
        None, description="The evaluation of the answer's quality, if available."
    )
