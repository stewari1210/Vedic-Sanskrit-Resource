# Migration Debate Quick Reference

## Key Verses by Theory

### AMT Evidence Verses
```bash
# Geographic progression (River Hymn)
python migration_debate_cli.py --verse "RV 10.75"

# Dasa conflicts ("dark-skinned")
python migration_debate_cli.py --verse "RV 1.101.1"
python migration_debate_cli.py --verse "RV 1.130.8"

# Battle of Ten Kings
python migration_debate_cli.py --verse "RV 7.18"

# Anāsa (speechless) Dasyus
python migration_debate_cli.py --verse "RV 5.29.10"

# Fort-destroyer
python migration_debate_cli.py --verse "RV 1.174.2"
```

### OIT Evidence Verses
```bash
# Sarasvati "mighty river to sea" (STRONGEST OIT)
python migration_debate_cli.py --verse "RV 7.95.2"
python migration_debate_cli.py --verse "RV 6.61.2"
python migration_debate_cli.py --verse "RV 6.61.8"

# Fathers' ancestral path
python migration_debate_cli.py --verse "RV 8.30.3"

# Hariyupiya (Harappa?)
python migration_debate_cli.py --verse "RV 6.27.5"

# Indigenous fauna (elephant)
python migration_debate_cli.py --verse "RV 1.163.1"

# Vedic people have forts too
python migration_debate_cli.py --verse "RV 7.3.7"
```

## Command Templates

```bash
# Basic usage
python migration_debate_cli.py --verse "RV X.Y.Z"

# With context
python migration_debate_cli.py --verse "RV X.Y" \
  --context "Archaeological context here"

# Multiple rounds
python migration_debate_cli.py --verse "RV X.Y" --rounds 3

# With Google Gemini (better quality)
python migration_debate_cli.py --verse "RV X.Y" --google --rounds 3

# Interactive mode
python migration_debate_cli.py --interactive
```

## Analysis Categories

### Strong AMT Evidence
- Clear west-to-east geographic progression
- Ethnic/linguistic markers in conflicts
- Cultural memory of migration

### Strong OIT Evidence
- Sarasvati perennial (requires pre-1900 BCE)
- No migration memory
- Deep indigenous geographic knowledge

### Ambiguous/Weak
- Mythological battles (could be historical or pure myth)
- Generic river/fort references
- Poetic exaggerations

## Output Files

Debates saved to: `migration_debates/migration_debate_RV_X_Y_Z_TIMESTAMP.json`
