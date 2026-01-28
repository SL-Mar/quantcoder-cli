"""Storage and management for article summaries."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class IndividualSummary:
    """Summary of a single article."""
    article_id: int
    title: str
    authors: str
    url: str
    strategy_type: str
    key_concepts: List[str]
    indicators: List[str]
    risk_approach: str
    summary_text: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "IndividualSummary":
        return cls(**data)


@dataclass
class ConsolidatedSummary:
    """Consolidated summary from multiple articles."""
    summary_id: int
    source_article_ids: List[int]
    references: List[Dict]  # [{id, title, contribution}, ...]
    merged_strategy_type: str
    merged_description: str
    contributions_by_article: Dict[int, str]  # {article_id: "what it contributes"}
    key_concepts: List[str]
    indicators: List[str]
    risk_approach: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_consolidated: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ConsolidatedSummary":
        return cls(**data)


class SummaryStore:
    """Manages storage and retrieval of article summaries."""

    def __init__(self, base_dir: Path):
        """Initialize summary store.

        Args:
            base_dir: Base directory for storage (e.g., ~/.quantcoder)
        """
        self.base_dir = Path(base_dir)
        self.summaries_dir = self.base_dir / "summaries"
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.summaries_dir / "index.json"
        self._load_index()

    def _load_index(self):
        """Load the summary index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "individual": {},  # article_id -> summary_id
                "consolidated": {},  # summary_id -> {source_ids, ...}
                "next_id": 1
            }
            self._save_index()

    def _save_index(self):
        """Save the summary index."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def _get_next_id(self) -> int:
        """Get next available summary ID."""
        next_id = self.index["next_id"]
        self.index["next_id"] = next_id + 1
        self._save_index()
        return next_id

    def save_individual(self, summary: IndividualSummary) -> int:
        """Save an individual article summary.

        Args:
            summary: The individual summary to save

        Returns:
            The summary ID
        """
        # Check if already exists
        article_id_str = str(summary.article_id)
        if article_id_str in self.index["individual"]:
            summary_id = self.index["individual"][article_id_str]
        else:
            summary_id = self._get_next_id()
            self.index["individual"][article_id_str] = summary_id
            self._save_index()

        # Save summary file
        summary_file = self.summaries_dir / f"summary_{summary_id}.json"
        data = summary.to_dict()
        data["summary_id"] = summary_id
        data["is_consolidated"] = False

        with open(summary_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved individual summary {summary_id} for article {summary.article_id}")
        return summary_id

    def save_consolidated(self, summary: ConsolidatedSummary) -> int:
        """Save a consolidated summary.

        Args:
            summary: The consolidated summary to save

        Returns:
            The summary ID
        """
        summary_id = self._get_next_id()
        summary.summary_id = summary_id

        # Update index
        self.index["consolidated"][str(summary_id)] = {
            "source_ids": summary.source_article_ids,
            "created_at": summary.created_at
        }
        self._save_index()

        # Save summary file
        summary_file = self.summaries_dir / f"summary_{summary_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary.to_dict(), f, indent=2)

        logger.info(f"Saved consolidated summary {summary_id} from articles {summary.source_article_ids}")
        return summary_id

    def get_summary(self, summary_id: int) -> Optional[Dict]:
        """Get a summary by ID.

        Args:
            summary_id: The summary ID

        Returns:
            Summary data dict or None
        """
        summary_file = self.summaries_dir / f"summary_{summary_id}.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                return json.load(f)
        return None

    def get_summary_id_for_article(self, article_id: int) -> Optional[int]:
        """Get summary ID for an article.

        Args:
            article_id: The article ID

        Returns:
            Summary ID or None
        """
        return self.index["individual"].get(str(article_id))

    def is_consolidated(self, summary_id: int) -> bool:
        """Check if a summary ID is consolidated.

        Args:
            summary_id: The summary ID

        Returns:
            True if consolidated
        """
        return str(summary_id) in self.index["consolidated"]

    def list_summaries(self) -> Dict:
        """List all summaries.

        Returns:
            Dict with individual and consolidated summaries
        """
        result = {
            "individual": [],
            "consolidated": []
        }

        # Individual summaries
        for article_id, summary_id in self.index["individual"].items():
            summary = self.get_summary(summary_id)
            if summary:
                result["individual"].append({
                    "summary_id": summary_id,
                    "article_id": int(article_id),
                    "title": summary.get("title", "Unknown"),
                    "strategy_type": summary.get("strategy_type", "Unknown")
                })

        # Consolidated summaries
        for summary_id, info in self.index["consolidated"].items():
            summary = self.get_summary(int(summary_id))
            if summary:
                result["consolidated"].append({
                    "summary_id": int(summary_id),
                    "source_article_ids": info["source_ids"],
                    "strategy_type": summary.get("merged_strategy_type", "hybrid"),
                    "created_at": info.get("created_at")
                })

        return result

    def get_individual_summaries(self, article_ids: List[int]) -> List[Dict]:
        """Get multiple individual summaries.

        Args:
            article_ids: List of article IDs

        Returns:
            List of summary dicts
        """
        summaries = []
        for article_id in article_ids:
            summary_id = self.get_summary_id_for_article(article_id)
            if summary_id:
                summary = self.get_summary(summary_id)
                if summary:
                    summaries.append(summary)
        return summaries
