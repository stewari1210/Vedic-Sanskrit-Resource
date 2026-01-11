# 🚀 Using Smaller/Faster Models for Sanskrit Tutor

## Quick Start

### Install the recommended fast model:
```bash
ollama pull phi3.5:mini
```

### Run the tutor with it:
```bash
python src/vedic_sanskrit_tutor.py --model phi3.5:mini
```

## Available Fast Models

### 🏆 **Recommended: phi3.5:mini**
```bash
ollama pull phi3.5:mini
python src/vedic_sanskrit_tutor.py --model phi3.5:mini
```
- **Size**: ~2.2 GB
- **Speed**: 2-3x faster than llama3.1:8b
- **Quality**: Excellent for education/grammar
- **Best for**: All-around Sanskrit learning

### ⚡ **Super Fast: llama3.2:3b**
```bash
ollama pull llama3.2:3b
python src/vedic_sanskrit_tutor.py --model llama3.2:3b
```
- **Size**: ~2 GB
- **Speed**: Very fast
- **Quality**: Good
- **Best for**: Quick vocabulary lookup, grammar basics

### 🏃 **Fastest: llama3.2:1b**
```bash
ollama pull llama3.2:1b
python src/vedic_sanskrit_tutor.py --model llama3.2:1b
```
- **Size**: ~1 GB
- **Speed**: Extremely fast
- **Quality**: Decent
- **Best for**: Flashcards, simple definitions

### 🎓 **Alternative: phi3:mini**
```bash
ollama pull phi3:mini
python src/vedic_sanskrit_tutor.py --model phi3:mini
```
- **Size**: ~2.3 GB
- **Speed**: Fast
- **Quality**: Excellent for teaching
- **Note**: Slightly older than phi3.5

### 🔷 **Google's gemma2:2b**
```bash
ollama pull gemma2:2b
python src/vedic_sanskrit_tutor.py --model gemma2:2b
```
- **Size**: ~1.6 GB
- **Speed**: Very fast
- **Quality**: Good balance

## Speed Comparison (Approximate)

| Model | Speed (tokens/sec) | Time for Lesson* | RAM Usage |
|-------|-------------------|------------------|-----------|
| llama3.1:8b | 25 | 90 sec | ~5 GB |
| **phi3.5:mini** | **60** | **40 sec** | **~2.5 GB** |
| phi3:mini | 55 | 45 sec | ~2.5 GB |
| llama3.2:3b | 70 | 35 sec | ~2 GB |
| llama3.2:1b | 100 | 25 sec | ~1.5 GB |
| gemma2:2b | 75 | 30 sec | ~2 GB |

*Average time to generate a full grammar/vocabulary lesson

## Quality Comparison for Sanskrit Tasks

| Model | Grammar | Vocabulary | Translation | Overall |
|-------|---------|------------|-------------|---------|
| llama3.1:8b | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **phi3.5:mini** | **⭐⭐⭐⭐** | **⭐⭐⭐⭐** | **⭐⭐⭐** | **⭐⭐⭐⭐** |
| phi3:mini | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| llama3.2:3b | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| llama3.2:1b | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| gemma2:2b | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

## Which Model Should You Use?

### **For Most Users: phi3.5:mini**
- Perfect balance of speed and quality
- Excellent at explaining grammar
- Great for all learning modules
- 2-3x faster than current setup

### **If You Want Maximum Speed: llama3.2:3b**
- Still maintains good quality
- Very fast responses
- Good for daily practice

### **If RAM is Limited: llama3.2:1b or gemma2:2b**
- Uses minimal resources
- Still useful for basic lookup
- Best for older computers

### **If Quality > Speed: stick with llama3.1:8b**
- Your current model
- Best overall quality
- Slower but more thorough

## Installation & Testing

### 1. Install your chosen model:
```bash
ollama pull phi3.5:mini
```

### 2. Test it:
```bash
python src/vedic_sanskrit_tutor.py --model phi3.5:mini
```

### 3. Try a quick lesson:
- Choose module 2 (Vocabulary)
- Choose category 1 (Deities)
- Compare speed with llama3.1:8b

### 4. If happy, make it default:
Edit `src/vedic_sanskrit_tutor.py` line 333:
```python
parser.add_argument("--model", type=str, default="phi3.5:mini",  # Changed from llama3.1:8b
```

## Pro Tips

### Multiple Models for Different Tasks

Use different models for different modules:

```bash
# Fast model for vocab drills
alias sanskrit-vocab="python src/vedic_sanskrit_tutor.py --model llama3.2:3b"

# Quality model for deep translation
alias sanskrit-translate="python src/vedic_sanskrit_tutor.py --model llama3.1:8b"

# Balanced model for general learning
alias sanskrit-tutor="python src/vedic_sanskrit_tutor.py --model phi3.5:mini"
```

### Benchmark Your Own System

Test speed on your machine:
```bash
# Time a vocabulary lesson
time python src/vedic_sanskrit_tutor.py --model phi3.5:mini
# (Choose module 2, category 1, wait for response)

# Compare with current model
time python src/vedic_sanskrit_tutor.py --model llama3.1:8b
```

## Troubleshooting

### Model not found?
```bash
# Pull the model first
ollama pull phi3.5:mini

# Verify it's installed
ollama list
```

### Out of memory?
Try smaller models:
```bash
ollama pull llama3.2:1b  # Only 1 GB
python src/vedic_sanskrit_tutor.py --model llama3.2:1b
```

### Quality seems worse?
Some trade-offs with smaller models:
- Use phi3.5:mini for best small model quality
- Or stick with llama3.1:8b for complex explanations
- Use smaller models for simple lookups only

## Summary

**TL;DR: Install and use phi3.5:mini for 2-3x faster learning with minimal quality loss:**

```bash
ollama pull phi3.5:mini
python src/vedic_sanskrit_tutor.py --model phi3.5:mini
```

Happy faster learning! 🚀🕉️
