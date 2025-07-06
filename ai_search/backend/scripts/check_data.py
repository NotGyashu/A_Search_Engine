#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Get the project root directory (three levels up from this script)
project_root = Path(__file__).parent.parent.parent.parent
db_path = project_root / "data" / "processed" / "documents.db"

# Connect to database
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get statistics
cursor.execute('SELECT COUNT(*) FROM documents')
total_docs = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT domain) FROM documents')
unique_domains = cursor.fetchone()[0]

cursor.execute('SELECT SUM(word_count) FROM documents')
total_words = cursor.fetchone()[0]

cursor.execute('SELECT domain, COUNT(*) as count FROM documents GROUP BY domain ORDER BY count DESC LIMIT 5')
top_domains = cursor.fetchall()

print("📊 DATABASE STATISTICS")
print("=" * 30)
print(f"Total documents: {total_docs:,}")
print(f"Unique domains: {unique_domains}")
print(f"Total words: {total_words:,}")
print(f"Average words per doc: {total_words//total_docs if total_docs > 0 else 0}")

print("\n🏆 TOP DOMAINS:")
for domain, count in top_domains:
    print(f"  {domain}: {count} pages")

# Get some sample titles
cursor.execute('SELECT title, domain, word_count FROM documents ORDER BY word_count DESC LIMIT 5')
samples = cursor.fetchall()

print("\n📄 SAMPLE DOCUMENTS (by word count):")
for title, domain, word_count in samples:
    print(f"  • {title[:60]}... ({domain}) - {word_count} words")

conn.close()
