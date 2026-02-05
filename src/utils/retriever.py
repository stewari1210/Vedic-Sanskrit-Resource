from src.helper import logger
from src.config import RETRIEVAL_K, SEMANTIC_WEIGHT, KEYWORD_WEIGHT, EXPANSION_DOCS
from typing import List, Optional, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
import re
from src.utils.proper_noun_variants import (
    get_proper_noun_variants,
    disambiguate_proper_noun,
    get_confederation_for_tribe,
    get_constituent_tribes
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Import MW Concept Store and Transliteration for bilingual support
try:
    from src.utils.mw_concept_store import MWConceptStore
    from src.utils.transliteration import TransliterationHelper
    MW_ENABLED = True
except ImportError as e:
    logger.warning(f"MW Concept Store not available: {e}")
    MW_ENABLED = False

# Import parallelization settings
try:
    from config_parallel import RETRIEVAL_PARALLEL_QUERIES, RETRIEVAL_MAX_WORKERS
    PARALLEL_ENABLED = True
except ImportError:
    RETRIEVAL_PARALLEL_QUERIES = False
    RETRIEVAL_MAX_WORKERS = 1
    PARALLEL_ENABLED = False


class HybridRetriever(BaseRetriever):
    """Custom hybrid retriever that combines semantic and keyword search.

    Retrieves from BOTH:
    - Semantic search (Qdrant): Good for conceptual queries, relationships, meanings
    - Keyword search (BM25): Good for exact matches like hymn numbers, specific phrases

    Then merges and deduplicates results, prioritizing exact keyword matches.
    
    Now enhanced with MW Concept Store for bilingual Sanskrit/Hindi support:
    - Transliteration bridging (Devanagari ↔ IAST)
    - Semantic expansion (definitions → related terms)
    - Vedic text grounding (RV/YV/AV references)
    """

    semantic_retriever: BaseRetriever
    keyword_retriever: BaseRetriever
    k: int = 10
    mw_store: Optional[Any] = None
    trans_helper: Optional[Any] = None
    
    def __init__(self, **kwargs):
        """Initialize with MW Concept Store if available."""
        super().__init__(**kwargs)
        
        # Initialize MW Concept Store for bilingual support
        if MW_ENABLED:
            try:
                self.mw_store = MWConceptStore()
                self.trans_helper = TransliterationHelper()
                logger.info("✅ MW Concept Store and Transliteration enabled for bilingual queries")
            except Exception as e:
                logger.warning(f"Failed to initialize MW Concept Store: {e}")
                self.mw_store = None
                self.trans_helper = None
        else:
            self.mw_store = None
            self.trans_helper = None
    
    def _is_english_query(self, query: str) -> bool:
        """
        Detect if query is primarily in English (vs Sanskrit/Hindi/Devanagari).
        
        Returns:
            True if query is English, False if Sanskrit/Hindi/Devanagari
        """
        # Check for Devanagari characters
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in query)
        if has_devanagari:
            return False
        
        # Check for IAST diacritics (ā, ī, ū, ṛ, ṃ, ḥ, ś, ṣ, ṭ, ḍ, ṅ, ñ)
        iast_chars = set('āīūṛṝḷḹṃḥśṣṭḍṅñ')
        has_iast = any(char in iast_chars for char in query.lower())
        if has_iast:
            return False  # Likely Sanskrit transliteration
        
        # Common English question words (strong signal)
        english_words = {'who', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were', 
                        'the', 'a', 'an', 'in', 'on', 'at', 'of', 'for', 'to', 'from',
                        'explain', 'describe', 'tell', 'summarize', 'which', 'verses', 'talk', 'about'}
        
        words = query.lower().split()
        english_count = sum(1 for word in words if word.strip('?.,!;:') in english_words)
        
        # If >50% of words are common English words, it's an English query
        if len(words) > 0 and english_count / len(words) > 0.5:
            return True
        
        # Default: assume English for queries without Devanagari or IAST
        return True
    
    def _enhance_query_with_mw(self, query: str) -> tuple[str, list, list]:
        """
        Enhance query using MW Concept Store for bilingual support.
        
        **Only applied to Sanskrit/Hindi/Devanagari queries, NOT pure English queries.**
        
        Returns:
            tuple: (enhanced_query, transliteration_variants, mw_context)
        
        Example:
            Query: "अग्नि पूजा" 
            → Enhanced: "अग्नि पूजा fire sacrificial god Agni puja"
            → Variants: ["Agni pūjā", "agni puja", "अग्नि पूजा"]
            → MW Context: [{"primary_key": "agni", "definitions": [...], "vedic_refs": [...]}]
        """
        if not self.mw_store or not self.trans_helper:
            logger.info(f"MW: Skipping - MW store or transliteration helper not available")
            return query, [query], []
        
        # CRITICAL: Skip MW expansion for pure English queries
        is_english = self._is_english_query(query)
        logger.info(f"MW: Language detection for '{query}' → is_english={is_english}")
        
        if is_english:
            logger.info(f"MW: ✅ Skipping expansion - detected English query")
            return query, [query], []
        
        logger.info(f"MW: ❌ Detected non-English query - applying bilingual expansion")
        
        # Step 1: Generate transliteration variants
        transliteration_variants = self.trans_helper.normalize_query(query)
        logger.info(f"MW: Generated {len(transliteration_variants)} transliteration variants")
        
        # Step 2: Lookup Sanskrit terms in MW
        # For Devanagari queries, lookup using IAST variants (MW uses IAST keys)
        mw_results = []
        
        # Try all transliteration variants for MW lookup
        all_words = set()
        for variant in transliteration_variants[:3]:  # Use top 3 variants
            all_words.update(variant.split())
        
        for word in all_words:
            if len(word) < 3:  # Skip very short words
                continue
            
            result = self.mw_store.lookup(word)
            if result and result.get('found'):
                mw_results.append(result)
                logger.info(f"MW: Found '{word}' → '{result['primary_key']}' with {len(result.get('definitions', []))} definitions")
        
        # Step 3: Expand query with MW definitions
        # Use the first IAST variant for expansion (most readable)
        query_for_expansion = transliteration_variants[0] if len(transliteration_variants) > 1 else query
        enhanced_query = self.mw_store.expand_query(query_for_expansion) if mw_results else query_for_expansion
        
        # Add synonym expansion for key Vedic terms
        # This helps bridge semantic gaps (e.g., vināśana → collapsed, bendings)
        VEDIC_SYNONYMS = {
            'vinasana': 'disappearance vanishing collapsed ending destruction bendings sustain propped sun gods',
            'vināśana': 'disappearance vanishing collapsed ending destruction bendings sustain propped sun gods',
            'sarasvati': 'river goddess stream water flow',
            'sarasvatī': 'river goddess stream water flow'
        }
        
        # Special case: Sarasvati + Vinasana together = Pancavimsa Brahmana passage
        query_lower = enhanced_query.lower()
        if ('sarasvat' in query_lower and ('vinasana' in query_lower or 'vināśana' in query_lower)):
            # Add very specific terms from the Pancavimsa passage
            enhanced_query += " Pancavimsa Brahmana collapsed sustain sun gods propped bendings river"
            logger.info("MW: Detected Sarasvati+Vinasana query - adding Pancavimsa-specific terms")
        
        for term, synonyms in VEDIC_SYNONYMS.items():
            if term in query_lower:
                enhanced_query += f" {synonyms}"
                logger.info(f"MW: Added synonyms for '{term}': {synonyms}")
        
        if enhanced_query != query:
            logger.info(f"MW: Query expanded from '{query}' to '{enhanced_query[:150]}...'")
        
        return enhanced_query, transliteration_variants, mw_results
    
    def _attach_mw_context_to_docs(self, docs: List[Document], mw_results: list) -> List[Document]:
        """
        Attach MW context to retrieved documents for display in UI.
        
        This adds MW dictionary definitions and Vedic references to document metadata
        so the Streamlit UI can display them alongside retrieval results.
        """
        if not mw_results:
            return docs
        
        for doc in docs:
            if 'mw_context' not in doc.metadata:
                doc.metadata['mw_context'] = mw_results
        
        logger.info(f"MW: Attached MW context ({len(mw_results)} entries) to {len(docs)} documents")
        return docs

    def _get_transliteration_variants(self, word: str) -> List[str]:
        """Get transliteration variants for Sanskrit/Vedic proper nouns.

        Now uses comprehensive ProperNounVariantManager with data from:
        - Rigveda-Sharma (1,028 Suktas, 31,593 proper nouns)
        - Griffith-Rigveda (943 hymns, 4,473 proper nouns)
        - Yajurveda-Sharma (1,830 verses, 6,661 proper nouns)
        - Griffith-Yajurveda (296 sections, 979 proper nouns)

        Total: 43,706 proper noun references across 4 translations
        """
        variants = [word]  # Always include original

        # Get comprehensive variants from database (includes all 4 translations)
        db_variants = get_proper_noun_variants(word)
        if db_variants:
            variants.extend(db_variants)
            logger.info(f"HybridRetriever: Found {len(db_variants)} database variants for '{word}': {db_variants}")
        else:
            # Fallback: Try common suffix patterns if not in database
            # Pattern-based variants (final 's' vs 'sa')
            if word.endswith('as'):
                variants.append(word + 'a')  # Sudas → Sudasa
            elif word.endswith('asa'):
                variants.append(word[:-1])  # Sudasa → Sudas

            # sh ↔ s pattern (Sharma vs Griffith)
            if 'sh' in word.lower():
                variants.append(word.replace('sh', 's').replace('Sh', 'S'))
            elif 's' in word.lower() and 'sh' not in word.lower():
                variants.append(word.replace('s', 'sh').replace('S', 'Sh'))

        return list(set(variants))  # Remove duplicates

    def _extract_proper_nouns(self, text: str) -> List[str]:
        """Extract proper nouns from query using heuristics.

        Targets: Names of people, places, tribes (Pakthas, Sudas, Vashistha, etc.)
        Excludes: Common words, question words, prepositions, generic nouns
        """
        # Comprehensive blacklist of common English words that get capitalized
        common_words = {
            # Question words
            'What', 'When', 'Where', 'Which', 'Who', 'Whom', 'Whose', 'Why', 'How',
            # Pronouns
            'I', 'You', 'He', 'She', 'It', 'We', 'They', 'This', 'That', 'These', 'Those',
            # Conjunctions
            'And', 'But', 'Or', 'Nor', 'For', 'Yet', 'So', 'If', 'Then', 'Because',
            # Prepositions
            'In', 'On', 'At', 'By', 'For', 'With', 'From', 'To', 'Of', 'Into', 'Through', 'During', 'Before', 'After', 'Above', 'Below', 'Between', 'Among',
            # Articles
            'The', 'A', 'An',
            # Common verbs (past participle often capitalized)
            'Is', 'Are', 'Was', 'Were', 'Be', 'Been', 'Being', 'Have', 'Has', 'Had', 'Do', 'Does', 'Did', 'Will', 'Would', 'Could', 'Should', 'May', 'Might', 'Must', 'Can',
            # Generic nouns that might appear capitalized
            'War', 'Wars', 'Battle', 'Battles', 'King', 'Kings', 'Queen', 'Queens', 'Hymn', 'Hymns', 'Book', 'Books', 'Chapter', 'Chapters',
            'Ten', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Hundred', 'Thousand',
            # Question starters
            'Tell', 'Explain', 'Describe', 'Name', 'List', 'Give', 'Show', 'Find',
            # Determiners
            'All', 'Some', 'Any', 'Each', 'Every', 'Both', 'Either', 'Neither', 'Many', 'Few', 'Several',
            # Modal auxiliaries
            'Shall', 'Should', 'Will', 'Would', 'Can', 'Could', 'May', 'Might', 'Must',
        }

        words = text.split()
        proper_nouns = []
        seen = set()  # Deduplicate

        for i, word in enumerate(words):
            # Skip first word (sentence start capitalization)
            if i == 0:
                continue

            # Remove punctuation from word
            clean_word = re.sub(r'[^\w]', '', word)

            # Must start with uppercase and be at least 3 characters
            if not clean_word or len(clean_word) < 3 or not clean_word[0].isupper():
                continue

            # Skip if it's a common word
            if clean_word in common_words:
                continue

            # Skip if it's all uppercase (likely acronym or emphasis, not a name)
            if clean_word.isupper():
                continue

            # Skip if already seen
            if clean_word in seen:
                continue

            # Likely a proper noun (person, place, tribe name)
            proper_nouns.append(clean_word)
            seen.add(clean_word)

        return proper_nouns

    def _disambiguate_proper_noun(self, noun: str, query: str) -> str:
        """Apply context-based disambiguation for homonyms.

        Examples:
        - "Bharata" + "battle" context → "Bharata (tribe)"
        - "Bharata" + "sage/hymn" context → "Bharata (sage)"
        - "Puru" + "battle/enemy" context → "Puru (tribe)"
        - "Purusha" + "cosmic/creation" context → "Purusha (Cosmic Being)"
        """
        # disambiguate_proper_noun returns a tuple (form, role)
        disambiguated_form, role = disambiguate_proper_noun(noun, query)

        # Only log if disambiguation changed the form
        if disambiguated_form != noun:
            logger.info(f"HybridRetriever: Disambiguated '{noun}' → '{disambiguated_form}' (role: {role}) based on context: '{query}'")

        return disambiguated_form

    def _detect_source_text_filter(self, query: str) -> tuple[list[str], bool]:
        """Detect if query mentions specific source texts and should filter results.

        Returns:
            tuple: (list of source identifiers, whether to apply strict filtering)

        Examples:
            "What is X in Rigveda?" -> (['rigveda'], True)
            "Compare X in Rigveda and Yajurveda" -> (['rigveda', 'yajurveda'], False)
            "Tell me about X" -> ([], False)
        """
        query_lower = query.lower()

        # Define source text identifiers and their variations
        source_mapping = {
            'rigveda': ['rigveda', 'rig veda', 'rig-veda', 'rgveda'],
            'yajurveda': ['yajurveda', 'yajur veda', 'yajur-veda'],
            'griffith-rigveda': ['griffith rigveda', 'griffith\'s rigveda', 'griffith rig veda'],
            'griffith-yajurveda': ['griffith yajurveda', 'griffith\'s yajurveda', 'griffith yajur veda'],
        }

        detected_sources = []

        # Check for each source
        for source_key, variations in source_mapping.items():
            for variation in variations:
                if variation in query_lower:
                    # Determine the base source (rigveda or yajurveda)
                    if 'rigveda' in source_key or 'rig' in source_key:
                        if 'rigveda' not in detected_sources:
                            detected_sources.append('rigveda')
                    elif 'yajurveda' in source_key or 'yajur' in source_key:
                        if 'yajurveda' not in detected_sources:
                            detected_sources.append('yajurveda')
                    break

        # Determine if strict filtering (only one source mentioned)
        # NOTE: Using balanced mode by default to allow proper noun expansion to work
        # Strict mode can filter out all docs before expansion completes
        strict_filter = False  # Always use balanced mode for now

        # Check for comparative queries (both texts mentioned)
        comparative_keywords = ['both', 'compare', 'comparison', 'versus', 'vs', 'and', 'between']
        is_comparative = any(keyword in query_lower for keyword in comparative_keywords)

        # If comparative, ensure balanced retrieval (not strict)
        if is_comparative and len(detected_sources) > 1:
            strict_filter = False

        if detected_sources:
            filter_type = "strict (single source)" if strict_filter else "balanced (multiple sources)"
            logger.info(f"HybridRetriever: Detected source filter: {detected_sources} ({filter_type})")

        return detected_sources, strict_filter

    def _filter_docs_by_source(self, docs: List[Document], source_filters: list[str], strict: bool) -> List[Document]:
        """Filter documents based on source text.

        Args:
            docs: Documents to filter
            source_filters: List of source identifiers ('rigveda', 'yajurveda')
            strict: If True, only return docs from specified sources. If False, boost them.

        Returns:
            Filtered/reordered documents
        """
        if not source_filters:
            return docs

        matching_docs = []
        non_matching_docs = []

        for doc in docs:
            filename = doc.metadata.get('filename', '').lower()
            title = doc.metadata.get('title', '').lower()
            source = doc.metadata.get('source', '').lower()

            # Check if document matches any of the source filters (check filename, title, and source fields)
            matches = any(
                (filt in filename) or (filt in title) or (filt in source)
                for filt in source_filters
            )

            if matches:
                matching_docs.append(doc)
            else:
                non_matching_docs.append(doc)

        if strict:
            # Strict mode: only return matching docs
            logger.info(f"HybridRetriever: Strict filter applied - {len(matching_docs)} docs match {source_filters}, {len(non_matching_docs)} filtered out")
            return matching_docs
        else:
            # Balanced mode: matching docs first, then others
            logger.info(f"HybridRetriever: Balanced filter - {len(matching_docs)} docs from {source_filters} prioritized, {len(non_matching_docs)} others included")
            return matching_docs + non_matching_docs

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """Get relevant documents from both retrievers and merge."""

        logger.info(f"HybridRetriever: Query = '{query}'")
        
        # PHASE 1: SANSKRIT PREPROCESSING (NEW)
        # Apply Sanskrit-specific preprocessing to improve matching of inflected forms
        # This handles cases like "Sudas" matching "Sudasah", "Sudasam", "Sudasya"
        try:
            from src.utils.sanskrit_preprocessor import get_sanskrit_preprocessor
            preprocessor = get_sanskrit_preprocessor()
            
            if preprocessor.is_sanskrit(query):
                # For Sanskrit queries, apply stem extraction to match inflected forms
                preprocessed_query = preprocessor.preprocess_query(query)
                logger.info(f"🔤 Sanskrit detected: Preprocessing query '{query}' → '{preprocessed_query}'")
                # Don't replace query yet - use it as variant for retrieval
                # Will be added to variant search below
            else:
                preprocessed_query = None
                logger.debug(f"🔤 Non-Sanskrit query detected, skipping Sanskrit preprocessing")
        except ImportError:
            preprocessed_query = None
            logger.debug("Sanskrit preprocessor not available")
        except Exception as e:
            preprocessed_query = None
            logger.warning(f"Error applying Sanskrit preprocessing: {e}")
        
        # STEP 0: MW CONCEPT STORE ENHANCEMENT (if available)
        enhanced_query = query
        transliteration_variants = []
        mw_context = []
        
        if self.mw_store and self.trans_helper:
            enhanced_query, transliteration_variants, mw_context = self._enhance_query_with_mw(query)
            
            if mw_context:
                logger.info(f"MW: Found {len(mw_context)} Sanskrit terms in MW dictionary")
                # Log Vedic references for ranking boost
                all_vedic_refs = set()
                for mw_entry in mw_context:
                    all_vedic_refs.update(mw_entry.get('vedic_refs', []))
                if all_vedic_refs:
                    logger.info(f"MW: Vedic references for boosting: {list(all_vedic_refs)[:5]}")

        # Detect source text filters (Rigveda, Yajurveda, etc.)
        source_filters, strict_filter = self._detect_source_text_filter(query)

        # Extract keywords for BM25 (remove action words like "summarize", "explain", etc.)
        # This helps BM25 match on the actual content patterns like hymn numbers or specific terms
        import re
        import unicodedata
        
        # Detect if query is in Devanagari script
        # Devanagari Unicode range: 0900-097F
        is_devanagari = any('\u0900' <= char <= '\u097F' for char in query)
        
        # Keep hymn references, numbers in brackets, and important nouns
        keyword_query = re.sub(r'\b(summarize|explain|describe|tell|about|what|who|when|where|why|how|is|are|the|a|an|in|on|at|for)\b', '', query, flags=re.IGNORECASE)
        keyword_query = keyword_query.strip()

        # Strip diacritical marks ONLY for Latin scripts (IAST), NOT for Devanagari
        # For Devanagari: Preserve all characters (vowel marks are essential, not diacritics)
        # For Latin/IAST: Remove diacritics (e.g., Sūdaḥ → Sudas, ā → a)
        if is_devanagari:
            # Devanagari: Use query as-is (BM25 will match exact Devanagari text)
            keyword_query_normalized = keyword_query
            logger.info(f"🔤 Devanagari detected: Preserving original script for BM25")
        else:
            # Latin/IAST: Strip diacritical marks to match transliteration variants
            keyword_query_normalized = unicodedata.normalize('NFD', keyword_query)
            keyword_query_normalized = ''.join(char for char in keyword_query_normalized if unicodedata.category(char) != 'Mn')
            
            # Remove punctuation except hyphens and brackets (keep hymn references intact)
            keyword_query_normalized = re.sub(r'[^\w\s\[\]\-]', '', keyword_query_normalized)
            keyword_query_normalized = keyword_query_normalized.strip()
            logger.info(f"🔤 Latin script detected: Normalized diacritics for BM25")

        # If we stripped too much, fall back to original query
        if len(keyword_query_normalized) < 2:
            keyword_query_normalized = query

        logger.info(f"HybridRetriever: Keyword query for BM25 = '{keyword_query_normalized}'")

        # Get results from both retrievers - WITH PARALLELIZATION
        if PARALLEL_ENABLED and RETRIEVAL_PARALLEL_QUERIES:
            logger.info(f"🚀 HybridRetriever: Using parallel retrieval with {RETRIEVAL_MAX_WORKERS} workers")
            start_time = time.time()

            # If we have transliteration variants or preprocessed Sanskrit query, search them too
            all_variants = transliteration_variants[:3] if transliteration_variants else []
            if preprocessed_query and preprocessed_query not in all_variants:
                all_variants.insert(0, preprocessed_query)  # Add preprocessed form at the start
            
            if all_variants and len(all_variants) > 0:
                logger.info(f"🌐 Searching {len(all_variants)} query variants in parallel (MW variants + Sanskrit preprocessing)")
                
                # Execute semantic retrieval for ALL variants in parallel
                with ThreadPoolExecutor(max_workers=min(len(all_variants) + 1, 5)) as executor:
                    # Submit keyword retrieval
                    keyword_future = executor.submit(self.keyword_retriever.invoke, keyword_query_normalized)
                    
                    # Submit semantic retrieval for all variants
                    variant_futures = [
                        executor.submit(self.semantic_retriever.invoke, variant)
                        for variant in all_variants
                    ]
                    
                    # Also search enhanced query (with MW definitions)
                    enhanced_future = executor.submit(self.semantic_retriever.invoke, enhanced_query)
                    
                    # Collect all results
                    keyword_docs = keyword_future.result()
                    variant_results = [f.result() for f in variant_futures]
                    enhanced_docs = enhanced_future.result()
                    
                    # Merge all semantic results, deduplicating by page_content
                    seen_content = set()
                    semantic_docs = []
                    
                    # Prioritize enhanced query results first
                    for doc in enhanced_docs:
                        content_hash = hash(doc.page_content[:200])
                        if content_hash not in seen_content:
                            semantic_docs.append(doc)
                            seen_content.add(content_hash)
                    
                    # Then add variant results (including preprocessed Sanskrit form)
                    for variant_docs in variant_results:
                        for doc in variant_docs:
                            content_hash = hash(doc.page_content[:200])
                            if content_hash not in seen_content:
                                semantic_docs.append(doc)
                                seen_content.add(content_hash)
                                if len(semantic_docs) >= self.k * 2:  # Limit total results
                                    break
                
                logger.info(f"🌐 Merged results from {len(all_variants)} variants → {len(semantic_docs)} unique docs")
            else:
                # Standard parallel retrieval without variants
                with ThreadPoolExecutor(max_workers=2) as executor:
                    keyword_future = executor.submit(self.keyword_retriever.invoke, keyword_query_normalized)
                    semantic_future = executor.submit(self.semantic_retriever.invoke, enhanced_query)
                    
                    keyword_docs = keyword_future.result()
                    semantic_docs = semantic_future.result()

            elapsed = time.time() - start_time
            logger.info(f"⚡ Parallel retrieval completed in {elapsed:.2f}s")
        else:
            # Sequential retrieval
            all_variants = transliteration_variants[:3] if transliteration_variants else []
            if preprocessed_query and preprocessed_query not in all_variants:
                all_variants.insert(0, preprocessed_query)  # Add preprocessed form at the start
            
            if all_variants and len(all_variants) > 0:
                logger.info(f"🌐 Searching {len(all_variants)} query variants sequentially (MW variants + Sanskrit preprocessing)")
                
                # Search all variants
                all_semantic_docs = []
                seen_content = set()
                
                # Search enhanced query first
                enhanced_docs = self.semantic_retriever.invoke(enhanced_query)
                for doc in enhanced_docs:
                    content_hash = hash(doc.page_content[:200])
                    if content_hash not in seen_content:
                        all_semantic_docs.append(doc)
                        seen_content.add(content_hash)
                
                # Then search variants (including preprocessed Sanskrit form)
                for variant in all_variants:
                    variant_docs = self.semantic_retriever.invoke(variant)
                    for doc in variant_docs:
                        content_hash = hash(doc.page_content[:200])
                        if content_hash not in seen_content:
                            all_semantic_docs.append(doc)
                            seen_content.add(content_hash)
                            if len(all_semantic_docs) >= self.k * 2:
                                break
                
                semantic_docs = all_semantic_docs
                logger.info(f"🌐 Merged results from {len(all_variants)} variants → {len(semantic_docs)} unique docs")
            else:
                semantic_docs = self.semantic_retriever.invoke(enhanced_query)
            
            keyword_docs = self.keyword_retriever.invoke(keyword_query_normalized)


        logger.info(f"HybridRetriever: BM25 returned {len(keyword_docs)} docs, Qdrant returned {len(semantic_docs)} docs")
        if keyword_docs:
            preview = keyword_docs[0].page_content[:100].replace('\n', ' ')
            logger.info(f"HybridRetriever: BM25 top result: {preview}...")
        if keyword_docs and len(keyword_docs) > 1:
            preview2 = keyword_docs[1].page_content[:100].replace('\n', ' ')
            logger.info(f"HybridRetriever: BM25 #2 result: {preview2}...")

        # Merge with WEIGHTED scoring: Semantic + Keyword
        # SEMANTIC_WEIGHT (default 70%): Prioritizes conceptual understanding (e.g., "Vashistha" associated with "Sudas")
        # KEYWORD_WEIGHT (default 30%): Boosts exact matches (e.g., specific hymn numbers, exact phrases)
        seen_content = {}
        doc_scores = {}

        # Score semantic results
        for i, doc in enumerate(semantic_docs):
            content_hash = hash(doc.page_content)
            # Higher position = higher score (inverse rank)
            score = (len(semantic_docs) - i) * SEMANTIC_WEIGHT
            seen_content[content_hash] = doc
            doc_scores[content_hash] = score

        # Score keyword results (boosts if already in semantic)
        for i, doc in enumerate(keyword_docs):
            content_hash = hash(doc.page_content)
            score = (len(keyword_docs) - i) * KEYWORD_WEIGHT

            if content_hash in doc_scores:
                # Document appears in BOTH - boost it significantly
                doc_scores[content_hash] += score * 2  # Double the keyword boost
            else:
                # Keyword-only result (rare, but possible for exact matches)
                seen_content[content_hash] = doc
                doc_scores[content_hash] = score

        # Sort by combined score (highest first)
        sorted_hashes = sorted(doc_scores.keys(), key=lambda h: doc_scores[h], reverse=True)
        merged_docs = [seen_content[h] for h in sorted_hashes]

        # PRIORITIZE SANSKRIT ORIGINAL SOURCES over English translations
        # Sanskrit Sharma texts contain original Vedic verses with more explicit relationships
        # English Griffith translations may omit or generalize genealogical details
        logger.info("🔍 Checking for Sanskrit vs English sources to apply prioritization")
        
        for content_hash in doc_scores:
            doc = seen_content[content_hash]
            filename = doc.metadata.get('filename', '').lower()
            source = doc.metadata.get('source', '').lower()
            title = doc.metadata.get('title', '').lower()
            creator = doc.metadata.get('creator', '').lower()
            preprocessing = doc.metadata.get('preprocessing', '').lower()
            keywords = str(doc.metadata.get('keywords', '')).lower()
            
            # Detect Sanskrit/original sources (Sharma, original text markers, preprocessing field)
            is_sanskrit_source = (
                preprocessing == 'sanskrit' or  # Direct marker from indexing
                any(indicator in filename or indicator in source or indicator in title or indicator in creator
                    for indicator in ['sharma', 'sanskrit', 'original', 'devanagari', 'sanskritdocuments']) or
                'sanskrit' in keywords  # Check keywords array for Sanskrit marker
            )
            
            # Detect English translation sources (Griffith, translation markers)
            is_english_translation = any(indicator in filename or indicator in source or indicator in title
                                         for indicator in ['griffith', 'translation', 'english'])
            
            # BOOST Sanskrit sources significantly (2.5x multiplier)
            if is_sanskrit_source and not is_english_translation:
                old_score = doc_scores[content_hash]
                doc_scores[content_hash] *= 2.5
                logger.info(f"✨ SANSKRIT SOURCE BOOST: {title[:60] if title else filename[:60]} "
                           f"(preprocessing={preprocessing}, score {old_score:.1f} → {doc_scores[content_hash]:.1f})")
            
            # DOWNRANK English translations when Sanskrit available (0.6x multiplier)
            elif is_english_translation and not is_sanskrit_source:
                old_score = doc_scores[content_hash]
                doc_scores[content_hash] *= 0.6
                logger.info(f"⬇️  English translation downranked: {title[:60] if title else filename[:60]} "
                           f"(score {old_score:.1f} → {doc_scores[content_hash]:.1f})")
        
        # Re-sort after Sanskrit prioritization
        sorted_hashes = sorted(doc_scores.keys(), key=lambda h: doc_scores[h], reverse=True)
        merged_docs = [seen_content[h] for h in sorted_hashes]
        
        top_title = merged_docs[0].metadata.get('title', 'unknown') if merged_docs else 'none'
        top_preprocessing = merged_docs[0].metadata.get('preprocessing', 'unknown') if merged_docs else 'none'
        logger.info(f"📊 After Sanskrit prioritization: Top source = {top_title} (preprocessing={top_preprocessing})")

        # BOOST PRIMARY SOURCES based on proper noun database
        # Extract proper nouns to determine primary source
        proper_nouns = self._extract_proper_nouns(query)
        
        if proper_nouns:
            from src.utils.proper_noun_variants import get_proper_noun_context
            
            # Check each proper noun for source priority
            primary_sources = set()
            for noun in proper_nouns:
                metadata = get_proper_noun_context(noun)
                if metadata and 'sources' in metadata:
                    sources = metadata['sources']
                    # sources is a list of source names
                    if sources:
                        # Extract primary source names from the list
                        for source_name in sources:
                            # Map to filename patterns
                            if 'Rigveda' in source_name:
                                primary_sources.add('rigveda')
                            elif 'Yajurveda' in source_name:
                                primary_sources.add('yajurveda')
                            elif 'Ramayana' in source_name:
                                primary_sources.add('ramayana')
            
            if primary_sources:
                logger.info(f"🎯 Detected proper nouns {proper_nouns} - boosting primary sources: {primary_sources}")
                
                # Boost documents from primary sources, downrank footnotes/commentaries
                for content_hash in doc_scores:
                    doc = seen_content[content_hash]
                    filename = doc.metadata.get('filename', '').lower()
                    source = doc.metadata.get('source', '').lower()
                    title = doc.metadata.get('title', '').lower()
                    
                    # Check if this is from a primary source (check filename, source, AND title)
                    is_primary = any((ps in filename) or (ps in source) or (ps in title) for ps in primary_sources)
                    
                    # Check if this is a commentary/footnote (Brahmana, unless specifically requested)
                    is_commentary = any(term in filename or term in source or term in title
                                      for term in ['brahmana', 'commentary', 'footnote'])
                    
                    if is_primary and not is_commentary:
                        # Boost primary source documents
                        old_score = doc_scores[content_hash]
                        doc_scores[content_hash] *= 2.0
                        logger.info(f"🎯 Boosted primary source: {title[:50]} (score {old_score:.1f} → {doc_scores[content_hash]:.1f})")
                    elif is_commentary and not is_primary:
                        # Downrank commentaries when primary sources available
                        old_score = doc_scores[content_hash]
                        doc_scores[content_hash] *= 0.5
                        logger.info(f"⬇️  Downranked commentary: {title[:50]} (score {old_score:.1f} → {doc_scores[content_hash]:.1f})")
                
                # Re-sort after boosting
                sorted_hashes = sorted(doc_scores.keys(), key=lambda h: doc_scores[h], reverse=True)
                merged_docs = [seen_content[h] for h in sorted_hashes]

        # BOOST SPECIFIC SOURCES based on query keywords
        # If Sarasvati + disappearance/vinasana mentioned, boost Pancavimsa Brahmana
        query_lower = query.lower()
        if 'sarasvat' in query_lower and any(term in query_lower for term in ['vinasana', 'vināśana', 'disappear', 'destruction', 'विनाशन']):
            logger.info("🎯 Detected Sarasvati disappearance query - boosting Pancavimsa Brahmana sources")
            
            # Re-score to boost Pancavimsa sources
            for content_hash in doc_scores:
                doc = seen_content[content_hash]
                source = doc.metadata.get('source', '').lower()
                title = doc.metadata.get('title', '').lower()
                
                # Check both source and title fields for Pancavimsa/Pancavamsa
                if 'pancavimsa' in source or 'pancavamsa' in source or 'pancavimsa' in title or 'pancavamsa' in title:
                    # Significantly boost Pancavimsa sources
                    old_score = doc_scores[content_hash]
                    doc_scores[content_hash] *= 3.0
                    logger.info(f"🎯 Boosted Pancavimsa document: {title if title else source} (score {old_score:.1f} → {doc_scores[content_hash]:.1f})")
            
            # Re-sort after boosting
            sorted_hashes = sorted(doc_scores.keys(), key=lambda h: doc_scores[h], reverse=True)
            merged_docs = [seen_content[h] for h in sorted_hashes]

        logger.info(f"HybridRetriever: Merged to {len(merged_docs)} unique docs, returning top {self.k}")
        if merged_docs and len(merged_docs) > 0:
            top_score = doc_scores[sorted_hashes[0]]
            top_source = merged_docs[0].metadata.get('source', 'unknown')
            logger.info(f"HybridRetriever: Top doc score={top_score:.2f} source={top_source} (semantic {SEMANTIC_WEIGHT:.0%}, keyword {KEYWORD_WEIGHT:.0%})")

        # APPLY SOURCE TEXT FILTERING (if specific texts mentioned in query)
        if source_filters:
            merged_docs = self._filter_docs_by_source(merged_docs, source_filters, strict_filter)

        # QUERY EXPANSION: Add documents related to proper nouns in the query
        if EXPANSION_DOCS > 0:
            proper_nouns = self._extract_proper_nouns(query)

            # Apply context-based disambiguation for homonyms
            # Example: "Bharata in battle" → searches for Bharata tribe, not sage
            # NOTE: We keep BOTH original and disambiguated for proper variant lookup
            proper_nouns_disambiguated = []
            for noun in proper_nouns:
                disambiguated_form, role = disambiguate_proper_noun(noun, query)
                # Only log if disambiguation changed the form
                if disambiguated_form != noun:
                    logger.info(f"HybridRetriever: Disambiguated '{noun}' → '{disambiguated_form}' (role: {role}) based on context: '{query}'")
                # Store tuple of (original, disambiguated, role) for later use
                proper_nouns_disambiguated.append((noun, disambiguated_form, role))

            # Log disambiguation results (for the old format logs)
            for original, disambiguated, role in proper_nouns_disambiguated:
                if original != disambiguated:
                    logger.info(f"HybridRetriever: Query expansion using '{disambiguated}' instead of '{original}'")            # LOCATION-AWARE EXPANSION: Detect queries about geographic locations
            # Triggers for: "where", "which river", "cross", "location", "place", "dwell", "live"
            location_keywords = ['where', 'location', 'place', 'river', 'rivers', 'cross', 'crossed', 'crossing',
                               'dwell', 'dwelling', 'lived', 'live', 'settled', 'settlement', 'bank', 'banks']
            is_location_query = any(word in query.lower() for word in location_keywords)

            # TRIBAL EXPANSION: Detect queries about tribes, enemies, allies in Ten Kings battle
            # Triggers for: "tribes", "enemies", "allies", "fought with", "fought against", "ten kings"
            tribal_keywords = ['tribe', 'tribes', 'enemy', 'enemies', 'ally', 'allies', 'fought with', 'fought against',
                             'confederat', 'coalition', 'ten kings']
            is_tribal_query = any(keyword in query.lower() for keyword in tribal_keywords)

            if is_location_query:
                # Search for documents mentioning entities + comprehensive Vedic geographic locations
                # Sources: Rigveda, Yajurveda (both Sharma and Griffith translations)
                # Rivers: Major rivers (Sarasvati 72×, Sindhu 50×, plus tributaries)
                # Mountains: Sacred peaks (Mujavat, Himavat/Himalaya, Trikakud)
                # Regions: Geographic and cultural regions
                common_locations = [
                    # ===== MAJOR RIVERS (Primary Sapta Sindhu system) =====
                    'Sarasvati',     # Most sacred river, 72 mentions
                    'Sindhu', 'Indus',  # Sindhu = Indus river, 50 mentions
                    'Ganga', 'Ganges',  # Ganga/Ganges
                    'Yamuna', 'Jumna',  # Yamuna/Jumna

                    # ===== PUNJAB TRIBUTARIES (Five Rivers region) =====
                    'Vipas', 'Vipasa', 'Beas',     # Modern Beas
                    'Sutudri', 'Sutlej',            # Modern Sutlej
                    'Parushni', 'Parusni', 'Ravi',  # Modern Ravi, Battle of Ten Kings site
                    'Askini', 'Asikni', 'Chenab',   # Modern Chenab
                    'Vitasta', 'Jhelum',            # Modern Jhelum

                    # ===== OTHER RIVERS =====
                    'Rasa',          # Mysterious northwestern river
                    'Arjikiya',      # Tributary
                    'Susoma',        # Lesser river
                    'Gomati', 'Gomti',  # Gomati/Gomti
                    'Sarayu',        # Sarayu river
                    'Drsadvati', 'Drishadvati',  # Drishadva ti paired with Sarasvati
                    'Kubha', 'Kabul',   # Kabul river (Afghanistan)
                    'Krumu', 'Kurram',  # Kurram river
                    'Marudvrdha',    # River in Rigveda

                    # ===== MOUNTAINS AND PEAKS =====
                    'Mujavat', 'Mūjavat',  # Sacred mountain, soma source
                    'Himavat', 'Himalaya', 'Himalayas',  # Himalayan ranges
                    'Trikakud',      # Three-peaked mountain
                    'Meru',          # Cosmic mountain

                    # ===== REGIONS AND PLACES =====
                    'Kurukshetra',   # Sacred plain, Kuru region
                    'Sapta Sindhu', 'Seven Rivers',  # Land of Seven Rivers
                    'Aryavarta',     # Land of Aryans

                    # ===== GEOGRAPHIC TERMS =====
                    'forests', 'forest',    # Forest regions (Yajurveda)
                    'plains', 'valleys',    # Geographic features
                ]
                logger.info(f"HybridRetriever: Location query detected (keywords: {[k for k in location_keywords if k in query.lower()]})")
                # Add location names to proper nouns for expansion (use original nouns, not disambiguated)
                nouns_for_expansion = [orig for orig, _, _ in proper_nouns_disambiguated] + common_locations
            elif is_tribal_query:
                # Search for documents mentioning entities + known tribal confederacies
                # Ten Kings battle: Pakthas, Bhalanas, Alinas, Sivas, Visanins, Druhyus, Anavas, Purus, etc.
                known_tribes = ['Pakthas', 'Bhalanas', 'Alinas', 'Sivas', 'Visanins', 'Druhyus', 'Anavas', 'Purus',
                              'Anu', 'Vaikarna', 'Kavasa', 'Bhrgus']
                logger.info(f"HybridRetriever: Tribal query detected (keywords: {[k for k in tribal_keywords if k in query.lower()]})")
                # Add tribal names to proper nouns for expansion (use original nouns)
                nouns_for_expansion = [orig for orig, _, _ in proper_nouns_disambiguated] + known_tribes

                # CONFEDERATION EXPANSION: If constituent tribes detected, add confederation names
                confederation_expansions = set()
                for noun in nouns_for_expansion:
                    confed = get_confederation_for_tribe(noun)
                    if confed:
                        confederation_expansions.add(confed)
                        logger.info(f"HybridRetriever: Detected constituent tribe '{noun}' → adding confederation '{confed}'")
                        # Also add the constituent tribes of that confederation
                        constituents = get_constituent_tribes(confed)
                        confederation_expansions.update(constituents)
                        logger.info(f"HybridRetriever: Adding all '{confed}' constituents: {constituents}")

                # Add confederations to expansion list
                nouns_for_expansion.extend(list(confederation_expansions))
            else:
                # Use original nouns for variant lookup
                nouns_for_expansion = [orig for orig, _, _ in proper_nouns_disambiguated]

            if nouns_for_expansion:
                logger.info(f"HybridRetriever: Found proper nouns for expansion: {nouns_for_expansion}")
                expansion_docs = []
                expansion_seen = set(sorted_hashes)  # Don't duplicate primary results

                # For each proper noun, get related documents
                # Increased limit to 12 for tribal/location queries (more entities to search)
                expansion_limit = 12 if (is_location_query or is_tribal_query) else 8
                for noun in nouns_for_expansion[:expansion_limit]:
                    # Get transliteration variants (e.g., Sudas → Sudasa, Vasishtha → Vasistha)
                    variants = self._get_transliteration_variants(noun)
                    logger.info(f"HybridRetriever: Searching variants for '{noun}': {variants}")

                    # Search semantically for the proper noun and all its variants
                    for variant in variants:
                        noun_docs = self.semantic_retriever.invoke(variant)

                        for doc in noun_docs[:EXPANSION_DOCS]:
                            content_hash = hash(doc.page_content)
                            if content_hash not in expansion_seen:
                                expansion_docs.append(doc)
                                expansion_seen.add(content_hash)
                                # Break after getting EXPANSION_DOCS per noun
                                if len(expansion_docs) >= EXPANSION_DOCS * len(proper_nouns[:3]):
                                    break

                        # Stop searching variants if we have enough docs
                        if len(expansion_docs) >= EXPANSION_DOCS * len(proper_nouns[:3]):
                            break

                if expansion_docs:
                    # Apply source filtering to expansion docs as well
                    if source_filters:
                        expansion_docs = self._filter_docs_by_source(expansion_docs, source_filters, strict_filter)

                    logger.info(f"HybridRetriever: Added {len(expansion_docs)} expansion docs via proper noun association")
                    merged_docs = merged_docs[:self.k] + expansion_docs
                    logger.info(f"HybridRetriever: Total docs (primary + expansion) = {len(merged_docs)}")

        # ATTACH MW CONTEXT to all documents for UI display
        if mw_context:
            merged_docs = self._attach_mw_context_to_docs(merged_docs, mw_context)

        # Return top k primary results + limited expansion docs
        # For Groq: Keep total manageable to stay under 6K token limit
        max_expansion = EXPANSION_DOCS * 2 if EXPANSION_DOCS > 0 else 0
        return merged_docs[:self.k + max_expansion]


