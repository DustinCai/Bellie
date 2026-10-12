import os
import sys

# retrieve.py and generate.py build API clients at import time, so dummy keys
# must be set before main is imported. Real calls are mocked out in the tests.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ["BELLIE_API_KEY"] = "test-bellie-key"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
