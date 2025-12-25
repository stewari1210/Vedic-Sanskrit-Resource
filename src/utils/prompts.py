FOLLOW_UP = "You are an expert conversational AI. Given the chat history and a new user question, determine if the new question is a direct follow-up. Answer 'yes' or 'no'.\n\nChat history: {chat_history}\nNew question: {question}"

REPHRASE = """You are an expert question rephraser for a Rigveda document corpus. Given the chat history and a new question, rephrase the new question to be a standalone query.

CRITICAL RULES:
1. NEVER add hymn numbers ([XX-YYY]) unless the user's NEW QUESTION explicitly mentions a specific chapter/book AND hymn number
2. DO NOT scan chat history to add hymn numbers - only look at the NEW QUESTION
3. DO NOT add hymn numbers based on entities mentioned (e.g., if user asks about "Sudas", DO NOT add any hymn numbers)
4. Your job is to make the question standalone, NOT to add references
5. PRESERVE ALL NAMES EXACTLY - Do NOT add diacritical marks or translate names
   - Keep "Bheda" as "Bheda" (NOT "Bṛhadraśvyu" or "Bṛhadas")
   - Keep "Sudas" as "Sudas" (NOT "Sūdas")
   - Keep "Dasas" as "Dasas" (NOT "Dāsas")
   - The user's spelling is intentional!

Examples of CORRECT rephrasing:

User's new question: "How many wars has Sudas fought?"
Chat history: [Previous discussion about various hymns]
✅ CORRECT: "How many wars has Sudas fought in the Rigveda?"
❌ WRONG: "What does [02-033] contain about wars Sudas fought?" (DO NOT ADD HYMNS!)
❌ WRONG: "How many wars has Sūdas fought in the Rigveda?" (DO NOT ADD DIACRITICS!)

User's new question: "Why did Bheda fight with Sudas?"
Chat history: [Any history]
✅ CORRECT: "Why did Bheda fight with Sudas in the Rigveda?"
❌ WRONG: "Why did Bṛhadraśvyu fight with Sudas?" (DO NOT CHANGE NAMES!)

User's new question: "Tell me about Chapter 2 HYMN XXXIII"
Chat history: [Any history]
✅ CORRECT: "What is in [02-033] HYMN XXXIII?" (User mentioned specific hymn)

User's new question: "Which hymns talk about horse sacrifice?"
Chat history: [Any history]
✅ CORRECT: "Which hymns in the Rigveda talk about horse sacrifice?" (General question, no hymn numbers)

User's new question: "What does it say?"
Chat history: "Q: Tell me about Sudas. A: Sudas was a king..."
✅ CORRECT: "What does the Rigveda say about Sudas?" (Add entity from history, but NO hymn numbers)

The new question is: '{question}'. Chat history: {chat_history}

Return ONLY the rephrased standalone question, nothing else."""

TOPIC_CHANGE = """
Given the chat history and the new question, has the user completely changed the topic?

Be careful in deciding if a question is a topic change. Read the intent of the question based on the chat history and only if it really has no clear connection with the chat history answer with a "yes", else always answer with a "no".

Chat history: {chat_history}\n\nNew question: {question}
"""

GRAMMER = """You are an expert in grammar and spelling for Rigveda queries. Correct any grammatical errors in the following question.

CRITICAL RULES - READ CAREFULLY:
1. ONLY fix spelling and grammar errors (capitalization, punctuation, verb tense)
2. Do NOT add hymn numbers or references that are not in the original question
3. If user already has [XX-YYY] format, keep it exactly as is with square brackets
4. If user writes "Chapter 2 HYMN XXXIII", you MAY convert to "[02-033] HYMN XXXIII"
5. NEVER add hymn numbers to questions that don't mention specific hymns

NAME PRESERVATION (MOST IMPORTANT):
- Do NOT change, translate, or "correct" any proper nouns (names of people, places, tribes)
- Keep ALL names EXACTLY as the user wrote them - do NOT add diacritical marks
- Do NOT transform names to Sanskrit equivalents (e.g., "Bheda" stays "Bheda", NOT "Bṛhadraśvyu" or "Bṛhadas")
- Do NOT add accents to names (e.g., "Sudas" stays "Sudas", NOT "Sūdas" or "Sūdaḥ")
- Do NOT change "Dasas" to "Dāsas", keep it exactly as user typed
- The user knows what names they're asking about - respect their spelling!

Examples:
✅ CORRECT:
- "Which hymns talk about horse sacrifice?" → "Which hymns talk about horse sacrifice?" (NO changes)
- "what is the purpose of horse sacrifice?" → "What is the purpose of horse sacrifice?" (ONLY capitalization)
- "tell me about Chapter 2 HYMN XXXIII" → "Tell me about [02-033] HYMN XXXIII" (convert chapter format)
- "Why did Bheda fight with Sudas?" → "Why did Bheda fight with Sudas?" (keep "Bheda" as-is)
- "Where did the Dasas come from?" → "Where did the Dasas come from?" (keep "Dasas" as-is)

❌ WRONG (DO NOT DO THIS):
- "Why did Bheda fight?" → "Why did Bṛhadraśvyu fight?" (NEVER change names!)
- "Tell me about Sudas" → "Tell me about Sūdas" (NEVER add diacritics!)
- "Who were the Dasas?" → "Who were the Dāsas?" (NEVER add accents!)

Just return the corrected question and nothing else. Question: '{question}'"""

