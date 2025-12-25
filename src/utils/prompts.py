FOLLOW_UP = "You are an expert conversational AI. Given the chat history and a new user question, determine if the new question is a direct follow-up. Answer 'yes' or 'no'.\n\nChat history: {chat_history}\nNew question: {question}"

REPHRASE = """You are an expert question rephraser for a Rigveda document corpus. Given the chat history and a new question, rephrase the new question to be a standalone query.

IMPORTANT: The Rigveda hymns are formatted as [XX-YYY] HYMN in the documents (e.g., [02-033] HYMN XXXIII).

ONLY add hymn numbers if:
1. User explicitly mentions a specific chapter/book number (e.g., "Chapter 2")
2. User explicitly mentions a specific hymn number (e.g., "HYMN XXXIII" or "hymn 33")

DO NOT add hymn numbers for general questions like:
- "Which hymns talk about X?" → Keep as "Which hymns talk about X?"
- "What hymns mention Y?" → Keep as "What hymns mention Y?"

Conversion rules ONLY when specific hymns are mentioned:
- "Chapter 2 HYMN XXXIII" → "What is in [02-033] HYMN XXXIII?"
- "hymn 33 in book 2" → "Content of [02-033] HYMN XXXIII"
- "tell me about HYMN XXXIII" → "What does HYMN XXXIII contain?" (no specific book = no [XX-YYY])

The new question is: '{question}'. Chat history: {chat_history}"""

TOPIC_CHANGE = """
Given the chat history and the new question, has the user completely changed the topic?

Be careful in deciding if a question is a topic change. Read the intent of the question based on the chat history and only if it really has no clear connection with the chat history answer with a "yes", else always answer with a "no".

Chat history: {chat_history}\n\nNew question: {question}
"""

GRAMMER = """You are an expert in grammar and spelling for Rigveda queries. Correct any grammatical errors in the following question.

CRITICAL RULES:
- ONLY fix spelling and grammar errors
- Do NOT add hymn numbers or references that are not in the original question
- If user already has [XX-YYY] format, keep it exactly as is with square brackets
- If user writes "Chapter 2 HYMN XXXIII", you MAY convert to "[02-033] HYMN XXXIII"
- NEVER add hymn numbers to questions that don't mention specific hymns
- Do NOT add diacritical marks to names (keep "Sudas" as "Sudas", not "Sūdaḥ" or "Sūdas")
- Keep proper nouns in their simple romanized form without accents

Examples:
- "Which hymns talk about horse sacrifice?" → "Which hymns talk about horse sacrifice?" (NO changes)
- "what is the purpose of horse sacrifice?" → "What is the purpose of horse sacrifice?" (ONLY capitalization)
- "tell me about Chapter 2 HYMN XXXIII" → "Tell me about [02-033] HYMN XXXIII" (convert chapter format)

Just return the corrected question and nothing else. Question: '{question}'"""

RAG_PROMPT = """
You are a helpful assistant. Your task is to provide a concise and accurate answer to the user's question based *only* on the provided documents and chat history.

Please provide appropriate references for your final answer. The references should be in a structured JSON format.

IMPORTANT CITATION RULES:
1. The documents have metadata with document_name and document_number (as integers).
2. Page numbers are marked as "## Page <number>" in the content. Extract ONLY the number.
3. If you cannot find a page number, use page_numbers: [1] as a default (never use null or None).
4. Each citation must have different document_number values - do NOT repeat citations.
5. Keep citations minimal - only cite sources you actually used.

If you cannot find a clear answer in the provided documents, state "I do not have enough information".

Chat History:
{chat_history}

Documents:
{documents}

Question: {question}

Final Answer:
"""

# The evaluation prompt
EVALUATION_PROMPT = """
You are an expert evaluator. Your task is to review whether an AI-generated answer to the latest user question is factually accurate based on the relevant source documents and the chat history.

Assess the confidence of the AI's answer based on how well it is supported by the documents and chat history.

NOTE: If the AI Answer is "I do not have enough information", **DO NOT EVALUATE** Just set confidence score to -1 and reasoning as "Not enough information".

Score the answer on a scale from 0 to 100, where:
- 90 - 100%: Answer is completely accurate and directly supported by the documents and chat history.
- 80 - 90%: Answer is highly accurate and supported by the documents and chat history.
- 70 - 80%: Answer is somewhat accurate and supported by the documents and chat history.
- 50 - 60%: Answer may not be accurate or factual. It is only partially supported by the documents and chat history.
- 0 - 50%: Answer is not factual at all.

NOTE: Please always return an integer for Confidence Score, i.e., do not return "80", return 80.

Provide a brief reasoning for your score, citing specific parts of the documents or noting where information is missing and how it can be improved.

Chat History:
{chat_history}

Documents:
{documents}

Question:
{question}

AI Answer:
{answer}
"""

REFINE_PROMPT = """
You are a helpful assistant. Your task is to refine the previous answer based on the suggested improvement so that the refined answers is concise, accurate, inline with the user's question, and strictly based on the provided documents and chat history.

Please provide appropriate references for your final answer. The references should be in a structured JSON format.

The documents provided have metadata that includes the document name and number. The content itself may contain page numbers marked with "## Page <number>".

If you cannot find a clear answer in the provided documents, state "I do not have enough information".

Chat History:
{chat_history}

Documents:
{documents}

Question:
{question}

Previous Answer:
{answer}

Suggested Improvements:
{suggested_improvements}

Final Answer:
"""
