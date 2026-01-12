# Agentic RAG Query Types

The Agentic RAG system handles three types of queries differently, using specialized tools and reasoning chains for each.

## Query Type Classification

The agent classifies queries based on keywords:

### 1. **CONSTRUCTION Queries**
**Keywords:** "how do i say", "translate", "in sanskrit", "sanskrit for", "how to say", "say in sanskrit", "sanskrit word for", "construct", "write in sanskrit"

**Example Queries:**
- "Can you translate I love you in Sanskrit?"
- "How do I say I want milk?"
- "What is good morning in Sanskrit?"
- "Construct: The fire burns bright"

**Agent Flow:**
```
Question → Dictionary Lookup → Grammar Rules → Corpus Examples → Synthesize Construction
```

**Tools Used:**
1. **Dictionary Lookup**: Finds Sanskrit equivalents for English words
2. **Grammar Rules Search**: Retrieves declension/conjugation rules
3. **Corpus Examples Search**: Finds usage examples in Rigveda/Yajurveda

**Output Format:**
- Sanskrit in Devanagari
- IAST transliteration
- Word-by-word breakdown with grammar
- Grammar notes explaining construction

---

### 2. **GRAMMAR Queries**
**Keywords:** "explain", "what is the rule", "how does", "declension", "conjugation"

**Example Queries:**
- "Explain the declension of agni"
- "What is the rule for sandhi?"
- "How does the present tense conjugation work?"
- "What are the cases in Sanskrit?"

**Agent Flow:**
```
Question → Grammar Rules → Corpus Examples → Synthesize Explanation
```

**Tools Used:**
1. **Grammar Rules Search**: Retrieves relevant Macdonell grammar rules
2. **Corpus Examples Search**: Finds examples demonstrating the rule

**Output Format:**
- Clear explanation of the grammar rule
- Examples with Devanagari and IAST
- Step-by-step breakdown
- Usage notes

---

### 3. **FACTUAL Queries**
**Keywords:** None of the above (default)

**Example Queries:**
- "Who is Indra?"
- "What is the significance of Soma?"
- "Tell me about the Rigveda"
- "What are the major gods in the Vedas?"
- "Explain the fire ritual"

**Agent Flow:**
```
Question → Corpus Search → Synthesize Answer (RAG-style)
```

**Tools Used:**
1. **Corpus Examples Search**: Semantic search across Rigveda/Yajurveda for relevant passages

**Output Format:**
- Direct answer to the question
- Citations from corpus passages
- Sanskrit terms with transliteration
- Context from Vedic texts

---

## Comparison with Traditional RAG

| Aspect | Traditional RAG | Agentic RAG (Factual) | Agentic RAG (Construction) |
|--------|----------------|----------------------|---------------------------|
| **Query Analysis** | None | Classifies query type | Classifies + extracts words |
| **Tools** | 1 (retriever) | 1 (corpus search) | 3 (dictionary + grammar + corpus) |
| **Reasoning** | Single-step | Single-step | Multi-step sequential |
| **Context** | Top-k chunks | Top-k chunks | Dictionary + Grammar + Examples |
| **Output** | Generated answer | RAG answer | Constructed sentence |

## Benefits of Agentic Approach

### For Construction Queries:
✅ **Better translations**: Uses dictionary for accurate word choices
✅ **Grammar awareness**: Retrieves relevant grammar rules
✅ **Example-based**: Shows how words are used in actual texts
✅ **Pedagogical**: Explains construction step-by-step

### For Grammar Queries:
✅ **Targeted retrieval**: Gets specific grammar rules
✅ **Contextual examples**: Shows rules in practice
✅ **Clear explanations**: LLM synthesizes with educational focus

### For Factual Queries:
✅ **Similar to traditional RAG**: Direct corpus search
✅ **Context-aware**: Agent knows this is a factual question
✅ **Better synthesis**: LLM knows to cite sources and explain
✅ **Fallback handling**: Clear message if corpus lacks info

## Technical Implementation

### Tool Definitions:
```python
@tool
def dictionary_lookup(word: str) -> str:
    """19K+ entry Monier-Williams dictionary"""

@tool
def grammar_rules_search(sanskrit_word: str, context: str) -> str:
    """Macdonell grammar search"""

@tool
def corpus_examples_search(sanskrit_terms: str, pattern: str) -> str:
    """Rigveda/Yajurveda semantic search"""
```

### State Management:
```python
class AgentState(TypedDict):
    question: str
    query_type: str  # "construction" | "grammar" | "factual"
    english_words: List[str]  # Extracted words
    sanskrit_words: dict  # Dictionary results
    grammar_rules: List[Document]
    corpus_examples: List[Document]
    next_action: str  # Tool routing
    answer: dict  # Final output
```

### Graph Flow:
```
Entry → classify_and_plan → execute_tools → synthesize → END
            ↓                      ↓
       [Decides type]      [Calls tools based on type]
       [Extracts words]    [Routes: dict→gram→corpus]
```

## Testing Different Query Types

### Test Construction:
```
You: Can you translate I love you in Sanskrit?
Agent: [Shows dictionary → grammar → corpus flow]
Output: Sanskrit construction with full explanation
```

### Test Grammar:
```
You: Explain the declension of agni
Agent: [Shows grammar → corpus flow]
Output: Grammar rule explanation with examples
```

### Test Factual:
```
You: Who is Indra?
Agent: [Shows corpus search flow]
Output: RAG-style answer from Vedic passages
```

## Future Enhancements

1. **Better classification**: Use LLM to classify instead of keyword matching
2. **Iterative retrieval**: Agent can decide to search again if info insufficient
3. **Cross-query learning**: Cache common constructions/rules
4. **User feedback**: Learn from corrections to improve future responses
5. **Multi-turn conversations**: Remember context across queries
