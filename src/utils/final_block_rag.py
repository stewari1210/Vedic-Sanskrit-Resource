from typing import TypedDict, List, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import groq
import re
from settings import Settings
from helper import logger
from utils.prompts import (
    FOLLOW_UP,
    REPHRASE,
    GRAMMER,
    TOPIC_CHANGE,
    RAG_PROMPT,
    EVALUATION_PROMPT,
    REFINE_PROMPT,
)
from utils.structure_output import RAGResponse, ConfidenceScore, InitialRAGResponse
import json
from config import CHAT_MEMORY_WINDOW, TOPIC_CHANGE_WINDOW

llm = Settings.llm
evaluator_llm = Settings.evaluator_llm


class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """

    question: str
    enhanced_question: str
    chat_history: List[BaseMessage]
    documents: List[Document]
    answer: dict
    is_follow_up: bool
    reset_history: bool


def retrieve_and_rerank_node(state: GraphState, reranking_retriever):
    """
    Retrieves and reranks documents based on the enhanced question.
    """
    logger.info("---RETRIEVING & RERANKING DOCUMENTS---")
    enhanced_question = state.get("enhanced_question", state["question"])

    # Use the combined retriever with the reranker
    retrieved_docs = reranking_retriever.invoke(enhanced_question)

    # Log what was retrieved for debugging
    logger.info(f"Query: {enhanced_question}")
    logger.info(f"Retrieved {len(retrieved_docs)} documents")
    for i, doc in enumerate(retrieved_docs[:2]):  # Log first 2 docs
        preview = doc.page_content[:200].replace('\n', ' ')
        logger.info(f"Doc {i+1} preview: {preview}...")

    # Update the state with the retrieved documents
    return {"documents": retrieved_docs}


# --- Nodes with LLM calls ---


def check_follow_up_node(state: GraphState):
    """Checks if the user's question is a follow-up using an LLM."""
    logger.info("---CHECKING FOLLOW-UP---")
    question = state["question"]
    chat_history = state["chat_history"]

    short_chat_history = (
        chat_history[:CHAT_MEMORY_WINDOW]
        if len(chat_history) > CHAT_MEMORY_WINDOW
        else chat_history
    )
    # Define LLM chains for specific tasks
    follow_up_chain = (
        ChatPromptTemplate.from_template(FOLLOW_UP) | llm | StrOutputParser()
    )

    response = follow_up_chain.invoke(
        {"chat_history": short_chat_history, "question": question}
    )
    is_follow_up = response.strip().lower() == "yes"

    return {"is_follow_up": is_follow_up}


def process_follow_up_node(state: GraphState):
    """Processes a follow-up question, getting intent and checking for a topic change using LLMs."""
    logger.info("---PROCESSING FOLLOW-UP---")
    question = state["question"]
    chat_history = state["chat_history"]
    short_chat_history = (
        chat_history[:CHAT_MEMORY_WINDOW]
        if len(chat_history) > CHAT_MEMORY_WINDOW
        else chat_history
    )

    rephrase_chain = (
        ChatPromptTemplate.from_template(REPHRASE) | llm | StrOutputParser()
    )

    # Get the enhanced question by rephrasing with LLM
    enhanced_question = rephrase_chain.invoke(
        {"chat_history": short_chat_history, "question": question}
    )

    topic_change_chain = (
        ChatPromptTemplate.from_template(TOPIC_CHANGE) | llm | StrOutputParser()
    )
    # Check for a complete topic change with LLM
    topic_change_response = topic_change_chain.invoke(
        {"chat_history": short_chat_history, "question": question}
    )
    reset_history = topic_change_response.strip().lower() == "yes"

    return {"enhanced_question": enhanced_question, "reset_history": reset_history}


def correct_grammar_node(state: GraphState):
    """Corrects the grammar of a standalone question using an LLM."""
    logger.info("---CORRECTING GRAMMAR---")
    question = state["question"]

    grammar_chain = ChatPromptTemplate.from_template(GRAMMER) | llm | StrOutputParser()

    enhanced_question = grammar_chain.invoke({"question": question})

    return {"enhanced_question": enhanced_question}


