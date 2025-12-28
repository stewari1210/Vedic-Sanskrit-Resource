from helper import logger
from config import RETRIEVAL_K, SEMANTIC_WEIGHT, KEYWORD_WEIGHT, EXPANSION_DOCS
from typing import List
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


class HybridRetriever(BaseRetriever):
    """Custom hybrid retriever that combines semantic and keyword search.

    Retrieves from BOTH:
    - Semantic search (Qdrant): Good for conceptual queries, relationships, meanings
    - Keyword search (BM25): Good for exact matches like hymn numbers, specific phrases

    Then merges and deduplicates results, prioritizing exact keyword matches."""

    semantic_retriever: BaseRetriever
    keyword_retriever: BaseRetriever
    k: int = 10

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
        strict_filter = len(detected_sources) == 1

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

            # Check if document matches any of the source filters
            matches = any(source in filename for source in source_filters)

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

        # Detect source text filters (Rigveda, Yajurveda, etc.)
        source_filters, strict_filter = self._detect_source_text_filter(query)

        # Extract keywords for BM25 (remove action words like "summarize", "explain", etc.)
        # This helps BM25 match on the actual content patterns like hymn numbers or specific terms
        import re
        import unicodedata
        # Keep hymn references, numbers in brackets, and important nouns
        keyword_query = re.sub(r'\b(summarize|explain|describe|tell|about|what|who|when|where|why|how|is|are|the|a|an|in|on|at|for)\b', '', query, flags=re.IGNORECASE)
        keyword_query = keyword_query.strip()

        # Strip diacritical marks for BM25 (e.g., Sūdaḥ → Sudas, ā → a)
        # This helps match Sanskrit terms that may be transliterated differently
        keyword_query_normalized = unicodedata.normalize('NFD', keyword_query)
        keyword_query_normalized = ''.join(char for char in keyword_query_normalized if unicodedata.category(char) != 'Mn')

        # Remove punctuation except hyphens and brackets (keep hymn references intact)
        keyword_query_normalized = re.sub(r'[^\w\s\[\]\-]', '', keyword_query_normalized)
        keyword_query_normalized = keyword_query_normalized.strip()

        # If we stripped too much, fall back to original query
        if len(keyword_query_normalized) < 2:
            keyword_query_normalized = query

        logger.info(f"HybridRetriever: Keyword query for BM25 = '{keyword_query_normalized}'")

        # Get results from both retrievers
        # Keyword retriever with extracted keywords (normalized, no diacritics)
        keyword_docs = self.keyword_retriever.invoke(keyword_query_normalized)
        # Semantic retriever with full natural language query (original with diacritics)
        semantic_docs = self.semantic_retriever.invoke(query)

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

        logger.info(f"HybridRetriever: Merged to {len(merged_docs)} unique docs, returning top {self.k}")
        if merged_docs and len(merged_docs) > 0:
            top_score = doc_scores[sorted_hashes[0]]
            logger.info(f"HybridRetriever: Top doc score={top_score:.2f} (semantic {SEMANTIC_WEIGHT:.0%}, keyword {KEYWORD_WEIGHT:.0%})")

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

        # Return top k primary results (expansion docs come after for LLM context)
        return merged_docs[:self.k + (EXPANSION_DOCS * 3 if EXPANSION_DOCS > 0 else 0)]


def create_retriever(vec_db, documents, top_n=5):
    """Create a hybrid retriever combining semantic (Qdrant) and keyword (BM25) search.

    This combines the best of both:
    - BM25 for exact matches: specific hymn numbers, exact phrases
    - Semantic for concepts: understanding meanings, associations, relationships
    """

    # Configure Qdrant semantic retriever
    qdrant_retriever = vec_db.as_retriever(search_kwargs={"k": RETRIEVAL_K})

    try:
        from langchain_community.retrievers import BM25Retriever

        # Create BM25 keyword retriever
        logger.info(f"Creating BM25 retriever with {len(documents)} documents")

        bm25_retriever = BM25Retriever.from_documents(documents=documents)
        bm25_retriever.k = RETRIEVAL_K

        # Create custom hybrid retriever
        hybrid = HybridRetriever(
            semantic_retriever=qdrant_retriever,
            keyword_retriever=bm25_retriever,
            k=RETRIEVAL_K
        )

        logger.info(f"Hybrid retriever created: BM25 (keywords) + Qdrant (semantic), k={RETRIEVAL_K}")
        return hybrid

    except Exception as e:
        logger.warning(
            f"BM25 unavailable ({e}). Using semantic retriever only.",
        )
        return qdrant_retriever
