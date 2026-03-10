#!/usr/bin/env python3
import subprocess
import sys

# Install olefile for .doc format
subprocess.run([sys.executable, "-m", "pip", "install", "olefile", "-q"], check=True)

import olefile

filepath = "/mnt/c/Users/algoldsc/Documents/PriceProducerSystem.docx"

ole = olefile.OleFileIO(filepath)

# Word 97-2003 stores text in different streams
# Try to get text from various possible locations
text_parts = []

# Check for WordDocument stream (contains FIB and text)
if ole.exists("WordDocument"):
    word_doc = ole.openstream("WordDocument").read()

    # The FIB (File Information Block) tells us where text is
    # For complex docs, text may be in '1Table' or '0Table' stream
    # Let's try to read the text piece table

# Try reading from the Data stream or extracting unicode text
for stream_name in ole.listdir():
    stream_path = "/".join(stream_name)
    try:
        data = ole.openstream(stream_name).read()
        # Try UTF-16LE decoding (common in Word docs)
        try:
            decoded = data.decode("utf-16-le", errors="ignore")
            # Filter to get meaningful text runs
            import re

            chunks = re.findall(r"[A-Za-z0-9\s\.,;:!?\-\'\"()]{20,}", decoded)
            text_parts.extend(chunks)
        except:
            pass
    except:
        pass

# Also try direct byte extraction for ASCII text
if ole.exists("WordDocument"):
    word_doc = ole.openstream("WordDocument").read()
    # Extract ASCII sequences
    import re

    ascii_text = word_doc.decode("cp1252", errors="ignore")
    # Look for sentence-like patterns
    sentences = re.findall(
        r"[A-Z][a-z][A-Za-z0-9\s\.,;:!?\-\'\"()]{15,}[.!?]", ascii_text
    )
    text_parts.extend(sentences)

ole.close()

# Deduplicate and print
seen = set()
for part in text_parts:
    clean = part.strip()
    if clean and clean not in seen and len(clean) > 25:
        seen.add(clean)
        print(clean)
        print()