def parse_failed_generation(error_message: str):
    """
    Parses a Groq API error message to extract the answer and citations
    from the 'failed_generation' field.
    """
    try:
        # Use a regular expression to find the 'failed_generation' field's content.
        # Look for the function call format: <function=...> {...}
        match = re.search(
            r"'failed_generation': '.*?<function=\w+>\s*(\{.+?\})\s*</function>'",
            error_message,
            re.DOTALL
        )

        if not match:
            # Try alternative format without function tags
            match = re.search(
                r"'failed_generation': '(.+?)'\}\}'?$", error_message, re.DOTALL
            )
            if match:
                json_str = match.group(1)
            else:
                logger.warning("Could not find failed_generation field in error")
                return "I could not generate a proper response. Please try again.", []
        else:
            json_str = match.group(1)

        # Clean up the JSON string
        json_str = json_str.replace("\\'", "'").replace('\\"', '"').strip()

        # Remove the function wrapper if present
        json_str = re.sub(r'<function=\w+>\s*', '', json_str)
        json_str = re.sub(r'\s*</function>', '', json_str)

        # Load the extracted string as a JSON object
        failed_generation_data = json.loads(json_str)

        # Extract the 'answer' and 'citations' fields
        answer = failed_generation_data.get("answer", "No answer found.")
        citations = failed_generation_data.get("citations", [])

        logger.info(f"Successfully parsed failed generation: {len(citations)} citations found")
        return answer, citations

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Error parsing failed generation data: {e}")
        return "Parsing error: Could not extract a valid answer.", []


def call_llm_node(state: GraphState):
    """
    Calls the main RAG LLM to get the final structured answer (without evaluation fields).
    """
    logger.info("---CALLING LLM FOR INITIAL ANSWER---")
    enhanced_question = state["enhanced_question"]
    documents = state["documents"]
    chat_history = state["chat_history"]
    short_chat_history = (
        chat_history[:CHAT_MEMORY_WINDOW]
        if len(chat_history) > CHAT_MEMORY_WINDOW
        else chat_history
    )

    inputs = {
        "question": enhanced_question,
        "documents": documents,
        "chat_history": short_chat_history,
    }

    # Bind to the simplified model
    rag_chain = ChatPromptTemplate.from_template(
        RAG_PROMPT
    ) | llm.with_structured_output(InitialRAGResponse)

    try:
        # Invoke the chain
        structured_response = rag_chain.invoke(inputs)

        # Return the Pydantic object directly
        # This will be stored in the state as a dictionary
        return {"answer": structured_response.model_dump()}

    except groq.BadRequestError as e:
        logger.error(f"Response does not conform to InitialRagResponse: {e}")
        try:
            # Convert error to string before parsing
            part_answer, citations = parse_failed_generation(str(e))
            logger.info(f"Extracted answer from failed generation: {part_answer[:100]}...")
            # Return a fallback response
            return {
                "answer": {
                    "answer": part_answer,
                    "citations": citations,
                }
            }
        except Exception as parse_error:
            logger.error(f"Failed to parse error message: {parse_error}")
            # General fallback
            return {
                "answer": {
                    "answer": "An unexpected error occurred. Please try again.",
                    "citations": [],
                }
            }
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        # General fallback
        return {
            "answer": {
                "answer": "An unexpected error occurred. Please try again.",
                "citations": [],
            }
        }


def parse_confidence_score_from_error(error_message: str):
    """
    Parses a Groq API error message to extract the confidence score
    from the 'failed_generation' field and convert it to an integer.

    Args:
        error_message: The full string of the Groq BadRequestError.

    Returns:
        The confidence score as an integer, or None if parsing fails.
    """
    try:
        # Step 1: Use a regular expression to find and extract the JSON string
        # The pattern looks for the 'failed_generation' key and captures the
        # content between single quotes. The re.DOTALL flag handles newlines.
        match = re.search(
            r"'failed_generation': '(.+?)'\}\}'$", error_message, re.DOTALL
        )
        if not match:
            print("Could not find 'failed_generation' in the error message.")
            return None

        # The extracted string still has escaped quotes.
        json_str = match.group(1)

        # Step 2: Clean the string by replacing escaped characters with proper ones
        # This is a critical step for json.loads()
        cleaned_str = json_str.replace("\\n", "").replace('\\"', '"').strip()

        # Step 3: Load the cleaned string as a JSON object (which is a list)
        data_list = json.loads(cleaned_str)

        # Step 4: Access the nested dictionary and extract the score
        if data_list and isinstance(data_list, list) and "parameters" in data_list[0]:
            parameters = data_list[0].get("parameters", {})
            confidence_score_str = parameters.get("confidence_score")
            reasoning = parameters.get("reasoning")
            confidence_score = -1
            # Step 5: Convert the string score to an integer
            if confidence_score_str is not None:
                confidence_score = int(confidence_score_str)

            return {"confidence_score": confidence_score, "reasoning": reasoning}

    except Exception as e:
        # Catch various parsing errors (e.g., malformed JSON, missing keys)
        logger.error(f"Failed to parse confidence score. Error: {e}")
        return {"confidence_score": -1, "reasoning": "Could not Evaluate."}


