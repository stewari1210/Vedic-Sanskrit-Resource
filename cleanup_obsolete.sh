#!/bin/bash
# Cleanup script for obsolete files in Vedic Sanskrit Tutor

echo "🗑️  Cleaning up obsolete files..."

# 1. CLI RAG System (obsolete - replaced by Agentic RAG)
echo "Removing CLI RAG system..."
rm -f src/cli_run.py

# 2. Debate System (moved to different repo)
echo "Removing debate system files..."
rm -f debate_cli.py
rm -f src/utils/debate_agents.py
rm -f DEBATE_SYSTEM_README.md
rm -f DEBATE_SYSTEM_EXPLAINED.md
rm -f DEBATE_CLI_README.md
rm -f DEBATE_CLI_GUIDE.md
rm -f DEBATE_USAGE_TIPS.md
rm -f DEBATE_QUICKREF.md
rm -f MIGRATION_DEBATE_README.md

# 3. Legacy/Development Documentation
echo "Removing legacy documentation..."
rm -f SOURCE_TEXT_FILTERING.md
rm -f REGENERATION_LOOP_FIX.md
rm -f SHARMA_RIGVEDA_PARSING_NOTES.md
rm -f M5_SETUP_GUIDE.md
rm -f EVALUATOR_ANALYSIS.md
rm -f YAJURVEDA_PROPER_NOUN_ANALYSIS.md
rm -f AGENTIC_RAG_EXPLANATION.md
rm -f COMPLETE_CONSOLIDATION_ANALYSIS.md
rm -f PARALLELIZATION_DIAGRAM.md
rm -f PARALLELIZATION_SUMMARY.md
rm -f TROUBLESHOOTING_OLLAMA_HANG.md

# 4. Temp/test files
echo "Removing temporary test files..."
rm -f test_parallelization.py
rm -f streamlit.log

# 5. Old dictionary parsing files (keep v2, remove older versions)
echo "Removing old dictionary parsing versions..."
rm -f parse_monier_williams.py
rm -f monier_williams_eng_to_skt.json

# 6. Old optimization scripts
echo "Removing old optimization scripts..."
rm -f reindex_optimized.py
rm -f convert_and_index_new_texts.py
rm -f src/config_parallel.py

# 7. Remove old test markdown
rm -f test_agentic_frontend.md

echo "✅ Cleanup complete!"
echo ""
echo "Files removed:"
echo "  - CLI RAG system (1 file)"
echo "  - Debate system (9 files)"
echo "  - Legacy docs (11 files)"
echo "  - Test/temp files (2 files)"
echo "  - Old scripts (6 files)"
echo ""
echo "Total: ~29 obsolete files removed"
