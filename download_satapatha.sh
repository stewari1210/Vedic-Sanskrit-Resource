#!/bin/bash
# Download all 5 parts of Satapatha Brahmana from archive.org

echo "Downloading Satapatha Brahmana (5 parts)..."

# Part 1 - Books I-II (already downloaded, but re-download for consistency)
curl -L "https://archive.org/stream/satapathabrahmana00egge/satapathabrahmana00egge_djvu.txt" -o satapatha_brahmana_part1_books_1_2.txt
echo "✓ Part 1 (Books I-II) downloaded"

# Part 2 - Books III-IV
curl -L "https://archive.org/stream/satapathabrahman02egge/satapathabrahman02egge_djvu.txt" -o satapatha_brahmana_part2_books_3_4.txt
echo "✓ Part 2 (Books III-IV) downloaded"

# Part 3 - Books V-VII
curl -L "https://archive.org/stream/satapathabrahman03egge/satapathabrahman03egge_djvu.txt" -o satapatha_brahmana_part3_books_5_7.txt
echo "✓ Part 3 (Books V-VII) downloaded"

# Part 4 - Books VIII-X
curl -L "https://archive.org/stream/satapathabrahman04egge/satapathabrahman04egge_djvu.txt" -o satapatha_brahmana_part4_books_8_10.txt
echo "✓ Part 4 (Books VIII-X) downloaded"

# Part 5 - Books XI-XIV
curl -L "https://archive.org/stream/satapathabrahman05egge/satapathabrahman05egge_djvu.txt" -o satapatha_brahmana_part5_books_11_14.txt
echo "✓ Part 5 (Books XI-XIV) downloaded"

echo ""
echo "All 5 parts downloaded successfully!"
ls -lh satapatha_brahmana_part*.txt
