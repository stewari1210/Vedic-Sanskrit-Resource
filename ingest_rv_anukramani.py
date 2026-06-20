"""
Bulk-ingest the Rigveda anukramaṇī (ṛṣi / devatā / meter for all 1028 sūktas).

Source: the digital Rig Veda Anukramaṇī of Akavarapu & Bhattacharya (2023),
"Creation of a Digital Rig Vedic Index (Anukramaṇī) for Computational Linguistic
Tasks", 18th World Sanskrit Conference (ACL). Apache-2.0 licensed. The dataset is
the traditional anukramaṇī (Śaunaka/Kātyāyana) digitised with the anuvṛtti
already resolved — i.e. indigenous Vedic apparatus, not a translation, so it is
consistent with the project's anti-translator-bias mission.

  https://github.com/mahesh-ak/WSC2023  →  Anukramani/Mandala_{1..10}.txt

Each line is:  hymn.verses.seer.divinity.meter
(values never contain '.', so a plain split on '.' yields exactly 5 fields; the
per-verse `(1-4)x,(5)y` annotations use only commas/parens/hyphens.)

Writes knowledge_store/anukramani_rv.json:
    {"_meta": {...}, "hymns": {"M.SSS": {rishi, devata, meter, verses}, ...}}

This is the BASE layer; knowledge_store/kg_seed.json (curated patron/theme/
entities) overrides it at load time — so this never clobbers curated grounding.

Usage:
    python ingest_rv_anukramani.py             # fetch all 10 maṇḍalas → write JSON
    python ingest_rv_anukramani.py --dry-run   # fetch + parse + report, no write
    python ingest_rv_anukramani.py --self-test # offline parser unit test (no network)
"""

import argparse
import json
import sys
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/mahesh-ak/WSC2023/main/Anukramani/Mandala_{}.txt"
OUT_PATH = Path(__file__).parent / "knowledge_store" / "anukramani_rv.json"

SOURCE_META = {
    "source": "Akavarapu & Bhattacharya 2023, Digital Rig Veda Anukramaṇī (WSC/ACL)",
    "url": "https://github.com/mahesh-ak/WSC2023",
    "license": "Apache-2.0",
    "provenance": "authoritative",
    "note": "Traditional Śaunaka/Kātyāyana anukramaṇī, anuvṛtti resolved. ṛṣi/devatā/meter per sūkta.",
}


def parse_mandala(mandala: int, text: str) -> tuple[dict, int]:
    """Parse one maṇḍala file → ({hymn_id: {...}}, n_skipped)."""
    hymns, skipped = {}, 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("hymn.verses"):
            continue
        parts = line.split(".")
        if len(parts) != 5:
            skipped += 1
            continue
        hy, vs, rishi, devata, meter = parts
        try:
            hy_i, vs_i = int(hy), int(vs)
        except ValueError:
            skipped += 1
            continue
        hymns[f"{mandala}.{hy_i:03d}"] = {
            "rishi": rishi.strip(),
            "devata": devata.strip(),
            "meter": meter.strip(),
            "verses": vs_i,
        }
    return hymns, skipped


def _fetch(mandala: int) -> str:
    import urllib.request
    with urllib.request.urlopen(BASE_URL.format(mandala), timeout=60) as r:
        return r.read().decode("utf-8")


# ── Offline parser unit test ─────────────────────────────────────────────────
_SELF_TEST_SAMPLES = {
    # mandala: representative real lines (incl. the tricky per-verse cases)
    2: "1.16.śaunako gṛtsamadaḥ.agniḥ.jagatī",
    10: ("60.12.(1-5,7-12)bandhuḥ śrutabandhurviprabandhugaupāyanāḥ,(6)agastyasvasā."
         "(1-4,6)asamātiḥ,(5)indraḥ,(7-11)subandhojīvaḥ,(12)bandhvādīnāṁ hastāḥ."
         "(1-5)gāyatrī,(6-7,10-12)anuṣṭup,(8-9)paṅktiḥ"),
}


def self_test() -> bool:
    ok = True
    h2, _ = parse_mandala(2, "hymn.verses.seer.divinity.meter\n" + _SELF_TEST_SAMPLES[2])
    e = h2.get("2.001", {})
    cond = e.get("rishi") == "śaunako gṛtsamadaḥ" and e.get("devata") == "agniḥ" and e.get("meter") == "jagatī"
    print(f"  {'✓' if cond else '✗'} RV 2.001 → {e}")
    ok &= cond

    h10, _ = parse_mandala(10, "hymn.verses.seer.divinity.meter\n" + _SELF_TEST_SAMPLES[10])
    e = h10.get("10.060", {})
    cond = ("gaupāyanāḥ" in e.get("rishi", "")
            and "asamātiḥ" in e.get("devata", "")
            and "gāyatrī" in e.get("meter", "")
            and e.get("verses") == 12)
    print(f"  {'✓' if cond else '✗'} RV 10.060 → rishi has Gaupāyanas, devatā names asamātiḥ, meter gāyatrī")
    ok &= cond
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="parse + report, do not write")
    ap.add_argument("--self-test", action="store_true", help="offline parser unit test")
    args = ap.parse_args()

    if args.self_test:
        print("Self-test (offline):")
        sys.exit(0 if self_test() else 1)

    all_hymns, total_skipped = {}, 0
    for m in range(1, 11):
        try:
            text = _fetch(m)
        except Exception as e:
            print(f"❌ failed to fetch Maṇḍala {m}: {e}")
            sys.exit(1)
        hymns, skipped = parse_mandala(m, text)
        total_skipped += skipped
        all_hymns.update(hymns)
        print(f"  Maṇḍala {m:>2}: {len(hymns)} hymns" + (f"  ({skipped} skipped)" if skipped else ""))

    print(f"\nTotal: {len(all_hymns)} sūktas parsed"
          + (f", {total_skipped} lines skipped" if total_skipped else ""))
    if len(all_hymns) < 1000:
        print("⚠️  Expected ~1028 sūktas — check the source/format before trusting output.")

    # Spot-check a few well-known hymns
    for hid, want in [("10.060", "gaupāyanāḥ"), ("7.018", "vasiṣṭha"),
                      ("3.062", "viśvāmitra"), ("1.001", "madhucchand")]:
        got = all_hymns.get(hid, {})
        flag = "✓" if want in got.get("rishi", "").lower() else "?"
        print(f"  {flag} {hid}: ṛṣi={got.get('rishi','—')} | devatā={got.get('devata','—')[:40]}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"_meta": SOURCE_META, "hymns": all_hymns}, f,
                  indent=2, ensure_ascii=False)
    print(f"\n✅ Wrote {len(all_hymns)} hymns → {OUT_PATH}")
    print("The injection path picks this up automatically (curated kg_seed.json "
          "still overrides per-key). Restart Streamlit to load it.")


if __name__ == "__main__":
    main()
