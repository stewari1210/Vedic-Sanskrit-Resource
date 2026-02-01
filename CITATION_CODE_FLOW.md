# Citation System: Code Flow Documentation

## Exact Code Path for Each Query

### Query: "Who is Sudas?" - Complete Flow

**File: `src/utils/agentic_rag.py`**

```python
# Line 400-450: Main Query Processing
def synthesize_answer_node(state: dict):
    """Synthesize final answer using all tool results."""
    question = state["question"]
    # question = "Who is Sudas?"
    
    # Line 420: Get corpus examples
    corpus_info = state.get("corpus_examples", [])
    # corpus_info retrieved from execute_tools_node()
    
    # Line 550-555: CITATION ENHANCEMENT
    if corpus_info:
        corpus_context = enhance_corpus_results_with_citations(corpus_info[:5])
        # Calls citation_enhancer.py function
    
    # Line 560-570: Build LLM Prompt
    synthesis_prompt = f"""You are a Sanskrit scholar...
    
RELEVANT CORPUS PASSAGES FROM RIGVEDA:
{corpus_context}

INSTRUCTIONS:
1. Answer based on corpus passages
2. **IMPORTANT**: When citing passages, use verse references 
   shown in headers (e.g., "RV 1.33 - Sudas") instead of 
   generic "Passage N" labels
...
"""
    
    # Line 580: Call LLM
    response = llm.invoke(synthesis_prompt)
```

**File: `src/utils/citation_enhancer.py`**

```python
# Line 212: enhance_corpus_results_with_citations
def enhance_corpus_results_with_citations(examples: List[Document]) -> str:
    """Convert retrieved documents to formatted text with proper citations."""
    
    char_limit = 500
    formatted_passages = []
    
    # Loop through top 5 retrieved documents
    for i, doc in enumerate(examples):  # i=0,1,2,3,4
        # i=0: Sudas document from RV 1.33
        # i=1: Sudas document from RV 1.47
        # i=2: Sudas document from RV 7.18
        # i=3: Additional context
        # i=4: Additional context
        
        # Line 220: Format citation
        citation_label, source = CitationFormatter.format_citation_with_source(doc, i + 1)
        # CitationFormatter.format_citation_with_source(doc, 1)
        
        # Get content
        content = doc.page_content[:char_limit]
        
        # Format passage
        formatted_passage = f"{citation_label}:\n{content}"
        # formatted_passage = "RV 1.33 - Sudas:\n[content about Sudas]"
        
        formatted_passages.append(formatted_passage)
    
    # Line 227: Join all
    return "\n\n".join(formatted_passages)
```

**File: `src/utils/citation_enhancer.py`**

```python
# Line 147: CitationFormatter.format_citation_with_source
@staticmethod
def format_citation_with_source(doc: Document, passage_number: int) -> Tuple[str, str]:
    """Create a formatted citation from a document."""
    
    # doc.page_content = "[01-033] HYMN XXXIII.\n[Names (Griffith-Rigveda): Sudas]..."
    # passage_number = 1
    
    # STEP 1: Try to extract citation
    # Line 152: First try metadata (not used yet)
    citation = doc.metadata.get("verse_reference")  # None in current implementation
    
    # STEP 2: If not in metadata, extract from content
    # Line 155: Extract verse reference from content
    if not citation:
        citation = VedicCitationExtractor.extract_verse_reference(doc.page_content[:500])
        # Calls extract_verse_reference with first 500 chars
    
    # STEP 3: Extract section title
    # Line 159: Extract title
    section_title = VedicCitationExtractor.extract_section_title(doc.page_content)
    # section_title = "Sudas"
    
    # STEP 4: Get source
    # Line 162: Get filename
    source_identifier = doc.metadata.get('filename', 'unknown_source')
    # source_identifier = "rigveda-griffith_COMPLETE_english_with_metadata"
    
    # STEP 5: Format final citation
    # Line 165-172: Combine citation and title
    if citation and section_title:
        citation_label = f"{citation} - {section_title}"
        # citation_label = "RV 1.33 - Sudas" ✅
    elif citation:
        citation_label = citation
    else:
        citation_label = f"Passage {passage_number}"
    
    return citation_label, source_identifier
    # Returns: ("RV 1.33 - Sudas", "rigveda-griffith_...")
```