def evaluate_response_node(state: GraphState):
    """
    Evaluates the AI's response and provides a confidence score.
    """
    logger.info("---EVALUATING AI RESPONSE---")

    # The evaluation LLM chain
    # evaluator_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest")
    evaluator_chain = ChatPromptTemplate.from_template(
        EVALUATION_PROMPT
    ) | evaluator_llm.with_structured_output(ConfidenceScore)

    # Get the necessary state variables
    documents = state["documents"]
    chat_history = state["chat_history"]
    enhanced_question = state["enhanced_question"]
    short_chat_history = (
        chat_history[:CHAT_MEMORY_WINDOW]
        if len(chat_history) > CHAT_MEMORY_WINDOW
        else chat_history
    )
    answer_dict = state["answer"]

    try:
        # Invoke the evaluator chain
        # The AI answer is a dictionary, so we need to get the 'answer' field
        evaluation_result = evaluator_chain.invoke(
            {
                "documents": documents,
                "chat_history": short_chat_history,
                "question": enhanced_question,
                "answer": answer_dict.get("answer", "No answer provided."),
            }
        )
        evals = evaluation_result.model_dump()
        # confidence_score is now an int from the schema, no conversion needed
        answer_dict["confidence"] = evals
    except groq.BadRequestError as e:
        logger.info(f"Evaluation output not as expected {e}. using fallback")
        # Convert error to string before parsing
        conf_dict = parse_confidence_score_from_error(str(e))
        answer_dict["confidence"] = conf_dict

    # Add the evaluation result to the answer dictionary

    logger.info(f"Evaluation: {answer_dict['confidence']}%")

    # Return the updated answer dictionary, which LangGraph will
    # merge back into the state's "answer" key.
    return {"answer": answer_dict}


