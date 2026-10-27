import argparse

from prs.ai import KeywordFallbackClassifier, OllamaClassifier
from prs.cli import CLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", metavar="MODEL",
                       help="use a local Ollama model (localhost) instead of expressgameserver")
    group.add_argument("--keyword", action="store_true",
                       help="use the keyword fallback (test substitute, NOT AI)")
    args = parser.parse_args()
    if args.local:
        model = OllamaClassifier(args.local, OllamaClassifier.LOCAL_URL)
    elif args.keyword:
        model = KeywordFallbackClassifier()
    else:
        model = None
    CLI(model=model).run()