**File: `src/utils/citation_enhancer.py`**

```python
# Line 58: VedicCitationExtractor.extract_verse_reference
@staticmethod
def extract_verse_reference(text: str) -> Optional[str]:
    """Extract verse reference from text content."""
    
    # text = "[01-033] HYMN XXXIII.\n[Names (Griffith-Rigveda): Sudas]...[first 500 chars]"
    
    # Loop through patterns in priority order
    for pattern_name, pattern in VedicCitationExtractor.PATTERNS.items():
        # Pattern 1: 'bracket_reference' = r'\[(\d{2})-(\d{3})\]\s+(?:HYMN|BOOK|CANTO)'
        
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        # Match found! Groups: ('01', '033')
        
        if match:
            # PATTERN MATCHED!
            return VedicCitationExtractor._format_citation(pattern_name, match)
            # Calls _format_citation('bracket_reference', match)
    
    return None  # No pattern matched
```

**File: `src/utils/citation_enhancer.py`**

```python
# Line 87: VedicCitationExtractor._format_citation
@staticmethod
def _format_citation(pattern_name: str, match) -> str:
    """Format matched groups into proper citation format."""
    
    # pattern_name = 'bracket_reference'
    # match.groups() = ('01', '033')
    
    if pattern_name == 'bracket_reference':
        mandala, sukta = match.groups()
        # mandala = '01', sukta = '033'
        
        mandala_int = str(int(mandala))  # '01' → 1 → '1'
        sukta_int = str(int(sukta))      # '033' → 33 → '33'
        
        return f"RV {mandala_int}.{sukta_int}"
        # Returns: "RV 1.33" ✅
```

**Back to citation_enhancer.py**

```python
# Line 159-161: VedicCitationExtractor.extract_section_title
@staticmethod
def extract_section_title(text: str) -> Optional[str]:
    """Extract section title from text."""
    
    # text = "[01-033] HYMN XXXIII.\n[Names (Griffith-Rigveda): Sudas]..."
    
    # Pattern: r'\[Names \([^)]*\): ([^\]]+)\]'
    match = re.search(pattern, text, re.IGNORECASE)
    # Match found! Group 1: "Sudas"
    
    if match:
        title_string = match.group(1)
        # title_string = "Sudas"
        
        # If multiple names, take first
        names = title_string.split(',')
        # names = ["Sudas"]
        
        return names[0].strip()
        # Returns: "Sudas" ✅
    
    return None
```

**Back to agentic_rag.py - format_citation_with_source returns**

```python
# Back in format_citation_with_source
return citation_label, source_identifier
# Returns: ("RV 1.33 - Sudas", "rigveda-griffith_COMPLETE_english_with_metadata")
```

**Back to enhance_corpus_results_with_citations**

```python
# Continue loop for document 2
# i=1: Next Sudas reference
citation_label, source = CitationFormatter.format_citation_with_source(doc, 2)
# Returns: ("RV 1.47 - Sudas", "rigveda-griffith_COMPLETE_english_with_metadata")

formatted_passage = f"{citation_label}:\n{content}"
formatted_passages.append(formatted_passage)

# Continue for document 3
# i=2: Another Sudas reference  
citation_label, source = CitationFormatter.format_citation_with_source(doc, 3)
# Returns: ("RV 7.18 - Sudas", "rigveda-griffith_COMPLETE_english_with_metadata")

formatted_passage = f"{citation_label}:\n{content}"
formatted_passages.append(formatted_passage)

# All documents processed
corpus_context = "\n\n".join([
    "RV 1.33 - Sudas:\n[content]",
    "RV 1.47 - Sudas:\n[content]",
    "RV 7.18 - Sudas:\n[content]",
    # ... more
])
```

**Back to synthesize_answer_node**