def refine_response_node(state: GraphState):
    """
    If evaluation results in less than 75% score then refine the output
    """

    # REFINE_PROMPT
    logger.info("---REFINING LLM ANSWER---")
    enhanced_question = state["enhanced_question"]
    documents = state["documents"]
    chat_history = state["chat_history"]
    short_chat_history = (
        chat_history[:CHAT_MEMORY_WINDOW]
        if len(chat_history) > CHAT_MEMORY_WINDOW
        else chat_history
    )

    answer_dict = state["answer"]
    suggested_improvements = answer_dict.get("confidence", {}).get("reasoning", "")
    inputs = {
        "question": enhanced_question,
        "documents": documents,
        "chat_history": short_chat_history,
        "answer": answer_dict.get("answer", "No answer provided."),
        "suggested_improvements": suggested_improvements,
    }

    refine_chain = ChatPromptTemplate.from_template(
        REFINE_PROMPT
    ) | llm.with_structured_output(RAGResponse)

    try:
        # The chain now returns a Pydantic object
        structured_response = refine_chain.invoke(inputs)

        # Return the Pydantic object directly
        return {"answer": structured_response.model_dump()}

    except groq.BadRequestError as e:
        logger.info(f"Response does not conform to RAGResponse: {e}. Falling back")
        # Convert error to string before parsing
        part_answer, citations = parse_failed_generation(str(e))
        return {
            "answer": part_answer,
            "citations": citations,
            "confidence": {
                "confidence_score": 50,
                "reasoning": "Could not evaluate. Partial Response",
            },
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        # General fallback
        return {
            "answer": {
                "answer": "An unexpected error occurred. Please try again.",
                "citations": [],
                "confidence": {"confidence_score": 0, "reasoning": "No Response"},
            }
        }


def route_to_refiner(state: GraphState) -> Literal["refine", "end"]:
    """
    Determines whether to refine the answer or end the graph.
    """
    answer_dict = state["answer"].get("confidence", {})
    confidence_score = answer_dict.get("confidence_score", None)
    if confidence_score is not None and confidence_score > -1 and confidence_score < 75:
        logger.info(f"Confidence is low {confidence_score}. Refining the answer.")
        return "refine"
    else:
        logger.info("Confidence is high enough. Ending the process.")
        return "end"


def update_chat_history_node(state: GraphState):
    """Updates the chat history with the new question and answer."""
    logger.info("---UPDATING CHAT HISTORY---")
    question = state["question"]
    answer = state["answer"]
    chat_history = state["chat_history"]
    reset_history = state["reset_history"]
    short_chat_history = (
        chat_history[:CHAT_MEMORY_WINDOW]
        if len(chat_history) > CHAT_MEMORY_WINDOW
        else chat_history
    )
    if reset_history and len(short_chat_history) > TOPIC_CHANGE_WINDOW:
        logger.info("---RESETTING HISTORY DUE TO TOPIC CHANGE---")
        updated_history = []
    else:
        updated_history = short_chat_history.copy()

    updated_history.append(HumanMessage(content=question))
    updated_history.append(AIMessage(content=json.dumps(answer, indent=2)))

    return {"chat_history": updated_history}


# --- Building the Graph (no changes needed here) ---
def create_langgraph_app(retriever):
    workflow = StateGraph(GraphState)
    workflow.add_node("check_follow_up", check_follow_up_node)
    workflow.add_node("process_follow_up", process_follow_up_node)
    workflow.add_node("correct_grammar", correct_grammar_node)
    workflow.add_node(
        "retrieve_documents", lambda state: retrieve_and_rerank_node(state, retriever)
    )
    workflow.add_node("call_llm", call_llm_node)
    workflow.add_node("evaluator", evaluate_response_node)
    workflow.add_node("refiner", refine_response_node)
    workflow.add_node("update_chat_history", update_chat_history_node)

    workflow.set_entry_point("check_follow_up")

    workflow.add_conditional_edges(
        "check_follow_up",
        lambda state: "follow_up" if state["is_follow_up"] else "standalone",
        {
            "follow_up": "process_follow_up",
            "standalone": "correct_grammar",
        },
    )

    workflow.add_edge("process_follow_up", "retrieve_documents")
    workflow.add_edge("correct_grammar", "retrieve_documents")
    workflow.add_edge("retrieve_documents", "call_llm")
    workflow.add_edge("call_llm", "evaluator")
    # Add the conditional edge from the evaluator
    workflow.add_conditional_edges(
        "evaluator",
        route_to_refiner,
        {"refine": "refiner", "end": "update_chat_history"},
    )

    # The refiner node is then again sent to evaluator to recompute the confidence.
    workflow.add_edge("refiner", "evaluator")
    workflow.add_edge("update_chat_history", END)

    app = workflow.compile()

    return app


def run_rag_with_langgraph(state: GraphState, app):
    # You would use the initial state to invoke the graph
    result = app.invoke(state)
    # print("Result is this:.......    ", str(result))
    # print(type(result))
    # Return the final result
    return result


if __name__ == "__main__":
    # Example 1: Standalone question
    initial_state_1 = {
        "question": "What is the capital of France?",
        "chat_history": [],
        "documents": [],
        "answer": "",
        "enhanced_question": "",
        "is_follow_up": False,
        "reset_history": False,
    }
    app = create_langgraph_app(None)
    logger.info("---RUNNING STANDALONE QUESTION WORKFLOW---")
    final_state_1 = app.invoke(initial_state_1)
    logger.info("\nFinal State (Standalone):")
    logger.info(final_state_1)

    logger.info("\n" + "=" * 50 + "\n")

    # Example 2: Follow-up question
    initial_state_2 = {
        "question": "and what about its population?",
        "chat_history": [
            HumanMessage(content="What is the capital of France?"),
            AIMessage(content="The capital of France is Paris."),
        ],
        "documents": [],
        "answer": "",
        "enhanced_question": "",
        "is_follow_up": False,
        "reset_history": False,
    }
    logger.info("---RUNNING FOLLOW-UP QUESTION WORKFLOW---")
    final_state_2 = app.invoke(initial_state_2)
    logger.info("\nFinal State (Follow-up):")
    logger.info(final_state_2)
