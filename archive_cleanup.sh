#!/usr/bin/env bash
set -euo pipefail
cd /sessions/modest-admiring-dirac/mnt/Vedic-Sanskrit-Tutor

mkdir -p archive/docs archive/scripts_oneoff archive/tests \
         archive/source_data archive/data_intermediate archive/dev_config

KEEP_PY="ingest_aitareya_brahmana.py ingest_atharvaveda_shaunaka.py ingest_pancavimsa_brahmana.py ingest_rv_anukramani.py ingest_shatapatha_brahmana.py ingest_taittiriya_samhita.py ingest_vajasaneyi_samhita.py build_corpus_lexicon.py rebuild_bm25_pickle.py rebuild_mandala_clean.py seed_kg.py migrate_kg_to_qdrant.py create_qdrant_payload_index.py keyvault.py"
KEEP_MD="README.md PROJECT_STATUS.md"
KEEP_JSON="monier_williams_concept_store.json proper_noun_variants.json sanskrit_dictionary.json sanskrit_dictionary_cleaned.json"
KEEP_OTHER="requirements.txt packages.txt run_sanskrit_tutor_web.sh"

in_list(){ case " $2 " in *" $1 "*) return 0;; *) return 1;; esac; }
mv_safe(){ [ -e "$1" ] && mv "$1" "$2" && echo "  -> $2$(basename "$1")" || true; }

moved=0
while IFS= read -r f; do
  case "$f" in .git*|env.template|.python-version) continue;; esac
  case "$f" in
    *.py)   in_list "$f" "$KEEP_PY" && continue
            case "$f" in test_*) mv_safe "$f" archive/tests/;; *) mv_safe "$f" archive/scripts_oneoff/;; esac; moved=$((moved+1));;
    *.md)   in_list "$f" "$KEEP_MD" && continue; mv_safe "$f" archive/docs/; moved=$((moved+1));;
    *.json) in_list "$f" "$KEEP_JSON" && continue; mv_safe "$f" archive/data_intermediate/; moved=$((moved+1));;
    *.txt)  in_list "$f" "$KEEP_OTHER" && continue; mv_safe "$f" archive/source_data/; moved=$((moved+1));;
    *.pdf)  mv_safe "$f" archive/source_data/; moved=$((moved+1));;
    *.sh)   in_list "$f" "$KEEP_OTHER" && continue; [ "$f" = "archive_cleanup.sh" ] && continue; mv_safe "$f" archive/scripts_oneoff/; moved=$((moved+1));;
    *.envrc|*.code-workspace|.DS_Store) mv_safe "$f" archive/dev_config/; moved=$((moved+1));;
  esac
done < <(git ls-files | grep -vE '/')

[ -d scripts ] && mv scripts archive/scripts_oneoff/scripts && echo "  -> archive/scripts_oneoff/scripts/" || true
[ -d tools ]   && mv tools   archive/scripts_oneoff/tools   && echo "  -> archive/scripts_oneoff/tools/" || true
echo ""; echo ">>> moved $moved root-level files into archive/"