```python
synthesis_prompt = f"""...
RELEVANT CORPUS PASSAGES FROM RIGVEDA:
RV 1.33 - Sudas:
[content about Sudas from RV 1.33]

RV 1.47 - Sudas:
[content about Sudas from RV 1.47]

RV 7.18 - Sudas:
[content about Sudas from RV 7.18]

INSTRUCTIONS:
1. Answer based on corpus passages
2. **IMPORTANT**: When citing passages, use verse references 
   shown in headers (e.g., "RV 1.33 - Sudas" or "RV 7.18 - Sudas") 
   instead of generic "Passage N" labels
...
"""

# LLM processes this prompt
response = llm.invoke(synthesis_prompt)

# LLM sees clear verse references in headers
# LLM follows instruction about using verse references
# LLM generates:
response = """
Sudas is an important figure in Vedic history. He is prominently 
mentioned in RV 1.33, where he is portrayed as a warrior-king. 
The verse describes how the Asvins brought victory to Sudas...

Additionally, RV 1.47 contains references to Sudas in the context 
of battles and victories...

In RV 7.18, Sudas is again mentioned as a heroic figure...
"""
```

---

### Query: "Who are Dasas?" - Complete Flow (With Issues)

**Same initial flow until enhance_corpus_results_with_citations...**

**File: `src/utils/citation_enhancer.py`**

```python
def enhance_corpus_results_with_citations(examples: List[Document]) -> str:
    
    for i, doc in enumerate(examples):
        # i=0: Document from RV 1.104 (Griffith, has header)
        citation_label, source = CitationFormatter.format_citation_with_source(doc, 1)
        # WORKS: Bracket pattern found, returns "RV 1.104 - Dasa, Dasyu, Indra"
        
        # i=1: Middle chunk from same hymn (Griffith, NO header)
        citation_label, source = CitationFormatter.format_citation_with_source(doc, 2)
        # PROBLEM: extract_verse_reference() searches only doc.page_content[:500]
        #          This chunk is from middle (no [01-104] marker)
        #          Pattern NOT found
        #          Falls back to "Passage 2" ❌
        
        # i=2: Document from Sharma translation (different format)
        citation_label, source = CitationFormatter.format_citation_with_source(doc, 3)
        # PROBLEM: Bracket pattern [01-XXX] doesn't exist in Sharma format
        #          Sharma uses "RV 1.104 - ..." format
        #          Bracket extraction fails
        #          Falls back to "Passage 3" ❌
        
        # i=3: Another Griffith document
        citation_label, source = CitationFormatter.format_citation_with_source(doc, 4)
        # WORKS: Returns "RV 1.178 - Agni, Dasa, Indra"
        
        # i=4: Another middle chunk
        citation_label, source = CitationFormatter.format_citation_with_source(doc, 5)
        # PROBLEM: No header, falls back to "Passage 5" ❌
```

**The problematic format_citation_with_source call:**

```python
# Document i=1: Middle chunk without header
doc.page_content = "...continuing content about Dasas without hymn marker..."

citation = VedicCitationExtractor.extract_verse_reference(doc.page_content[:500])
# SEARCHES: First 500 chars of middle chunk
# LOOKS FOR: [01-XXX] bracket pattern
# RESULT: NO MATCH (bracket is in first chunk, not this one)
# Returns: None ❌

section_title = VedicCitationExtractor.extract_section_title(doc.page_content)
# LOOKS FOR: [Names (...): ...]
# RESULT: NO MATCH (section header is in first chunk)
# Returns: None ❌

# Both are None
if citation and section_title:  # False and False
    citation_label = ...
elif citation:                  # False
    citation_label = ...
else:
    citation_label = f"Passage {passage_number}"  # ← FALLBACK
    # citation_label = "Passage 2" ❌
```

**The Sharma translation problem:**

```python
# Document i=2: Sharma translation
doc.page_content = "RV 1.104 - Dasa appears in battles...\nContent about Dasas..."

# TRY Pattern 1: 'bracket_reference'
pattern = r'\[(\d{2})-(\d{3})\]\s+(?:HYMN|BOOK|CANTO)'
match = re.search(pattern, doc.page_content[:500])
# LOOKING FOR: [01-104] format
# CONTENT HAS: "RV 1.104" format (no brackets!)
# RESULT: NO MATCH ❌

# TRY Pattern 2: 'rigveda_hymn'
pattern = r'(?:RV|Rigveda)\s+(\d+)\.(\d+)(?:\.(\d+))?'
match = re.search(pattern, doc.page_content[:500])
# LOOKING FOR: "RV 1.104" format
# CONTENT HAS: "RV 1.104" format
# RESULT: MATCH! ✅
# Returns: "RV 1.104"

# But wait - this pattern is AFTER bracket_reference in the loop
# The bracket pattern is tried FIRST
# Since bracket_reference is in PATTERNS dict as first entry
# and it FAILS, next pattern is tried

# Actually - PROBLEM: rigveda_hymn pattern comes SECOND
# Need to check actual PATTERNS dict order...

PATTERNS = {
    'bracket_reference': ...,      # Tried first
    'rigveda_hymn': ...,           # Tried second
    'yajurveda_verse': ...,        # etc
    # ...
}

# So bracket fails, then rigveda_hymn should match
# Hmm - need to check actual code
```

