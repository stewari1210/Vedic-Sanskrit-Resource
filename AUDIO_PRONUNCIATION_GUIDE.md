# 🔊 Audio Pronunciation Guide for Vedic Sanskrit Tutor

## ✨ New Feature: Text-to-Speech Pronunciation

The Sanskrit tutor now includes **audible pronunciation** using Google Text-to-Speech (gTTS), making it much easier to learn proper pronunciation!

## 🎯 Where Audio is Available

### 1. **Pronunciation Module (🗣️ उच्चारण)**
- Type any Sanskrit word (Devanagari or IAST)
- Click "🔊 Learn Pronunciation"
- **Hear the word pronounced** + get detailed explanation
- Quick practice words have a 🔊 button for instant audio

### 2. **Verse Translation Module (🔤 अनुवाद)**
- Choose famous verses (RV 1.1.1, Gayatri Mantra)
- **Hear the entire verse** pronounced correctly
- Perfect for learning mantras!

## 🛠️ How It Works

### Technology
- **Engine**: Google Text-to-Speech (gTTS)
- **Language**: Hindi mode (`lang='hi'`) for Devanagari
- **Speed**: Slow mode (`slow=True`) for clearer pronunciation
- **Format**: MP3 audio files
- **Caching**: Audio cached in session for faster replay

### Audio Quality
- ✅ Handles Devanagari script perfectly
- ✅ Correct vowel lengths (ā, ī, ū)
- ✅ Proper consonant clusters
- ✅ Anusvāra (ं) and Visarga (ः) pronunciation
- ⚠️ May not capture Vedic accents (udātta, anudātta) - these are subtle

## 🎓 Best Practices

### For Learning Pronunciation

1. **Listen First** 🎧
   - Play audio before reading explanation
   - Focus on the sounds

2. **Read Along** 📖
   - Watch Devanagari while listening
   - Track syllable-by-syllable

3. **Repeat** 🔄
   - Say word after hearing it
   - Play multiple times
   - Compare your pronunciation

4. **Study Details** 📚
   - Read AI tutor's explanation
   - Note vowel lengths
   - Understand syllable breaks

### For Mantras

1. **Full Verse First** 🕉️
   - Listen to complete verse
   - Get flow and rhythm

2. **Word-by-Word** 📝
   - Copy individual words to Pronunciation module
   - Practice each word separately
   - Build up to full verse

3. **Daily Practice** 🌅
   - Listen to same verse daily
   - Memorize through repetition
   - Focus on correct pronunciation

## 📱 Usage Examples

### Example 1: Learning a Single Word

```
1. Go to: 🗣️ Pronunciation module
2. Type: अग्नि
3. Click: 🔊 Learn Pronunciation
4. Result:
   - Large Devanagari display
   - Audio player (click to hear "ag-ni")
   - Detailed pronunciation guide
   - Tips for Hindi speakers
```

### Example 2: Quick Practice

```
1. Go to: 🗣️ Pronunciation module
2. Scroll to: "Quick Practice"
3. Select: इन्द्र
4. Click: 🔊 button (instant audio)
5. Click: 📚 Learn button (full lesson)
```

### Example 3: Gayatri Mantra

```
1. Go to: 🔤 Verse Translation
2. Click: "RV 3.62.10 (Gayatri Mantra)"
3. Read translation and explanation
4. Scroll down to: 🔊 Hear the Verse
5. Click audio player to hear:
   "तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्"
```

## 🎨 UI Features

### Audio Player
- Clean, native HTML5 audio player
- Play/pause controls
- Volume adjustment
- Download option (right-click)

### Layout
- **2-column design**:
  - Left: Large Devanagari text
  - Right: Audio player
- **Visual hierarchy**: Audio always near the text
- **Responsive**: Works on mobile/tablet

## 🔧 Technical Details

### Installation
```bash
pip install gtts
```

Already included in requirements!

### Supported Input
- ✅ Pure Devanagari: `अग्नि`
- ✅ IAST transliteration: `agni`
- ✅ Mixed scripts: `Agni देवता`
- ✅ Complete verses
- ✅ Multiple words

### Audio Caching
- First pronunciation: ~2-3 seconds (generation)
- Subsequent plays: Instant (cached)
- Cache cleared: On page refresh
- Cache storage: Temporary files (auto-cleanup)

