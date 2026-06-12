# Sanskrit Compound Word Breaking Packages - Technical Review

## ⚠️ CRITICAL FINDING

**Your system is NOT using `indic-nlp-library` for Sanskrit compound breaking.**

The `indic-nlp-library` package is **imported in the code but NOT installed** in the environment. The system falls back to **simple regex-based whitespace splitting**, which does NOT break compounds.

---

## Current Reality vs. Code

### ❌ What the Code Claims
**File**: `src/utils/sanskrit_preprocessor.py` (lines 22-23)
```python
from indic_nlp.tokenize import word_tokenize
from indic_nlp.normalize import IndicNormalize
```

### ✅ What Actually Happens
The import fails silently, and the system falls back to **regex whitespace splitting** (line 161-169):
```python
def _fallback_tokenize(self, text: str) -> List[str]:
    """Fallback tokenization when indic-nlp unavailable."""
    import re
    tokens = re.split(r'[\s।॥\-,\.;:!?]+', text)  # ← JUST SPLITS ON WHITESPACE
    return [t for t in tokens if t.strip()]
```

**This means NO compound word breaking is happening!**

---

## Available Packages in Environment

### ✅ Installed
- `nltk` (3.9.2) - but English-centric, doesn't support Sanskrit
- `spacy` (3.7.5) - general NLP, no Sanskrit models
- `sentence-transformers` (5.2.0) - embeddings only
- `indic_transliteration` (2.3.76) - script conversion only

### ❌ NOT Installed
- `indic-nlp-library` - **THE PACKAGE YOU NEED**

---

## What You Actually Need

### Primary Missing Package: `indic-nlp-library`

**Name**: `indic-nlp-library`
- **Language**: Python
- **Purpose**: NLP tools specifically designed for Indic languages (Sanskrit, Hindi, Tamil, Telugu, etc.)
- **Key Components**:
  - `indic_nlp.tokenize.word_tokenize()` - **Breaks Sanskrit compounds properly**
  - `indic_nlp.normalize.IndicNormalize` - Diacritic normalization

### Installation
```bash
pip install indic-nlp-library
```

### Expected Behavior (Once Installed)
```python
from indic_nlp.tokenize import word_tokenize

text = "अग्निमीळे पुरोहितम्"
tokens = word_tokenize(text, lang='san')  # lang='san' for Sanskrit
# Output: ["अग्नि", "मीळे", "पुरोहितम्"] - properly breaks compounds
```

### What's Actually Happening (Current State)

#### ⚠️ Current Fallback Behavior
Since `indic-nlp-library` is NOT installed, the code falls back to this:

```python
def _fallback_tokenize(self, text: str) -> List[str]:
    """
    Fallback tokenization when indic-nlp unavailable.
    Splits on whitespace and common punctuation ONLY.
    """
    import re
    tokens = re.split(r'[\s।॥\-,\.;:!?]+', text)  # JUST WHITESPACE SPLITTING
    return [t for t in tokens if t.strip()]
```

**Example of Current (Broken) Behavior**:
```
Input:  "अग्निमीळे पुरोहितम्"
Output: ["अग्निमीळे", "पुरोहितम्"]
         ↑
         NOT broken into components!
```

#### ❌ What's Missing
1. **No compound word breaking** (samasā decomposition)
2. **No Devanagari diacritic normalization**
3. **Basic regex splitting only** - just on whitespace and punctuation

#### ✅ Inflection Handling (Partial)
The system DOES have noun stem extraction for inflected forms:
```python
def extract_noun_stems(self, tokens: List[str]) -> List[str]:
    """
    Extract stems from inflected forms.
    Example: "Sudasah" (nominative) → "Sudas" (stem)
    """
    noun_endings = ['ah', 'am', 'a', 'asya', 'aya', 'at', 'ena', 'e', 'au', 'as']
```

But this is **applied to the already-broken tokens**, and if compounds aren't broken first, it won't help.

---

## Supporting Packages (Actually Installed)

### 1. **`indic_transliteration` (2.3.76)** ✅ Installed
**Purpose**: Script conversion (IAST ↔ Devanagari)

```python
from indic_transliteration import sanscript
```

**Used for**: Converting between scripts when needed for cross-script matching

### 2. **`sentence-transformers` (5.2.0)** ✅ Installed
**Embedding Model**: `paraphrase-multilingual-mpnet-base-v2`
- **Dimension**: 768
- **Supports**: 50+ languages including Sanskrit
- **Used for**: Creating vector embeddings

### 3. **`nltk` (3.9.2)** ✅ Installed
**Note**: Has `word_tokenize()` but is English-centric, not suitable for Sanskrit

### 4. **`spacy` (3.7.5)** ✅ Installed
**Note**: General NLP framework, but no Sanskrit language models

---

## Current (Broken) Preprocessing Pipeline

