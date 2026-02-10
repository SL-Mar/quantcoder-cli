"""Article processing module - adapted from legacy quantcli."""

import re
import ast
import logging
import pdfplumber
import spacy
from collections import defaultdict
from typing import Dict, List, Optional
from .llm import LLMHandler

logger = logging.getLogger(__name__)


class PDFLoader:
    """Handles loading and extracting text from PDF files."""

    def __init__(self):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    def load_pdf(self, pdf_path: str) -> str:
        """Load text from a PDF file."""
        self.logger.info(f"Loading PDF: {pdf_path}")
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    self.logger.debug(f"Extracted text from page {page_number}")
            self.logger.info("PDF loaded successfully")
        except FileNotFoundError:
            self.logger.error(f"PDF file not found: {pdf_path}")
        except Exception as e:
            self.logger.error(f"Failed to load PDF: {e}")
        return text


class TextPreprocessor:
    """Handles preprocessing of extracted text."""

    def __init__(self):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")
        self.url_pattern = re.compile(r'https?://\S+')
        self.phrase_pattern = re.compile(r'Electronic copy available at: .*', re.IGNORECASE)
        self.number_pattern = re.compile(r'^\d+\s*$', re.MULTILINE)
        self.multinew_pattern = re.compile(r'\n+')
        self.header_footer_pattern = re.compile(
            r'^\s*(Author|Title|Abstract)\s*$',
            re.MULTILINE | re.IGNORECASE
        )

    def preprocess_text(self, text: str) -> str:
        """Preprocess text by removing unnecessary elements."""
        self.logger.info("Starting text preprocessing")
        try:
            original_length = len(text)
            text = self.url_pattern.sub('', text)
            text = self.phrase_pattern.sub('', text)
            text = self.number_pattern.sub('', text)
            text = self.multinew_pattern.sub('\n', text)
            text = self.header_footer_pattern.sub('', text)
            text = text.strip()
            processed_length = len(text)
            self.logger.info(
                f"Text preprocessed: {original_length} -> {processed_length} characters"
            )
            return text
        except Exception as e:
            self.logger.error(f"Failed to preprocess text: {e}")
            return ""


class HeadingDetector:
    """Detects headings in text using NLP."""

    def __init__(self, model: str = "en_core_web_sm"):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")
        try:
            self.nlp = spacy.load(model)
            self.logger.info(f"SpaCy model '{model}' loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load SpaCy model '{model}': {e}")
            raise

    def detect_headings(self, text: str) -> List[str]:
        """Detect potential headings using NLP."""
        self.logger.info("Starting heading detection")
        headings = []
        try:
            doc = self.nlp(text)
            for sent in doc.sents:
                sent_text = sent.text.strip()
                # Simple heuristic: headings are short and title-cased
                if 2 <= len(sent_text.split()) <= 10 and sent_text.istitle():
                    headings.append(sent_text)
            self.logger.info(f"Detected {len(headings)} headings")
        except Exception as e:
            self.logger.error(f"Failed to detect headings: {e}")
        return headings


class SectionSplitter:
    """Splits text into sections based on detected headings."""

    def __init__(self):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    def split_into_sections(self, text: str, headings: List[str]) -> Dict[str, str]:
        """Split text into sections based on headings."""
        self.logger.info("Starting section splitting")
        sections = defaultdict(str)
        current_section = "Introduction"

        lines = text.split('\n')
        for line_number, line in enumerate(lines, start=1):
            line = line.strip()
            if line in headings:
                current_section = line
                self.logger.debug(f"Line {line_number}: New section - {current_section}")
            else:
                sections[current_section] += line + " "

        self.logger.info(f"Split text into {len(sections)} sections")
        return sections


