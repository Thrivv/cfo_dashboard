import sys
import os

# Add the project root to the Python path to allow for absolute imports
# This is a bit of a hack, a better solution would be to have a proper package structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pages.AI_Assistant import route_question, _init_embedding_model

def classify_queries_from_file(file_path):
    """
    Reads questions from a file and classifies them using the route_question function.
    """
    try:
        with open(file_path, 'r') as f:
            questions = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return

    # Initialize the embedding model once
    print("Initializing embedding model...")
    _init_embedding_model()
    print("Model initialized.")

    print("\n--- Classification Results ---")
    for question in questions:
        category, method = route_question(question)
        print(f"Question: \"{question}\"")
        print(f"  -> Classification: {category}, Method: {method}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = '/home/rohith/Git_Thrivv/Git_Use_Thrivv/cfo_runpod_working(10_nov)/cfo_dashboard/Query_test/Financial_queries.txt' # Default file path

    classify_queries_from_file(file_path)