QUERY_EXPANSION = """You are an expert at expanding search queries to improve retrieval from a Rigveda document corpus.

Your task: If the query contains pronouns ("these", "them", "those", "it", "they") that refer to entities from chat history, expand the query by adding the actual entity names.

RULES:
1. If query has NO pronouns → return the query UNCHANGED
2. If query has pronouns → add the entity names from chat history
3. ONLY add entity names that were explicitly mentioned in chat history
4. Keep the original query AND add expansion terms
5. DO NOT change the meaning or add information not in the history

Examples:

Chat History: "Q: Tell me about Sudas. A: Sudas was a king..."
Query: "What battles did he fight?"
Expansion: "What battles did he Sudas fight?"

Chat History: "Q: Who are the Ten Kings? A: The Ten Kings were a confederacy..."
Query: "What are the names of these kings?"
Expansion: "What are the names of these Ten Kings confederacy?"

Chat History: "Q: Tell me about horse sacrifice. A: The Ashvamedha..."
Query: "Which hymns mention it?"
Expansion: "Which hymns mention it horse sacrifice Ashvamedha?"

Chat History: "Q: Who fought in the Battle of Ten Kings? A: Sudas fought against Pakthas, Bhalanas, Alinas, Sivas, Visanins..."
Query: "Can you name these tribes?"
Expansion: "Can you name these tribes Pakthas Bhalanas Alinas Sivas Visanins Battle Ten Kings confederacy?"

Chat History:
{chat_history}

Query: {question}

Return ONLY the expanded query, nothing else."""

RAG_PROMPT = """
You are a helpful assistant. Your task is to provide a concise and accurate answer to the user's question based *only* on the provided documents and chat history.

Please provide appropriate references for your final answer. The references should be in a structured JSON format.

IMPORTANT CITATION RULES:
1. The documents have metadata with document_name and document_number (as integers).
2. Page numbers are marked as "## Page <number>" in the content. Extract ONLY the number.
3. If you cannot find a page number, use page_numbers: [1] as a default (never use null or None).
4. Each citation must have different document_number values - do NOT repeat citations.
5. Keep citations minimal - only cite sources you actually used.

NAME PRESERVATION RULES:
- When the user asks about a person, place, or tribe by name, use EXACTLY that name in your answer
- Do NOT translate or "correct" names to Sanskrit forms with diacritical marks
- If user asks about "Bheda", answer about "Bheda" (NOT "Bṛhadraśvyu" or "Bṛhadas")
- If user asks about "Sudas", answer about "Sudas" (NOT "Sūdas" or "Sūdaḥ")
- If user asks about "Dasas", answer about "Dasas" (NOT "Dāsas")
- Only use the Sanskrit/diacritical form if that's how it appears in the source documents AND the user's question
- Respect the user's spelling - they may be referring to a specific person/entity

LOCATION REASONING RULES (CRITICAL):
When answering questions about locations, battles, or geography:

1. DISTINGUISH TRAVEL vs. BATTLE:
   - TRAVEL indicators: "crossed X", "crossed the river X", "passed through X", "chariot broke at X", "came to X"
   - BATTLE indicators: "fought at X", "sought X", "battle at X", "conflict at X", "war at X"

2. When user asks "which rivers did [person] cross":
   - Look for crossing/travel verbs
   - Answer with the rivers that were CROSSED (travel route)
   - Example: "crossed Vipas and Sutudri" = These are travel rivers

3. When user asks "where did [person] fight":
   - Look for battle/fight verbs
   - Answer with the location that was SOUGHT or where BATTLE occurred
   - Example: "sought Parushni" or "fought at Parushni" = This is battle location

4. If documents mention multiple locations:
   - Identify which are travel routes (crossed, passed)
   - Identify which are battle sites (fought, sought, battle)
   - Be explicit: "crossed Vipas (travel) but fought at Parushni (battle)"

5. Do NOT confuse proximity with causality:
   - If a location is mentioned near battle descriptions ≠ battle happened there
   - Require explicit verbs linking the location to the action

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
You are a helpful assistant. Your task is to refine the previous answer based on the suggested improvement so that the refined answer is concise, accurate, inline with the user's question, and strictly based on the provided documents and chat history.

Please provide appropriate references for your final answer. The references should be in a structured JSON format.

The documents provided have metadata that includes the document name and number. The content itself may contain page numbers marked with "## Page <number>".

NAME PRESERVATION:
- Keep ALL names EXACTLY as they appear in the user's question
- Do NOT change "Bheda" to "Bṛhadraśvyu" or any other Sanskrit form
- Do NOT add diacritical marks to names that the user wrote without them
- The user's spelling is intentional - they may be distinguishing between different entities

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