Let me verify the actual pattern order in the code:
<br/>

**Checking src/utils/citation_enhancer.py lines 28-37:**

```python
PATTERNS = {
    'bracket_reference': r'\[(\d{2})-(\d{3})\]\s+(?:HYMN|BOOK|CANTO)',
    'rigveda_hymn': r'(?:RV|Rigveda)\s+(\d+)\.(\d+)(?:\.(\d+))?',
    'yajurveda_verse': r'(?:YV|Yajurveda|Verse)\s+(\d+)\.(\d+)',
    'brahmana_reference': r'(?:Satapatha|SB|Brahmana)\s+(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?',
    'mantra_number': r'(?:Mantra|Sukta|Adhyaya)\s+(\d+)',
    'heading_pattern': r'^#+\s*(?:Hymn|Verse|Sutra|Section|Book|Mandala)\s+(\d+)(?:[:\-]\s*(.+))?',
    'book_canto_pattern': r'(?:Book|Canto|Adhyaya)\s+([IVX]+|\d+)',
}
```

So in Python 3.7+, dicts maintain insertion order. The `rigveda_hymn` pattern IS second, so it should match Sharma format!

**Ah - the real issue for Sharma:**

```python
# Document i=2: Sharma translation
doc.page_content = "RV 1.104 - Dasa appears...\n..."

# Pattern 1 'bracket_reference': [01-104] format → NO MATCH
# Pattern 2 'rigveda_hymn': RV 1.104 format → MATCH ✅
# citation = "RV 1.104" (formatted from matched groups)

# Now extract section title
section_title = extract_section_title(doc.page_content)
# LOOKING FOR: [Names (Griffith-Rigveda): ...]
# Sharma format DOESN'T have this pattern
# RESULT: NO MATCH ❌
# Returns: None

# So we get
if citation and section_title:  # "RV 1.104" and None
    citation_label = ...        # False (title is None)
elif citation:
    citation_label = citation   # TRUE!
    # citation_label = "RV 1.104" ✅

# Actually Sharma MIGHT work if bracket search fails!
```

**Let me reconsider - checking actual output from user's query:**

The user showed: "Passage 4 directly mentions..." suggesting they got "Passage 4"

This means:
- Document 1: Got citation (works)
- Document 2: Got "Passage 2" (middle chunk problem)
- Document 3: Got "Passage 3" (could be Sharma or middle chunk)
- Document 4: Got "Passage 4" (middle chunk problem)

So the actual issue is a mix of:
1. ✅ Some Griffith first-chunk documents work
2. ❌ Griffith middle chunks lose citations
3. ❌ Possibly some Sharma documents (depends on section_title extraction)

---

## Summary: The Code Path Issue

| Phase | Sudas Query | Dasas Query | Issue |
|-------|-------------|------------|-------|
| **Retrieval** | Returns RV 1.33, RV 1.47, RV 7.18 | Returns mixed: first chunks + middle chunks + other translations | RAG retrieves relevant but not always with headers |
| **Citation Extraction** | `[01-033]` found, `[Names: Sudas]` found | Sometimes not found (missing from middle chunks) | Only searches first 500 chars |
| **Section Title** | "Sudas" extracted | "Dasa, Dasyu, Indra..." or nothing | Works when header present |
| **Combination** | "RV 1.33 - Sudas" ✅ | "Passage N" ❌ | Falls back when either is None |
| **LLM Receives** | Clear verse refs | Mixed verse + generic | LLM output format varies |
| **LLM Output** | Uses "RV X.Y" format | Uses "Passage N" format | Trained by input examples |