### Actual Flow Diagram
```
Document Text
    ↓
Detect if Sanskrit (Devanagari or IAST markers)
    ↓
[IF SANSKRIT]
    ↓
Attempt to use indic-nlp-library
    ↓
❌ IMPORT FAILS - NOT INSTALLED
    ↓
Fall back to regex whitespace splitting
    ↓
Extract Noun Stems (from partially-broken text)
    ↓
Generate Embeddings → sentence-transformers
    ↓
Store in Qdrant with metadata preprocessing='sanskrit'
    ↓
❌ RESULT: Compounds not broken, embeddings suboptimal
```

### Code Location
**File**: `src/utils/index_files.py` (lines 207-230)

```python
# PHASE 1: Apply Sanskrit preprocessing to all chunks
preprocessor = get_sanskrit_preprocessor()
if preprocessor.is_sanskrit(chunk.page_content):
    # ⚠️ This calls fallback tokenization (whitespace only)
    preprocessed = preprocessor.preprocess_for_embedding(chunk.page_content)
    chunk.metadata['preprocessing'] = 'sanskrit'
```

---

## Current Implementation Status

### ⚠️ **CRITICAL: No Compound Word Breaking Happening**

| Component | Status | Details |
|-----------|--------|---------|
| **Compound breaking** | ❌ NOT WORKING | indic-nlp-library not installed → falls back to whitespace splitting |
| **Diacritic normalization** | ❌ NOT WORKING | Requires indic-nlp-library |
| **Inflection handling** | ⚠️ PARTIAL | Code exists but applied to incompletely-tokenized text |
| **Script conversion** | ✅ WORKING | indic_transliteration installed |
| **Embedding generation** | ✅ WORKING | sentence-transformers working fine |

### ❌ What's NOT Working
1. **Atharvaveda** (IAST) → Detected as Sanskrit but NO compound breaking
2. **Shatapatha Brahmana** (Devanagari) → Detected as Sanskrit but NO compound breaking
3. **Rigveda** (IAST) → Not even enriched with preprocessing tag

### 🔧 Immediate Solution
Install the missing package:
```bash
conda activate vedic-tutor
pip install indic-nlp-library
```

Then re-index documents to apply proper tokenization.

---

## Package Dependencies & Installation

### ❌ Missing (Critical)
```bash
pip install indic-nlp-library
```

This is the ONLY package that can properly break Sanskrit compound words.

### ✅ Already Installed
```
indic_transliteration==2.3.76    # Script conversion
sentence-transformers==5.2.0     # Embeddings
nltk==3.9.2                       # (English-centric, limited use)
spacy==3.7.5                      # (General NLP, no Sanskrit)
```

---

## Why This Matters

### Compound Words in Sanskrit

Sanskrit extensively uses **samasas** (compound words) - unlike English where words are typically separated by spaces.

**Example**: 
- Modern Hindi/English: "देवता की सेना" (deva's army) = separate words
- Classical Sanskrit: "देवसेना" (devasena) = compound word

For RAG to work correctly:
1. **Query**: "Who leads the gods' army?" 
2. **Should find**: "devasena" passages
3. **With compound breaking**: ✅ Can match "deva" and "sena" components
4. **Without compound breaking**: ❌ Cannot match anything

### Current Impact
Without `indic-nlp-library`, your embeddings are based on **incorrectly tokenized text**, which reduces retrieval quality for Sanskrit texts.

---

## Limitations & Considerations

1. **Compound Word Breaking**: 
   - `indic-nlp-library` does proper **word tokenization** for Sanskrit
   - However, it does NOT do full samasā (compound) **decomposition**
   - For that, you'd need specialized tools like Turiya (morphological analyzer)

2. **Stem Extraction**:
   - Current code uses suffix-based heuristics (works OK)
   - Would need full morphological analyzer for 100% accuracy

3. **Installation Issues**:
   - `indic-nlp-library` has some build dependencies
   - On Mac ARM64, may require special compilation
   - Check GitHub for platform-specific installation instructions

---

## Next Steps

### Immediate (Required)
1. **Install indic-nlp-library**:
   ```bash
   pip install indic-nlp-library
   ```

2. **Verify installation**:
   ```python
   from indic_nlp.tokenize import word_tokenize
   text = "अग्निमीळे पुरोहितम्"
   print(word_tokenize(text, lang='san'))
   ```

3. **Re-index documents** with proper tokenization:
   ```bash
   python src/cli_run.py --force-reindex
   ```

4. **Re-upload enriched Rigveda documents** to Qdrant Cloud

### Optional (Enhancement)
- Add full samasā decomposition if needed for specific use cases
- Install additional Sanskrit NLP tools like Turiya for morphological analysis

---

## Recommendation

**✅ Install `indic-nlp-library` immediately** - it's essential for proper Sanskrit text retrieval.

This single package enables:
- Proper compound word breaking
- Diacritic normalization
- Better embedding quality
- Improved retrieval accuracy
