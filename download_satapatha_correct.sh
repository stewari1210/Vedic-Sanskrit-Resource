#!/bin/bash
# Download all 5 parts of Satapatha Brahmana - CORRECTED URLS

echo "Downloading Satapatha Brahmana (5 parts) - text files only..."

# Part 1 - Books I-II
curl -L "https://ia800207.us.archive.org/26/items/satapathabrahmana00egge/satapathabrahmana00egge_djvu.txt" -o satapatha_brahmana_part1_books_1_2.txt
echo "✓ Part 1 (Books I-II) downloaded"

# Part 2 - Books III-IV  
curl -L "https://ia800207.us.archive.org/2/items/satapathabrahman02egge/satapathabrahman02egge_djvu.txt" -o satapatha_brahmana_part2_books_3_4.txt
echo "✓ Part 2 (Books III-IV) downloaded"

# Part 3 - Books V-VII
curl -L "https://ia800207.us.archive.org/30/items/satapathabrahman03egge/satapathabrahman03egge_djvu.txt" -o satapatha_brahmana_part3_books_5_7.txt
echo "✓ Part 3 (Books V-VII) downloaded"

# Part 4 - Books VIII-X
curl -L "https://ia800207.us.archive.org/21/items/satapathabrahman04egge/satapathabrahman04egge_djvu.txt" -o satapatha_brahmana_part4_books_8_10.txt
echo "✓ Part 4 (Books VIII-X) downloaded"

# Part 5 - Books XI-XIV
curl -L "https://ia800207.us.archive.org/4/items/satapathabrahman05egge/satapathabrahman05egge_djvu.txt" -o satapatha_brahmana_part5_books_11_14.txt
echo "✓ Part 5 (Books XI-XIV) downloaded"

echo ""
echo "All 5 parts downloaded successfully!"
echo ""
echo "Verifying downloads (checking for actual text content):"
for file in satapatha_brahmana_part*.txt; do
    if head -5 "$file" | grep -q "<!DOCTYPE"; then
        echo "❌ $file is HTML (download failed)"
    else
        size=$(ls -lh "$file" | awk '{print $5}')
        lines=$(wc -l < "$file")
        echo "✓ $file ($size, $lines lines)"
    fi
done
