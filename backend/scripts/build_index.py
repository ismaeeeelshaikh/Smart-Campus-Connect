"""Index backend/college_data/*.txt into the knowledge base.

The backend already does this at startup (only changed files are re-embedded), so you only need
this script to rebuild from scratch:

    python -m scripts.build_index --rebuild

Stop the backend first: two processes should not write to the same Chroma folder.
"""
import argparse
import logging
import shutil
from app.config import settings
from app.services.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO, format="%(message)s")

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--rebuild", action="store_true", help="delete the whole index first")
args = parser.parse_args()

chroma_dir = settings.backend_path(settings.chroma_dir)
if args.rebuild and chroma_dir.exists():
    shutil.rmtree(chroma_dir)
    print(f"Deleted {chroma_dir}")

kb = KnowledgeBase(chroma_dir, settings.embedding_model)
stats = kb.sync_folder(settings.backend_path(settings.college_data_dir))
print(f"Done: {stats}, {kb.collection.count()} chunks in the index")
