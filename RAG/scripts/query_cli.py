import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import query_rag

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/query_cli.py \"<query>\" [template_name]")
        sys.exit(1)

    query = sys.argv[1]
    template_name = sys.argv[2] if len(sys.argv) > 2 else "default"
    result = query_rag(query, template_name=template_name)
    print(result)