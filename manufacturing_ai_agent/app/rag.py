"""
Lightweight local RAG: chunks every markdown file in app/knowledge_base
by its '##' section headers, builds a TF-IDF index over the chunks,
and exposes search() for semantic-ish keyword retrieval. No external
services or embedding API required — this mirrors the "v1: TF-IDF"
architecture from the project brief. Swap this module out for an
embedding model + FAISS/Chroma/Qdrant later without touching callers.
"""
import os
import re
from dataclasses import dataclass
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


class KnowledgeBase:
    def __init__(self, kb_dir: str = KB_DIR):
        self.kb_dir = kb_dir
        self.chunks: List[Chunk] = []
        self.vectorizer = None
        self.matrix = None
        self._load()

    def _load(self):
        self.chunks = []
        for fname in sorted(os.listdir(self.kb_dir)):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(self.kb_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.chunks.extend(self._split_into_chunks(fname, content))

        if not self.chunks:
            return

        corpus = [f"{c.heading}\n{c.text}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(corpus)

    @staticmethod
    def _split_into_chunks(fname: str, content: str) -> List[Chunk]:
        # Split on '## ' headings (level-2). Keep the doc title (level-1)
        # prefixed onto the first chunk for context.
        parts = re.split(r"\n(?=## )", content)
        chunks = []
        doc_title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
        doc_title = doc_title_match.group(1) if doc_title_match else fname
        for part in parts:
            part = part.strip()
            if not part:
                continue
            heading_match = re.match(r"^#{1,2} (.+)$", part, re.MULTILINE)
            heading = heading_match.group(1) if heading_match else doc_title
            # Skip trivially short chunks (e.g. stray fragments)
            if len(part) < 40:
                continue
            chunks.append(Chunk(source=fname, heading=heading, text=part))
        return chunks

    def search(self, query: str, top_k: int = 3):
        if not self.chunks or self.vectorizer is None:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results = []
        for i in ranked[:top_k]:
            if scores[i] <= 0:
                continue
            c = self.chunks[i]
            results.append(
                {
                    "source": c.source,
                    "heading": c.heading,
                    "score": round(float(scores[i]), 4),
                    "text": c.text,
                }
            )
        return results


# Singleton index built once at import time (reload the process to pick
# up knowledge-base file edits, or call kb_index.reload()).
kb_index = KnowledgeBase()