### Performance
- **Generation speed**: 1-3 seconds per word
- **File size**: ~5-20 KB per word
- **Network**: Requires internet (Google TTS API)
- **Offline**: Not supported (needs Google servers)

## 🐛 Troubleshooting

### "gTTS not installed" Warning

**Problem**: Warning appears when clicking audio button

**Solution**:
```bash
pip install gtts
```

Then refresh browser page.

### No Audio Playing

**Possible causes**:
1. **No internet connection** - gTTS requires online access
2. **Browser blocked audio** - Check browser permissions
3. **Generation failed** - Check console for errors

**Solution**:
```bash
# Check internet
ping google.com

# Reinstall gTTS
pip install --upgrade gtts

# Try different browser (Chrome/Firefox recommended)
```

### Audio Sounds Wrong

**Issue**: Pronunciation doesn't match expectations

**Explanation**:
- gTTS uses Hindi phonetics for Devanagari
- Generally accurate for Sanskrit words
- May not capture Vedic accents
- Good for learning, not perfect for ritual chanting

**Alternative**:
- Use audio as starting point
- Consult pronunciation guide details
- Consider dedicated Sanskrit pronunciation recordings for precision

### Slow Audio Generation

**Issue**: Taking >5 seconds to generate

**Causes**:
- Slow internet connection
- Long text (entire verses)
- Google TTS server load

**Solutions**:
- Use shorter words first
- Wait for cache to build up
- Practice with pre-cached quick practice words

## 💡 Pro Tips

### 1. Build a Practice List
- Try all 5 quick practice words
- Listen to each multiple times
- Audio is cached for the session

### 2. Compare Variations
- Type same word in Devanagari vs IAST
- Notice any pronunciation differences
- Learn which input gives better audio

### 3. Use with Hindi Knowledge
- gTTS uses Hindi phonetics
- Great if you know Hindi
- Bridging Hindi ↔ Sanskrit sounds

### 4. Focus on Difficult Sounds
**Challenge sounds for English speakers**:
- ṛ (ऋ) - retroflex 'r'
- ṣ (ष) - retroflex 'sh'
- ṭ/ḍ (ट/ड) - retroflex 't/d'
- aspirated consonants (kh, gh, ch, etc.)

Use audio repeatedly for these!

### 5. Morning Mantra Practice
```
Daily routine:
1. Open Verse Translation
2. Pick RV 1.1.1 or Gayatri
3. Listen 3-5 times
4. Recite along with audio
5. Practice without audio
6. Compare with audio again
```

## 📚 Recommended Learning Path

### Week 1: Single Words
- Use Pronunciation module
- Practice all 5 quick words daily
- Build audio vocabulary

### Week 2: Deity Names
- Type deity names: अग्नि, इन्द्र, सोम, वरुण, मित्र
- Learn proper pronunciation
- Recognize in verses

### Week 3: Common Words
- Vocabulary module + Pronunciation
- Copy new words to pronunciation
- Build listening comprehension

### Week 4: Short Verses
- Start with RV 1.1.1 (shortest verse)
- Listen + read + repeat
- Memorize with correct pronunciation

## 🆚 Audio vs Text Guide

| Method | Pros | Cons |
|--------|------|------|
| **🔊 Audio** | Natural learning<br>Correct sounds<br>Rhythm and flow | Requires internet<br>May miss nuances<br>No offline use |
| **📖 Text Guide** | Detailed explanations<br>Visual breakdown<br>Always available | Harder to grasp<br>Need phonetic knowledge<br>Easy to misread |

**Best Practice**: Use BOTH together! 🎧 + 📖

## 🎯 Success Metrics

Track your progress:
- ✅ Can pronounce all 5 quick practice words correctly
- ✅ Can hear difference between short/long vowels (a vs ā)
- ✅ Can identify retroflex vs dental consonants
- ✅ Can recite Gayatri Mantra with audio
- ✅ Can pronounce new words after hearing once
- ✅ Can recognize Sanskrit sounds in spoken Hindi

## 🙏 Cultural Note

**Pronunciation Matters**:
- Vedic Sanskrit is sacred language
- Correct pronunciation is respectful
- Mantras traditionally passed orally (śruti - "that which is heard")
- Audio feature honors oral tradition
- Use with reverence and practice

---

**Happy Learning! शुभ अध्ययनम्! 🕉️🔊**

*"Sound is Brahman" - श्रुति tradition*
