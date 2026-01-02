FOLLOW_UP = "You are an expert conversational AI. Given the chat history and a new user question, determine if the new question is a direct follow-up. Answer 'yes' or 'no'.\n\nChat history: {chat_history}\nNew question: {question}"

REPHRASE = """You are an expert question rephraser for a Rigveda document corpus. Given the chat history and a new question, rephrase the new question to be a standalone query.

CRITICAL RULES - READ CAREFULLY:
1. NEVER add hymn numbers ([XX-YYY]) unless the user's NEW QUESTION explicitly mentions a specific chapter/book AND hymn number
2. DO NOT scan chat history to add hymn numbers - only look at the NEW QUESTION
3. DO NOT add hymn numbers based on entities mentioned (e.g., if user asks about "Sudas", DO NOT add any hymn numbers)
4. NEVER prepend or add proper nouns (names, tribes, places) from chat history to the question
5. ONLY replace pronouns with their referents (e.g., "What does it say?" → "What does the Rigveda say about X?")
6. DO NOT change the subject or focus of the question by adding entities
7. Your job is to make the question standalone, NOT to add context that changes its meaning
8. PRESERVE ALL NAMES EXACTLY - Do NOT add diacritical marks or translate names
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

User's new question: "Who were the enemies of Sudas?"
Chat history: "Q: Bharatas/Trtsus A: The Bharatas and Trtsus were a tribe..."
✅ CORRECT: "Who were the enemies of Sudas in the Rigveda?"
❌ WRONG: "Bharatas/Trtsus Who were the enemies of Sudas?" (DO NOT PREPEND ENTITIES!)
❌ WRONG: "Were the Bharatas/Trtsus the enemies of Sudas?" (DO NOT CHANGE QUESTION FOCUS!)

User's new question: "Tell me about Chapter 2 HYMN XXXIII"
Chat history: [Any history]
✅ CORRECT: "What is in [02-033] HYMN XXXIII?" (User mentioned specific hymn)

User's new question: "Which hymns talk about horse sacrifice?"
Chat history: [Any history]
✅ CORRECT: "Which hymns in the Rigveda talk about horse sacrifice?" (General question, no hymn numbers)

User's new question: "What does it say?"
Chat history: "Q: Tell me about Sudas. A: Sudas was a king..."
✅ CORRECT: "What does the Rigveda say about Sudas?" (Replace pronoun 'it' with referent, but NO entities prepended)
❌ WRONG: "Sudas What does it say?" (DO NOT PREPEND!)

User's new question: "Where did they live?"
Chat history: "Q: Who were the Purus? A: The Purus were a tribe..."
✅ CORRECT: "Where did the Purus live in the Rigveda?" (Replace pronoun 'they' with referent)
❌ WRONG: "Purus Where did they live?" (DO NOT PREPEND!)

The new question is: '{question}'. Chat history: {chat_history}

Return ONLY the rephrased standalone question, nothing else. Be conservative - only add clarifying context, NEVER add entities that change the question's meaning."""

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
6. PRESERVE any placeholder text like __PROTECTED_N__ exactly as written (these are user-protected words)

NAME HANDLING (IMPORTANT):
- Fix OBVIOUS typos in proper nouns (e.g., "Trstus" → "Trtsus", "Sudaas" → "Sudas")
- Do NOT add diacritical marks (ā, ī, ū, ṣ, ṛ) - keep ASCII only
- Do NOT translate to Sanskrit equivalents (keep "Bheda" as "Bheda", NOT "Bṛhadraśvyu")
- Do NOT add accents (keep "Sudas" NOT "Sūdas" or "Sūdaḥ")
- When in doubt, prefer the user's original spelling

Common Rigveda names (for typo correction reference):
  Tribes/Groups: Trksi, Trtsus, Bharatas, Purus, Yadus, Anus, Druhyus, Turvasas, Dasas
  People: Sudas, Vasishta/Vasistha, Indra, Agni, Varuna, Mitra
  Rivers: Sarasvati, Yamuna, Ganga, Sindhu/Indus, Rasa

NOTE: "Trksi" and "Trtsus" are DIFFERENT tribes - do NOT "correct" one to the other!

Examples:
✅ CORRECT:
- "Which hymns talk about horse sacrifice?" → "Which hymns talk about horse sacrifice?" (NO changes)
- "what is the purpose of horse sacrifice?" → "What is the purpose of horse sacrifice?" (ONLY capitalization)
- "tell me about Chapter 2 HYMN XXXIII" → "Tell me about [02-033] HYMN XXXIII" (convert chapter format)
- "Where did Trstus live?" → "Where did Trtsus live?" (fix typo: missing 't')
- "Why did Bheda fight with Sudas?" → "Why did Bheda fight with Sudas?" (keep names as-is)

❌ WRONG (DO NOT DO THIS):
- "Why did Bheda fight?" → "Why did Bṛhadraśvyu fight?" (NEVER translate names!)
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