class CodeValidator:
    """Validates Python code syntax."""

    def __init__(self):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    def validate_code(self, code: str) -> bool:
        """
        Validate Python code syntax.

        Args:
            code: Python code string to validate

        Returns:
            True if code is syntactically valid, False otherwise
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.logger.debug(f"Syntax error in code: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False


class KeywordAnalyzer:
    """Analyzes text sections to categorize sentences based on keywords."""

    def __init__(self):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")
        self.risk_management_keywords = {
            "drawdown", "volatility", "reduce", "limit", "risk", "risk-adjusted",
            "maximal drawdown", "market volatility", "bear markets", "stability",
            "sidestep", "reduce drawdown", "stop-loss", "position sizing", "hedging",
            "max loss", "capital at risk", "leverage", "margin", "var", "value at risk",
            "portfolio protection", "tail risk", "max exposure"
        }
        self.trading_signal_keywords = {
            "buy", "sell", "signal", "indicator", "trend", "sma", "moving average",
            "momentum", "rsi", "macd", "bollinger bands", "rachev ratio", "stay long",
            "exit", "market timing", "yield curve", "recession", "unemployment",
            "housing starts", "treasuries", "economic indicator",
            "ema", "atr", "adx", "stochastic", "vwap", "volume weighted",
            "crossover", "cross above", "cross below", "golden cross", "death cross",
            "overbought", "oversold", "divergence", "breakout", "breakdown",
            "mean reversion", "pairs trading", "factor", "alpha", "beta", "sharpe",
            "long entry", "short entry", "entry condition", "exit condition",
            "go long", "go short", "open position", "close position"
        }
        self.strategy_parameter_keywords = {
            "period", "threshold", "parameter", "lookback", "rebalance",
            "weight", "allocation", "window", "lag", "decay", "half-life",
            "z-score", "standard deviation", "percentile", "quantile",
            "top decile", "bottom decile", "holding period", "frequency",
            "daily", "weekly", "monthly", "intraday", "minute", "hourly"
        }
        # Pattern to match sentences with numbers near indicator names
        self._param_pattern = re.compile(
            r'(?:\d+[- ]?(?:day|period|bar|minute|hour|week|month))|'
            r'(?:(?:period|lookback|window)\s*(?:of|=|:)?\s*\d+)',
            re.IGNORECASE
        )
        self.irrelevant_patterns = [
            re.compile(r'figure \d+', re.IGNORECASE),
            re.compile(r'\[\d+\]'),
            re.compile(r'\(.*?\)'),
            re.compile(r'chart', re.IGNORECASE),
            re.compile(r'\bfigure\b', re.IGNORECASE),
            re.compile(r'performance chart', re.IGNORECASE),
            re.compile(r'\d{4}-\d{4}'),
            re.compile(r'^\s*$')
        ]

    def keyword_analysis(self, sections: Dict[str, str]) -> Dict[str, List[str]]:
        """Categorize sentences into trading signals and risk management."""
        self.logger.info("Starting keyword analysis")
        keyword_map = defaultdict(list)
        processed_sentences = set()

        for section, content in sections.items():
            for sent in content.split('. '):
                sent_text = sent.lower().strip()

                if any(pattern.search(sent_text) for pattern in self.irrelevant_patterns):
                    continue
                if sent_text in processed_sentences:
                    continue
                processed_sentences.add(sent_text)

                if any(kw in sent_text for kw in self.trading_signal_keywords):
                    keyword_map['trading_signal'].append(sent.strip())
                if any(kw in sent_text for kw in self.risk_management_keywords):
                    keyword_map['risk_management'].append(sent.strip())
                if (any(kw in sent_text for kw in self.strategy_parameter_keywords)
                        or self._param_pattern.search(sent_text)):
                    keyword_map['strategy_parameters'].append(sent.strip())

        # Remove duplicates and sort
        for category, sentences in keyword_map.items():
            unique_sentences = sorted(set(sentences), key=lambda x: len(x))
            keyword_map[category] = unique_sentences

        self.logger.info("Keyword analysis completed")
        return keyword_map


class ArticleProcessor:
    """Main processor for article extraction and code generation."""

    def __init__(self, config, max_refine_attempts: int = 6):
        self.config = config
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")
        self.pdf_loader = PDFLoader()
        self.preprocessor = TextPreprocessor()
        self.heading_detector = HeadingDetector()
        self.section_splitter = SectionSplitter()
        self.keyword_analyzer = KeywordAnalyzer()
        self.llm_handler = LLMHandler(config)
        self.max_refine_attempts = max_refine_attempts

    def extract_sections(self, pdf_path: str) -> Dict[str, str]:
        """Extract paper sections from PDF (no keyword filtering).

        Returns:
            Dict mapping section names to their full text.
        """
        self.logger.info(f"Extracting sections from PDF: {pdf_path}")

        raw_text = self.pdf_loader.load_pdf(pdf_path)
        if not raw_text:
            self.logger.error("No text extracted from PDF")
            return {}

        preprocessed_text = self.preprocessor.preprocess_text(raw_text)
        if not preprocessed_text:
            self.logger.error("Preprocessing failed")
            return {}

        headings = self.heading_detector.detect_headings(preprocessed_text)
        if not headings:
            self.logger.warning("No headings detected. Using default sectioning")

        sections = self.section_splitter.split_into_sections(preprocessed_text, headings)
        return dict(sections)

    def extract_structure(self, pdf_path: str) -> Dict[str, List[str]]:
        """Extract structured data from PDF (legacy keyword-filtered path)."""
        self.logger.info(f"Starting extraction for PDF: {pdf_path}")

        raw_text = self.pdf_loader.load_pdf(pdf_path)
        if not raw_text:
            self.logger.error("No text extracted from PDF")
            return {}

        preprocessed_text = self.preprocessor.preprocess_text(raw_text)
        if not preprocessed_text:
            self.logger.error("Preprocessing failed")
            return {}

        headings = self.heading_detector.detect_headings(preprocessed_text)
        if not headings:
            self.logger.warning("No headings detected. Using default sectioning")

        sections = self.section_splitter.split_into_sections(preprocessed_text, headings)
        keyword_analysis = self.keyword_analyzer.keyword_analysis(sections)

        return keyword_analysis

    def generate_summary(self, extracted_data: Dict[str, List[str]]) -> Optional[str]:
        """Generate summary from extracted data (legacy single-pass)."""
        return self.llm_handler.generate_summary(extracted_data)

    def generate_two_pass_summary(self, pdf_path: str) -> Optional[str]:
        """Two-pass LLM summarization: extract then interpret.

        Falls back to the legacy keyword-filtered path if either LLM pass fails.
        """
        self.logger.info("Starting two-pass summarization pipeline")

        # Step 1 — get full sections (no keyword filter)
        sections = self.extract_sections(pdf_path)
        if not sections:
            self.logger.warning("No sections extracted, falling back to legacy path")
            return self._legacy_summarize(pdf_path)

        # Step 2 — Pass 1: extract verbatim quotes
        extractions = self.llm_handler.extract_key_passages(sections)
        if not extractions:
            self.logger.warning("Pass 1 failed, falling back to legacy path")
            return self._legacy_summarize(pdf_path)

        # Step 3 — Pass 2: interpret into strategy spec
        summary = self.llm_handler.interpret_strategy(extractions)
        if not summary:
            self.logger.warning("Pass 2 failed, falling back to legacy path")
            return self._legacy_summarize(pdf_path)

        self.logger.info("Two-pass summarization complete")
        return summary

    def _legacy_summarize(self, pdf_path: str) -> Optional[str]:
        """Legacy single-pass summarization via KeywordAnalyzer + rigid template."""
        self.logger.info("Using legacy summarization path")
        extracted_data = self.extract_structure(pdf_path)
        if not extracted_data:
            return None
        return self.llm_handler.generate_summary(extracted_data)

    def extract_structure_and_generate_code(self, pdf_path: str) -> Dict:
        """Extract structure and generate QuantConnect code."""
        self.logger.info("Starting extraction and code generation")

        # Use two-pass pipeline (with automatic legacy fallback)
        summary = self.generate_two_pass_summary(pdf_path)
        if not summary:
            self.logger.error("Failed to generate summary")
            summary = "Summary could not be generated."

        # Generate code
        qc_code = self.llm_handler.generate_qc_code(summary)

        # Refine code if needed
        attempt = 0
        while qc_code and not self._validate_code(qc_code) and attempt < self.max_refine_attempts:
            self.logger.info(f"Attempt {attempt + 1} to refine code")
            qc_code = self.llm_handler.refine_code(qc_code)
            if qc_code and self._validate_code(qc_code):
                self.logger.info("Refined code is valid")
                break
            attempt += 1

        if not qc_code or not self._validate_code(qc_code):
            self.logger.error("Failed to generate valid code after multiple attempts")
            qc_code = "QuantConnect code could not be generated successfully."

        return {"summary": summary, "code": qc_code}

    def generate_code_from_summary(self, summary_text: str) -> Optional[str]:
        """Generate QuantConnect code from a pre-existing summary.

        Args:
            summary_text: The strategy summary text

        Returns:
            Generated QuantConnect code or None
        """
        self.logger.info("Generating code from summary text")

        if not summary_text:
            self.logger.error("Empty summary provided")
            return None

        # Generate code
        qc_code = self.llm_handler.generate_qc_code(summary_text)

        # Refine code if needed
        attempt = 0
        while qc_code and not self._validate_code(qc_code) and attempt < self.max_refine_attempts:
            self.logger.info(f"Attempt {attempt + 1} to refine code")
            qc_code = self.llm_handler.refine_code(qc_code)
            if qc_code and self._validate_code(qc_code):
                self.logger.info("Refined code is valid")
                break
            attempt += 1

        if not qc_code or not self._validate_code(qc_code):
            self.logger.error("Failed to generate valid code after multiple attempts")
            return "QuantConnect code could not be generated successfully."

        return qc_code

    def _validate_code(self, code: str) -> bool:
        """Validate code syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error in code: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