def create_retriever(vec_db, documents, top_n=5):
    """Create a hybrid retriever combining semantic (Qdrant) and keyword (BM25) search.

    This combines the best of both:
    - BM25 for exact matches: specific hymn numbers, exact phrases
    - Semantic for concepts: understanding meanings, associations, relationships
    """
    
    # Override RETRIEVAL_K to 15 for better source coverage
    # This ensures we get enough documents for proper noun boosting to work effectively
    effective_k = max(RETRIEVAL_K, 15)  # Ensure minimum of 15 for Rigveda retrieval

    # Configure Qdrant semantic retriever
    qdrant_retriever = vec_db.as_retriever(search_kwargs={"k": effective_k})

    try:
        from langchain_community.retrievers import BM25Retriever

        # Create BM25 keyword retriever
        logger.info(f"Creating BM25 retriever with {len(documents)} documents")

        bm25_retriever = BM25Retriever.from_documents(documents=documents)
        bm25_retriever.k = effective_k

        # Create custom hybrid retriever
        hybrid = HybridRetriever(
            semantic_retriever=qdrant_retriever,
            keyword_retriever=bm25_retriever,
            k=effective_k
        )

        logger.info(f"Hybrid retriever created: BM25 (keywords) + Qdrant (semantic), k={effective_k}")
        return hybrid

    except Exception as e:
        logger.warning(
            f"BM25 unavailable ({e}). Using semantic retriever only.",
        )
        return qdrant_retriever
