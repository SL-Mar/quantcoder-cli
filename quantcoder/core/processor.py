"""Article processing module - adapted from legacy quantcli."""

import re
import ast
import logging
import tempfile
import pdfplumber
import spacy
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from .llm import LLMHandler

logger = logging.getLogger(__name__)

try:
    from magic_pdf.pipe.UNIPipe import UNIPipe
    from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
    MINERU_AVAILABLE = True
except ImportError:
    MINERU_AVAILABLE = False


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


class MinerULoader:
    """Converts PDF to structured markdown using MinerU (magic-pdf)."""

    def __init__(self):
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    def load_and_split(self, pdf_path: str) -> Dict[str, str]:
        """Read PDF, run MinerU pipeline, return sections dict.

        Returns:
            Dict mapping section headings to their text content,
            with LaTeX equations preserved as ``$...$`` / ``$$...$$``.
        """
        self.logger.info(f"Loading PDF via MinerU: {pdf_path}")
        try:
            pdf_bytes = Path(pdf_path).read_bytes()
        except FileNotFoundError:
            self.logger.error(f"PDF file not found: {pdf_path}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to read PDF: {e}")
            return {}

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                image_writer = DiskReaderWriter(tmp_dir)
                pipe = UNIPipe(pdf_bytes, {"_pdf_type": "", "model_list": []}, image_writer)
                pipe.pipe_classify()
                pipe.pipe_analyze()
                pipe.pipe_parse()
                md_content = pipe.pipe_mk_markdown(tmp_dir, drop_mode="none")
        except Exception as e:
            self.logger.error(f"MinerU pipeline failed: {e}")
            return {}

        sections = self._parse_markdown_sections(md_content)
        self.logger.info(f"MinerU extracted {len(sections)} sections")
        return sections

    @staticmethod
    def _parse_markdown_sections(md_content: str) -> Dict[str, str]:
        """Split markdown on ``##`` headers into a sections dict.

        Text before the first heading is stored under ``"Introduction"``.
        LaTeX equations (``$...$``, ``$$...$$``) are preserved verbatim.

        Args:
            md_content: Raw markdown string from MinerU.

        Returns:
            Dict mapping heading text to section body.
        """
        if not md_content or not md_content.strip():
            return {}

        sections: Dict[str, str] = {}
        current_heading = "Introduction"
        current_lines: list[str] = []

        for line in md_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                # Store previous section
                body = "\n".join(current_lines).strip()
                if body:
                    sections[current_heading] = body
                current_heading = stripped.lstrip("# ").strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Store last section
        body = "\n".join(current_lines).strip()
        if body:
            sections[current_heading] = body

        return sections


