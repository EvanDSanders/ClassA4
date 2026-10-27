import sys

from prs.cli import CLI

if __name__ == "__main__":
    CLI(use_ollama="--ollama" in sys.argv).run()