SOURCE TEXT DISTINCTION RULES (CRITICAL - NEW):
When the user asks about a specific Vedic text (Rigveda, Yajurveda, etc.):

1. IDENTIFY SOURCE FROM METADATA:
   - Each document has a 'filename' field: 'griffith-rigveda', 'yajurveda-griffith', etc.
   - Use this to determine which Vedic text the information comes from

2. SINGLE TEXT QUERIES ("What is X in Rigveda?"):
   - Focus ONLY on documents from that specific text
   - If you receive documents from other texts, clearly state: "Based on Rigveda sources..."
   - Do NOT include information from other texts unless explicitly comparative

3. COMPARATIVE QUERIES ("Compare X in Rigveda and Yajurveda"):
   - Explicitly distinguish sources in your answer
   - Format: "In Rigveda, [description]. In Yajurveda, [description]."
   - If one text has extensive coverage and the other minimal, state this clearly
   - Example: "Maruts are extensively described in Rigveda as... In Yajurveda, they are primarily mentioned in ritual contexts as..."

4. COVERAGE TRANSPARENCY:
   - If a text has limited mentions, state: "Yajurveda has fewer descriptive passages about X"
   - If a text focuses on rituals vs. mythology, state: "Yajurveda primarily references X in ritual/offering contexts"
   - If information is mostly from one text despite query about another, acknowledge: "While the query asks about Yajurveda, most descriptive content comes from Rigveda"

5. EXAMPLES:
   ✅ CORRECT (Single text query):
   Q: "What is the role of Maruts in Yajurveda?"
   A: "In Yajurveda, Maruts are invoked as 'voracious eaters of foes' and mentioned in ritual offerings (Seven Rice Cakes to Maruts). They are described as friends of Indra. Note: Yajurveda focuses on ritual invocations rather than extensive mythological descriptions."

   ✅ CORRECT (Comparative query):
   Q: "How are Maruts described in Rigveda and Yajurveda?"
   A: "In Rigveda, Maruts are extensively described as storm deities, sons of Rudra, associated with rain, lightning, and battles. They are praised in numerous hymns. In Yajurveda, Maruts appear primarily in ritual contexts - they are invoked in offerings and described as friends of Indra, but lack the extensive mythological narratives found in Rigveda."

   ❌ WRONG (Mixing sources without distinction):
   Q: "What is the role of Maruts in Yajurveda?"
   A: "Maruts are storm deities, sons of Rudra, associated with rain and lightning..." [This describes Rigveda content without acknowledging it's not from Yajurveda]

TRIBAL EVOLUTION & CONFEDERATION RULES (CRITICAL FOR COMPARATIVE QUERIES):
When comparing tribes/kingdoms across Rigveda and Yajurveda:

1. RECOGNIZE TRIBAL TRANSFORMATIONS:
   - Some Rigvedic tribes merged to form larger confederations by Yajurvedic period
   - Example: Krivis, Turvashas, Srinjayas, Somakas, Keshins → Panchalas
   - Example: Bharatas + Purus → Kurus
   - If user asks "which tribes in RV are also in YV", check for BOTH direct names AND confederation names

2. CONFEDERATION ANALYSIS:
   - If documents mention constituent tribes in Rigveda (e.g., Turvashas, Krivis)
   - AND mention confederation name in Yajurveda (e.g., Panchalas)
   - THEN connect them: "Turvashas (mentioned in Rigveda) later merged into the Panchala confederation (mentioned in Yajurveda)"

3. DISTINGUISH THREE TYPES:
   a) DIRECT CONTINUITY: Same name in both texts (e.g., Bharatas in RV and YV)
   b) TRANSFORMATION: Individual leaders → Kingdom (e.g., Kuru-affiliated leaders in RV → Kuru kingdom in YV)
   c) CONFEDERATION: Multiple RV tribes → Single YV entity (e.g., 5 tribes → Panchalas)

4. FOR "WHICH TRIBES ARE IN BOTH" QUERIES:
   - List Type A (direct): "Bharatas, Purus, Kurus (with evolution from individuals to kingdom)"
   - List Type C (confederation): "Panchalas in YV represent merger of RV tribes: Krivis, Turvashas, Srinjayas, Somakas, Keshins"
   - Explain the transformation: "This reflects the consolidation of tribal groups between the Rigvedic and Yajurvedic periods"