class ArticleProcessor:
    """Main processor for article extraction and code generation."""

    def __init__(self, config, max_refine_attempts: int = 6, max_fidelity_attempts: int = 3):
        self.config = config
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

        pdf_backend = getattr(getattr(config, "tools", None), "pdf_backend", "auto")
        self._use_mineru = self._resolve_pdf_backend(pdf_backend)

        if self._use_mineru:
            self.logger.info("Using MinerU PDF backend")
            self._mineru_loader = MinerULoader()
        else:
            self.logger.info("Using pdfplumber PDF backend")

        # Legacy pdfplumber pipeline (always available for fallback)
        self.pdf_loader = PDFLoader()
        self.preprocessor = TextPreprocessor()
        self.heading_detector = HeadingDetector()
        self.section_splitter = SectionSplitter()
        self.keyword_analyzer = KeywordAnalyzer()

        self.llm_handler = LLMHandler(config)
        self.max_refine_attempts = max_refine_attempts
        self.max_fidelity_attempts = max_fidelity_attempts

    @staticmethod
    def _resolve_pdf_backend(pdf_backend: str) -> bool:
        """Determine whether to use MinerU based on config value.

        Args:
            pdf_backend: ``"auto"``, ``"mineru"``, or ``"pdfplumber"``.

        Returns:
            True if MinerU should be used, False for pdfplumber.

        Raises:
            ImportError: If ``"mineru"`` is requested but not installed.
        """
        if pdf_backend == "pdfplumber":
            return False
        if pdf_backend == "mineru":
            if not MINERU_AVAILABLE:
                raise ImportError(
                    "MinerU is not installed. Install with: pip install 'quantcoder-cli[mineru]'"
                )
            return True
        # "auto" — use MinerU if available
        return MINERU_AVAILABLE

    def extract_sections(self, pdf_path: str) -> Dict[str, str]:
        """Extract paper sections from PDF (no keyword filtering).

        Uses MinerU when configured, with automatic fallback to pdfplumber
        if MinerU returns empty results.

        Returns:
            Dict mapping section names to their full text.
        """
        if self._use_mineru:
            self.logger.info(f"Extracting sections via MinerU: {pdf_path}")
            sections = self._mineru_loader.load_and_split(pdf_path)
            if sections:
                return sections
            self.logger.warning(
                "MinerU returned empty results — falling back to pdfplumber"
            )

        return self._extract_sections_pdfplumber(pdf_path)

    def _extract_sections_pdfplumber(self, pdf_path: str) -> Dict[str, str]:
        """Extract sections using the legacy pdfplumber + SpaCy pipeline."""
        self.logger.info(f"Extracting sections via pdfplumber: {pdf_path}")

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

        qc_code = self.generate_code_from_summary(summary)
        if qc_code is None:
            qc_code = "QuantConnect code could not be generated successfully."

        return {"summary": summary, "code": qc_code}

    def generate_code_from_summary(self, summary_text: str) -> Optional[str]:
        """Generate QuantConnect code from a pre-existing summary.

        Uses a two-stage pipeline:
          Stage 1 — generate QC framework with method stubs for novel math.
          Stage 2 — fill stub methods with mathematical implementations.

        Falls back to single-shot ``generate_qc_code()`` if Stage 1 fails.
        Falls back to the Stage 1 framework if Stage 2 fails syntax checks.

        After both stages, runs the fidelity assessment loop (unchanged).

        Args:
            summary_text: The strategy summary text

        Returns:
            Generated QuantConnect code or None
        """
        self.logger.info("Generating code from summary text")

        if not summary_text:
            self.logger.error("Empty summary provided")
            return None

        # -- Phase 1: two-stage code generation + syntax validation -----------

        # Stage 1: framework with stubs (fall back to single-shot)
        qc_code = self.llm_handler.generate_qc_framework(summary_text)
        if not qc_code:
            self.logger.warning("Stage 1 failed, falling back to single-shot generate_qc_code")
            qc_code = self.llm_handler.generate_qc_code(summary_text)

        # Syntax validation loop on Stage 1 output
        attempt = 0
        while qc_code and not self._validate_code(qc_code) and attempt < self.max_refine_attempts:
            self.logger.info(f"Syntax refine attempt {attempt + 1}")
            qc_code = self.llm_handler.refine_code(qc_code)
            if qc_code and self._validate_code(qc_code):
                self.logger.info("Refined code is syntactically valid")
                break
            attempt += 1

        if not qc_code or not self._validate_code(qc_code):
            self.logger.error("Failed to generate syntactically valid code")
            return "QuantConnect code could not be generated successfully."

        # Stage 2: fill mathematical core (only if stubs detected)
        framework_code = qc_code  # save as fallback anchor
        if self._has_stub_methods(framework_code):
            self.logger.info("Stubs detected — running Stage 2 (fill mathematical core)")
            filled_code = self.llm_handler.fill_mathematical_core(
                summary_text, framework_code
            )

            if filled_code:
                # Syntax validation loop on Stage 2 output
                s2_attempt = 0
                while (
                    not self._validate_code(filled_code)
                    and s2_attempt < self.max_refine_attempts
                ):
                    self.logger.info(
                        f"Stage 2 syntax refine attempt {s2_attempt + 1}"
                    )
                    refined = self.llm_handler.refine_code(filled_code)
                    if refined and self._validate_code(refined):
                        filled_code = refined
                        break
                    elif refined:
                        filled_code = refined
                    s2_attempt += 1

                if self._validate_code(filled_code):
                    self.logger.info("Stage 2 code is syntactically valid")
                    qc_code = filled_code
                else:
                    self.logger.warning(
                        "Stage 2 code failed syntax validation — "
                        "keeping Stage 1 framework"
                    )
            else:
                self.logger.warning(
                    "Stage 2 returned no code — keeping Stage 1 framework"
                )
        else:
            self.logger.info("No stubs detected — skipping Stage 2")

        # -- Phase 1.5: QC API linting ----------------------------------------
        from .qc_linter import lint_qc_code

        lint_result = lint_qc_code(qc_code)
        if lint_result.had_fixes and self._validate_code(lint_result.code):
            self.logger.info(
                "QC linter applied %d auto-fixes",
                sum(1 for i in lint_result.issues if i.fixed),
            )
            qc_code = lint_result.code
        for hint in lint_result.unfixable_hints:
            self.logger.warning("QC linter warning: %s", hint)

        # -- Phase 2: fidelity assessment loop (unchanged) --------------------
        for fidelity_attempt in range(self.max_fidelity_attempts):
            self.logger.info(f"Fidelity assessment attempt {fidelity_attempt + 1}")

            assessment = self.llm_handler.assess_fidelity(summary_text, qc_code)

            if assessment.get("faithful") and assessment.get("score", 0) >= 3:
                self.logger.info(
                    f"Code passed fidelity check (score={assessment['score']})"
                )
                return qc_code

            self.logger.warning(
                f"Fidelity check failed (score={assessment.get('score', 0)}, "
                f"issues={assessment.get('issues', [])})"
            )

            # Regenerate with critique
            new_code = self.llm_handler.regenerate_with_critique(
                summary_text, qc_code, assessment
            )

            if not new_code:
                self.logger.warning("Regeneration returned no code, keeping previous version")
                continue

            # Mini syntax validation loop on the new code
            syntax_attempt = 0
            while not self._validate_code(new_code) and syntax_attempt < 3:
                self.logger.info(f"Syntax refine on regenerated code, attempt {syntax_attempt + 1}")
                refined = self.llm_handler.refine_code(new_code)
                if refined and self._validate_code(refined):
                    new_code = refined
                    break
                elif refined:
                    new_code = refined
                syntax_attempt += 1

            if self._validate_code(new_code):
                # Lint regenerated code too
                regen_lint = lint_qc_code(new_code)
                if regen_lint.had_fixes and self._validate_code(regen_lint.code):
                    new_code = regen_lint.code
                qc_code = new_code
            else:
                self.logger.warning("Regenerated code failed syntax validation, keeping previous version")

        # Graceful degradation: fidelity never passed, keep last valid code
        self.logger.warning(
            f"Fidelity assessment did not pass after {self.max_fidelity_attempts} "
            f"attempts — returning last syntactically valid code"
        )
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

    @staticmethod
    def _has_stub_methods(code: str) -> bool:
        """Detect whether *code* contains method stubs (def + docstring + pass).

        A stub is a ``def`` whose body consists of only an optional docstring
        followed by ``pass``.  We use a simple line-based heuristic:
        scan for ``pass`` lines and look backward for a preceding ``def``
        with only blank lines, comments, or docstring delimiters between.

        False positives are harmless (Stage 2 preserves non-stub code).
        """
        if not code:
            return False

        lines = code.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped != "pass":
                continue
            # Walk backward from this ``pass`` looking for a ``def``
            in_docstring = False
            j = i - 1
            while j >= 0:
                prev = lines[j].strip()
                # toggle docstring state on triple-quote lines
                if prev.startswith('"""') or prev.startswith("'''"):
                    if prev.count('"""') == 2 or prev.count("'''") == 2:
                        # single-line docstring — keep walking
                        j -= 1
                        continue
                    in_docstring = not in_docstring
                    j -= 1
                    continue
                if in_docstring:
                    j -= 1
                    continue
                # skip blank lines and comments
                if prev == "" or prev.startswith("#"):
                    j -= 1
                    continue
                # the first real statement should be a def
                if prev.startswith("def ") and prev.endswith(":"):
                    return True
                # anything else means this pass is not a stub
                break
        return False
