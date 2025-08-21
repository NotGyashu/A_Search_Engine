import cProfile
import pstats
import json
from pathlib import Path

# --- IMPORTANT ---
# Import the necessary classes from your project
from processor import DocumentProcessor
from file_reader import FileReader

# --- CONFIGURATION ---
# 1. SET THE PATH TO ONE OF YOUR LARGE JSON FILES
FILE_TO_PROFILE = Path("../RawHTMLdata/batch_20250815_154631_8.json")

# 2. SET THE FILENAME FOR THE PROFILING OUTPUT
PROFILE_OUTPUT_FILE = "profile_output.pstats"

def profile_single_document():
    """
    Profiles the processing of a single document from a large file
    to identify CPU bottlenecks in the core logic.
    """
    if not FILE_TO_PROFILE.exists():
        print(f"Error: The file '{FILE_TO_PROFILE}' was not found.")
        return

    print(f"Starting profiling run for: {FILE_TO_PROFILE}")

    # Initialize the components needed for processing
    file_reader = FileReader()
    processor = DocumentProcessor()

    # Read just the first document from the specified JSON file
    try:
        raw_doc = next(file_reader.read_json_file(FILE_TO_PROFILE))
        print("Successfully read one document from the file.")
    except StopIteration:
        print("Error: The file is empty or contains no valid documents.")
        return
    except Exception as e:
        print(f"Error reading document from file: {e}")
        return

    # --- Profiling Execution ---
    profiler = cProfile.Profile()
    profiler.enable()

    # Run the core processing function
    processed_result = processor.process_document(raw_doc)

    profiler.disable()
    # --- End Profiling ---

    if processed_result:
        doc_count = len(processed_result.get("documents", []))
        chunk_count = len(processed_result.get("chunks", []))
        print(f"Processing successful: Created {doc_count} document and {chunk_count} chunks.")
    else:
        print("Processing failed or the document was skipped.")

    # Save the profiling stats to a file
    profiler.dump_stats(PROFILE_OUTPUT_FILE)
    print(f"\nProfiling complete. Results saved to '{PROFILE_OUTPUT_FILE}'")
    print("Please share this output file with me for analysis.")

if __name__ == "__main__":
    profile_single_document()