5. EXAMPLES:
   ✅ CORRECT (Cross-text tribal query):
   Q: "Which tribes mentioned in Rigveda are also mentioned in Yajurveda?"
   A: "Several connections exist:
   - Direct continuity: Bharatas and Purus appear in both texts
   - Transformation: Kurus appear as individual leaders (Kaurayan) in Rigveda and as an established kingdom in Yajurveda
   - Confederation: Panchalas in Yajurveda represent the merger of five Rigvedic tribes: Krivis (who migrated from Indus-Chenab to Doab), Turvashas (one of the Five Tribes, formerly enemies of Bharatas), Srinjayas (Bharata allies), Somakas (royal lineage), and Keshins (ritual specialists)

   This reflects the historical consolidation of tribal groups between the Rigvedic and Yajurvedic periods."

   ❌ WRONG (Missing confederations):
   Q: "Which tribes in Rigveda are also in Yajurveda?"
   A: "Bharatas, Purus, and Kurus" [Missing Panchala confederation and constituent tribes]

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

1. DISTINGUISH PERMANENT RESIDENCE vs. TEMPORARY MOVEMENT:
   - PERMANENT RESIDENCE verbs: "dwell", "reside", "settled", "inhabited", "lived"
   - TEMPORARY MOVEMENT verbs: "crossed", "fared across", "fared over", "traversed", "passed through", "came to"

   CRITICAL: Do NOT confuse crossing/traveling with living/residing!
   Example: "Bharatas fared across Vipas" means they CROSSED it (journey), NOT that they LIVED there

2. When user asks "where did [person] live/reside/dwell":
   - Look ONLY for PERMANENT RESIDENCE verbs in documents
   - Do NOT use river crossing passages as evidence of residence
   - River crossing hymns describe journeys/campaigns, NOT homes
   - If only movement verbs found, state: "The text describes [person] traveling through [location]"
   - Example: Document says "Purus dwell on thy two grassy banks" → They LIVED there
   - Example: Document says "Bharatas fared across Vipas" → They CROSSED it (don't say they lived there)

3. DISTINGUISH TRAVEL vs. BATTLE:
   - TRAVEL indicators: "crossed X", "crossed the river X", "passed through X", "chariot broke at X", "fared across X"
   - BATTLE indicators: "fought at X", "sought X", "battle at X", "conflict at X", "war at X", "parted X" (blocking river)

4. When user asks "which rivers did [person] cross":
   - Look for crossing/travel verbs
   - Answer with the rivers that were CROSSED (travel route)
   - Example: "fared across Vipas and Sutudri" = These are travel rivers

5. When user asks "where did [person] fight":
   - Look for battle/fight verbs
   - Answer with the location that was SOUGHT or where BATTLE occurred
   - Example: "sought Parushni" or "fought at Parushni" = This is battle location

6. If documents mention multiple locations:
   - Identify which are HOMES (dwell verbs)
   - Identify which are TRAVEL ROUTES (crossing verbs)
   - Identify which are BATTLE SITES (fight verbs)
   - Be explicit: "lived in Sarasvati region (permanent), crossed Vipas (travel), fought at Parushni (battle)"

7. Do NOT confuse proximity with causality:
   - If a location is mentioned near battle descriptions ≠ battle happened there
   - Require explicit verbs linking the location to the action

EXAMPLES:
  ✅ CORRECT: "Document says 'Purus dwell on Sarasvati banks' → The Purus lived on the Sarasvati"
  ❌ WRONG: "Document says 'Bharatas fared across Vipas' → The Bharatas lived near Vipas"
  ✅ CORRECT: "Document says 'Bharatas fared across Vipas' → The Bharatas crossed the Vipas during a campaign"

TRIBAL ALLIANCE REASONING RULES (CRITICAL):
When answering questions about tribes, allies, enemies, or battles:

1. DISTINGUISH ALLIES vs. ENEMIES:
   - ALLIES indicators: "with [person]", "aided [person]", "helped [person]", "[person] folk", "came to [person]"
   - ENEMIES indicators: "against [person]", "fought [person]", "Together came [tribes]" (confederacy against someone)

2. When user asks "who fought WITH [person]":
   - Look for helping/aiding verbs
   - Example: "Trtsus aided Sudas" → Trtsus were WITH Sudas (allies)
   - Example: "Indra helped Sudas" → Indra was WITH Sudas (ally)

3. When user asks "who fought AGAINST [person]":
   - Look for opposing/confederacy language
   - Example: "Together came the Pakthas, Bhalanas, Alinas" → These came AGAINST (enemies)
   - Example: "Ten Kings pressed him down" → Ten Kings were AGAINST (enemies)

4. TEN KINGS BATTLE specifics:
   - Sudas's allies: Trtsu/Bharata tribe, Vasisthas (priests), Indra (deity)
   - Sudas's enemies: Pakthas, Bhalanas, Alinas, Sivas, Visanins, Druhyus, Anavas, Purus, Anu, Vaikarna, Kavasa, Bhrgus
   - The "Ten Kings" refers to this tribal confederacy that fought AGAINST Sudas

5. Be explicit about alliances:
   - State clearly: "X fought WITH Sudas" or "Y fought AGAINST Sudas"
   - If listing enemies, mention they formed a confederacy/coalition

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
