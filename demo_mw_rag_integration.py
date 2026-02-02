#!/usr/bin/env python3
"""
Demo: MW Concept Store Integration with RAG

This script demonstrates how the MW concept store enhances RAG queries
by providing:
1. Transliteration bridging (Devanagari ↔ IAST)
2. Semantic expansion (definitions → related terms)
3. Vedic grounding (references to source texts)

Usage:
    python3 demo_mw_rag_integration.py
"""

from src.utils.mw_concept_store import MWConceptStore
from src.utils.transliteration import TransliterationHelper

def demo_query_enhancement():
    """Show how MW concept store enhances RAG queries."""
    
    print("=" * 80)
    print("MW Concept Store + Transliteration → Enhanced RAG")
    print("=" * 80)
    
    # Initialize components
    mw = MWConceptStore()
    trans = TransliterationHelper()
    
    # Test queries (mix of Devanagari, IAST, English)
    test_queries = [
        "अग्नि पूजा कैसे करें",           # Devanagari: "How to perform Agni worship"
        "Sarasvatī river disappearance",  # IAST + English
        "सोम रस का महत्व",                # Devanagari: "Importance of Soma juice"
        "Indra and Agni relationship",   # English
        "वेद में ऋषि",                    # Devanagari: "Rishis in the Vedas"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Original Query: {query}")
        print("=" * 80)
        
        # Step 1: Generate transliteration variants
        print("\n📝 Step 1: Transliteration Variants")
        variants = trans.normalize_query(query)
        for variant in variants[:5]:
            print(f"   • {variant}")
        
        # Step 2: Extract Sanskrit terms and lookup in MW
        print("\n📖 Step 2: MW Concept Store Lookup")
        words = query.split()
        
        found_terms = []
        for word in words:
            result = mw.lookup(word)
            if result['found']:
                found_terms.append(result)
                print(f"\n   ✅ '{word}' → '{result['primary_key']}'")
                print(f"      Devanagari: {result['devanagari']}")
                print(f"      Definitions: {result['definitions'][0][:100]}...")
                if result['vedic_refs']:
                    print(f"      Vedic refs: {', '.join(result['vedic_refs'][:3])}")
        
        if not found_terms:
            print("   ⚠️  No Sanskrit terms found in MW dictionary")
        
        # Step 3: Generate enhanced query
        print("\n🔍 Step 3: Enhanced Query for Vector Search")
        enhanced_query = mw.expand_query(query)
        print(f"   {enhanced_query[:200]}...")
        
        # Step 4: Show what the RAG would do
        print("\n🎯 Step 4: RAG Search Strategy")
        print("   • Search Qdrant with ALL transliteration variants")
        print("   • Boost results matching MW definitions")
        if found_terms and found_terms[0]['vedic_refs']:
            print(f"   • Filter/rank by Vedic references: {', '.join(found_terms[0]['vedic_refs'][:3])}")
        print("   • Return corpus chunks + MW definitions as context")


def demo_concept_store_stats():
    """Show statistics about the concept store."""
    
    print("\n\n" + "=" * 80)
    print("MW Concept Store Statistics")
    print("=" * 80)
    
    mw = MWConceptStore()
    stats = mw.stats()
    
    print(f"\n📊 Total Concepts: {stats['total_concepts']:,}")
    print(f"📊 Total Lookup Keys: {stats['total_lookup_keys']:,}")
    print(f"📊 Source: {stats['metadata']['source']}")
    print(f"📊 Version: {stats['metadata']['version']}")
    
    # Sample some common Vedic terms
    print("\n\n🔍 Sample Lookups for Common Vedic Terms:")
    print("=" * 80)
    
    common_terms = [
        "agni", "indra", "soma", "varuna", "mitra", 
        "ushas", "surya", "vayu", "aditya", "marut"
    ]
    
    for term in common_terms:
        result = mw.lookup(term)
        if result['found']:
            # Count definitions
            def_count = len(result['definitions'])
            ref_count = len(result['vedic_refs'])
            
            print(f"\n{term:15} → {result['primary_key']:15} "
                  f"({result['devanagari']:10}) "
                  f"[{def_count} defs, {ref_count} refs]")
            
            # Show first definition snippet
            if result['definitions']:
                first_def = result['definitions'][0][:80].replace('\n', ' ')
                print(f"   {first_def}...")


def demo_integration_pseudocode():
    """Show pseudocode for RAG integration."""
    
    print("\n\n" + "=" * 80)
    print("RAG Integration Pseudocode")
    print("=" * 80)
    
    pseudocode = """
# In src/utils/retriever.py

from src.utils.mw_concept_store import MWConceptStore
from src.utils.transliteration import TransliterationHelper

class EnhancedRetriever:
    def __init__(self):
        self.mw = MWConceptStore()
        self.trans = TransliterationHelper()
        self.qdrant_client = QdrantClient(...)
    
    def retrieve(self, query: str, k: int = 5):
        # Step 1: Generate transliteration variants
        variants = self.trans.normalize_query(query)
        
        # Step 2: Lookup Sanskrit terms in MW
        mw_results = []
        for word in query.split():
            result = self.mw.lookup(word)
            if result['found']:
                mw_results.append(result)
        
        # Step 3: Expand query with MW definitions
        enhanced_query = self.mw.expand_query(query)
        
        # Step 4: Search Qdrant with enhanced query + variants
        search_queries = [enhanced_query] + variants[:3]
        
        all_results = []
        for search_q in search_queries:
            results = self.qdrant_client.search(
                collection_name="ancient_history",
                query_vector=self.embed_model.encode(search_q),
                limit=k
            )
            all_results.extend(results)
        
        # Step 5: Deduplicate and rank results
        unique_results = self._deduplicate(all_results)
        
        # Step 6: Boost results that match MW Vedic references
        if mw_results:
            vedic_refs = set()
            for mw_res in mw_results:
                vedic_refs.update(mw_res['vedic_refs'])
            
            # Boost chunks whose metadata matches Vedic refs
            ranked_results = self._boost_by_vedic_refs(
                unique_results, vedic_refs
            )
        else:
            ranked_results = unique_results
        
        # Step 7: Attach MW context to results
        for result in ranked_results[:k]:
            result['mw_context'] = mw_results
        
        return ranked_results[:k]


# In Streamlit app (sanskrit_tutor_web.py)

def display_results(results):
    for result in results:
        st.write(result['text'])
        
        # Show MW definitions in sidebar/expander
        if result.get('mw_context'):
            with st.expander("📖 Sanskrit Dictionary Context"):
                for mw in result['mw_context']:
                    st.write(f"**{mw['primary_key']}** ({mw['devanagari']})")
                    st.write(mw['definitions'][0])
                    st.write(f"References: {', '.join(mw['vedic_refs'][:5])}")
    """
    
    print(pseudocode)
    
    print("\n" + "=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print("""
1. ✅ MW concept store created (176,146 entries, 522,880 lookup keys)
2. ✅ Transliteration layer ready (src/utils/transliteration.py)
3. ⏳ TODO: Integrate into src/utils/retriever.py
4. ⏳ TODO: Add MW context display in sanskrit_tutor_web.py
5. ⏳ TODO: Switch to multilingual embedding model
6. ⏳ TODO: Re-index corpus with multilingual embeddings
7. ⏳ TODO: Test end-to-end with bilingual queries
    """)


if __name__ == '__main__':
    demo_query_enhancement()
    demo_concept_store_stats()
    demo_integration_pseudocode()
    
    print("\n" + "=" * 80)
    print("✅ Demo Complete!")
    print("=" * 80)
