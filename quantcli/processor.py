"""
Package  
===============

Author: S.

Description:
------------
This script processes a PDF article to extract trading strategy and risk management information. It generates a summary and 
produces QuantConnect Python code for algorithmic trading based on the extracted data. The script utilizes OpenAI's language 
models for summarization and code generation, and presents the results in a graphical user interface (GUI) built with Tkinter.

LLM used : GPT-4o-latest preferred

License:
--------
This project is licensed under the MIT License. You are free to use, modify, and distribute this software. See the LICENSE file 
for more details.
"""

import re
import pdfplumber
import spacy
from collections import defaultdict
from typing import Dict, List, Optional
import os
import logging
from dotenv import load_dotenv, find_dotenv
import ast
# tkinter imports moved to GUI class methods (lazy loading)
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name
import subprocess

from .llm_client import LLMClient

class PDFLoader:
    """Handles loading and extracting text from PDF files."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_pdf(self, pdf_path: str) -> str:
        """
        Load the text from a PDF file using pdfplumber for better accuracy.
        """
        self.logger.info(f"Loading PDF: {pdf_path}")
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    self.logger.debug(f"Extracted text from page {page_number}.")
            self.logger.info("PDF loaded successfully.")
        except FileNotFoundError:
            self.logger.error(f"PDF file not found: {pdf_path}")
        except Exception as e:
            self.logger.error(f"Failed to load PDF: {e}")
        return text

class TextPreprocessor:
    """Handles preprocessing of extracted text."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # Precompile regex patterns for performance
        self.url_pattern = re.compile(r'https?://\S+')
        self.phrase_pattern = re.compile(r'Electronic copy available at: .*', re.IGNORECASE)
        self.number_pattern = re.compile(r'^\d+\s*$', re.MULTILINE)
        self.multinew_pattern = re.compile(r'\n+')
        self.header_footer_pattern = re.compile(r'^\s*(Author|Title|Abstract)\s*$', re.MULTILINE | re.IGNORECASE)

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess the text by removing headers, footers, references, and unnecessary whitespace.
        """
        self.logger.info("Starting text preprocessing.")
        try:
            original_length = len(text)
            text = self.url_pattern.sub('', text)
            text = self.phrase_pattern.sub('', text)
            text = self.number_pattern.sub('', text)
            text = self.multinew_pattern.sub('\n', text)
            text = self.header_footer_pattern.sub('', text)
            text = text.strip()
            processed_length = len(text)
            self.logger.info(f"Text preprocessed successfully. Reduced from {original_length} to {processed_length} characters.")
            return text
        except Exception as e:
            self.logger.error(f"Failed to preprocess text: {e}")
            return ""

class HeadingDetector:
    """Detects headings in the text using NLP techniques."""

    def __init__(self, model: str = "en_core_web_sm"):
        self.logger = logging.getLogger(self.__class__.__name__)
        try:
            self.nlp = spacy.load(model)
            self.logger.info(f"SpaCy model '{model}' loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load SpaCy model '{model}': {e}")
            raise

    def detect_headings(self, text: str) -> List[str]:
        """
        Detect potential headings using NLP techniques.
        """
        self.logger.info("Starting heading detection.")
        headings = []
        try:
            doc = self.nlp(text)
            for sent in doc.sents:
                sent_text = sent.text.strip()
                # Simple heuristic: headings are short and title-cased
                if 2 <= len(sent_text.split()) <= 10 and sent_text.istitle():
                    headings.append(sent_text)
            self.logger.info(f"Detected {len(headings)} headings.")
        except Exception as e:
            self.logger.error(f"Failed to detect headings: {e}")
        return headings

class SectionSplitter:
    """Splits text into sections based on detected headings."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def split_into_sections(self, text: str, headings: List[str]) -> Dict[str, str]:
        """
        Split the text into sections based on the detected headings.
        """
        self.logger.info("Starting section splitting.")
        sections = defaultdict(str)
        current_section = "Introduction"  # Default section

        lines = text.split('\n')
        for line_number, line in enumerate(lines, start=1):
            line = line.strip()
            if line in headings:
                current_section = line
                self.logger.debug(f"Line {line_number}: New section detected - {current_section}")
            else:
                sections[current_section] += line + " "

        self.logger.info(f"Split text into {len(sections)} sections.")
        return sections

class KeywordAnalyzer:
    """Analyzes text sections to categorize sentences based on keywords."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.risk_management_keywords = {
            "drawdown", "volatility", "reduce", "limit", "risk", "risk-adjusted",
            "maximal drawdown", "market volatility", "bear markets", "stability",
            "sidestep", "reduce drawdown", "stop-loss", "position sizing", "hedging"
        }
        self.trading_signal_keywords = {
            "buy", "sell", "signal", "indicator", "trend", "sma", "moving average",
            "momentum", "rsi", "macd", "bollinger bands", "rachev ratio", "stay long",
            "exit", "market timing", "yield curve", "recession", "unemployment",
            "housing starts", "treasuries", "economic indicator"
        }
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
        """
        Categorize sentences into trading signals and risk management based on keywords.
        """
        self.logger.info("Starting keyword analysis.")
        keyword_map = defaultdict(list)
        processed_sentences = set()

        for section, content in sections.items():
            for sent in content.split('. '):  # Simple sentence split; consider using NLP for better accuracy
                sent_text = sent.lower().strip()
                
                if any(pattern.search(sent_text) for pattern in self.irrelevant_patterns):
                    self.logger.debug(f"Irrelevant sentence skipped: {sent_text}")
                    continue
                if sent_text in processed_sentences:
                    self.logger.debug(f"Duplicate sentence skipped: {sent_text}")
                    continue
                processed_sentences.add(sent_text)
                
                if any(kw in sent_text for kw in self.trading_signal_keywords):
                    keyword_map['trading_signal'].append(sent.strip())
                elif any(kw in sent_text for kw in self.risk_management_keywords):
                    keyword_map['risk_management'].append(sent.strip())

        # Remove duplicates and sort
        for category, sentences in keyword_map.items():
            unique_sentences = sorted(set(sentences), key=lambda x: len(x))
            keyword_map[category] = unique_sentences

        self.logger.info("Keyword analysis completed.")
        return keyword_map

class OpenAIHandler:
    """Handles interactions with the OpenAI API."""

    def __init__(self, model: str = "gpt-4o-2024-11-20"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model
        self.llm_client = LLMClient(model=model)

    def generate_summary(self, extracted_data: Dict[str, List[str]]) -> Optional[str]:
        """
        Generate a summary of the trading strategy and risk management based on extracted data.
        """
        self.logger.info("Generating summary using OpenAI.")
        trading_signals = '\n'.join(extracted_data.get('trading_signal', []))
        risk_management = '\n'.join(extracted_data.get('risk_management', []))

        prompt = f"""Provide a clear and concise summary of the following trading strategy and its associated risk management rules. Ensure the explanation is understandable to traders familiar with basic trading concepts and is no longer than 300 words.

        ### Trading Strategy Overview:
        - Core Strategy: Describe the primary trading approach, including any specific indicators, time frames (e.g., 5-minute), and entry/exit rules.
        - Stock Selection: Highlight any stock filters (e.g., liquidity, trading volume thresholds, or price conditions) used to choose which stocks to trade.
        - Trade Signals: Explain how the strategy determines whether to go long or short, including any conditions based on candlestick patterns or breakouts.

        {trading_signals}

        ### Risk Management Rules:
        - Stop Loss: Describe how stop-loss levels are set (e.g., 10% ATR) and explain the position-sizing rules (e.g., 1% of capital at risk per trade).
        - Exit Conditions: Clarify how and when positions are closed (e.g., at the end of the trading day or if certain price targets are hit).
        - Additional Constraints: Mention any leverage limits or other risk controls (e.g., maximum leverage of 4x, focusing on Stocks in Play).

        {risk_management}

        Summarize the details in a practical and structured format.
        """

        summary = self.llm_client.simple_prompt(
            system_message="You are an algorithmic trading expert.",
            user_message=prompt,
            max_tokens=1000,
            temperature=0.5
        )

        if summary:
            self.logger.info("Summary generated successfully.")
        else:
            self.logger.error("Failed to generate summary.")

        return summary

    def generate_qc_code(self, summary: str) -> Optional[str]:
        """
        Generate QuantConnect Python code based on extracted data.
        """
        self.logger.info("Generating QuantConnect code using OpenAI.")
        #trading_signals = '\n'.join(extracted_data.get('trading_signal', []))
        #risk_management = '\n'.join(extracted_data.get('risk_management', []))

        prompt = f"""
        You are a QuantConnect algorithm developer. Convert the following trading strategy descriptions into a complete, error-free QuantConnect Python algorithm.

        ### Trading Strategy Summary:
        {summary}

        ### Requirements:
        1. **Initialize Method**:
            - Set the start and end dates.
            - Set the initial cash.
            - Define the universe selection logic as described in trading strategy summary. 
            - Initialize required indicators as described in summary.
        2. **OnData Method**:
            - Implement buy/sell logic as described in summary. 
            - Ensure indicators are updated correctly.
        3. **Risk Management**:
            - Apply position sizing or stop-loss mechanisms as described in summary. 
        4. **Ensure Compliance**:
            - Use only QuantConnect's supported indicators and methods.
            - The code must be syntactically correct and free of errors.
        ```

        ### Generated Code:
        ```
        # The LLM will generate the code after this line
        ```
        """

        generated_code = self.llm_client.simple_prompt(
            system_message="You are a helpful assistant specialized in generating QuantConnect algorithms in Python.",
            user_message=prompt,
            max_tokens=1500,
            temperature=0.3
        )

        if generated_code:
            self.logger.info("QuantConnect code generated successfully.")
        else:
            self.logger.error("Failed to generate QuantConnect code.")

        return generated_code
        
    def refine_code(self, code: str) -> Optional[str]:
        """
        Ask the LLM to fix syntax errors in the generated code.
        """
        self.logger.info("Refining generated code using OpenAI.")
        prompt = f"""
        The following QuantConnect Python code may have syntax or logical errors. Please fix them as required and provide the corrected code.

        ```python
        {code}
        ```
        """

        corrected_code = self.llm_client.simple_prompt(
            system_message="You are an expert in QuantConnect Python algorithms.",
            user_message=prompt,
            max_tokens=1500,
            temperature=0.2
        )

        if corrected_code:
            # Extract code block
            code_match = re.search(r'```python(.*?)```', corrected_code, re.DOTALL | re.IGNORECASE)
            if code_match:
                corrected_code = code_match.group(1).strip()
            self.logger.info("Code refined successfully.")
            return corrected_code
        else:
            self.logger.error("Failed to refine code.")
            return None

class CodeValidator:
    """Validates Python code for syntax correctness."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_code(self, code: str) -> bool:
        """
        Validate the generated code for syntax errors.
        """
        self.logger.info("Validating generated code for syntax errors.")
        try:
            ast.parse(code)
            self.logger.info("Generated code is syntactically correct.")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error in generated code: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during code validation: {e}")
            return False

class CodeRefiner:
    """Refines code by fixing syntax errors using OpenAI."""

    def __init__(self, openai_handler: OpenAIHandler):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.openai_handler = openai_handler

    def refine_code(self, code: str) -> Optional[str]:
        """
        Refine the code by fixing syntax errors.
        """
        self.logger.info("Refining code using OpenAI.")
        return self.openai_handler.refine_code(code)

class GUI:
    """Handles the graphical user interface using Tkinter."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def display_summary_and_code(self, summary: str, code: str):
        """
        Display the summary and the generated code side by side with syntax highlighting.
        """
        self.logger.info("Displaying summary and code in GUI.")
        try:
            # Lazy import tkinter (only when GUI is actually used)
            import tkinter as tk
            from tkinter import scrolledtext, messagebox, filedialog

            # Create the main Tkinter root
            root = tk.Tk()
            root.title("Article Processor")
            root.geometry("1200x800")
            root.configure(bg="#F0F0F0")

            # Configure grid layout
            root.columnconfigure(0, weight=1)
            root.columnconfigure(1, weight=1)
            root.rowconfigure(0, weight=1)

            # Summary Frame
            summary_frame = tk.Frame(root, bg="#FFFFFF", padx=10, pady=10)
            summary_frame.grid(row=0, column=0, sticky='nsew')

            summary_label = tk.Label(
                summary_frame, text="Article Summary", font=("Arial", 16, "bold"), bg="#FFFFFF"
            )
            summary_label.pack(pady=(0, 10))

            summary_text = scrolledtext.ScrolledText(
                summary_frame, wrap=tk.WORD, font=("Arial", 12)
            )
            summary_text.pack(expand=True, fill='both')
            summary_text.insert(tk.END, summary)
            summary_text.configure(state='disabled')  # Make it read-only

            # Add copy button in summary_frame
            copy_summary_btn = tk.Button(
                summary_frame, text="Copy Summary", command=lambda: self.copy_to_clipboard(summary)
            )
            copy_summary_btn.pack(pady=5)

            # Code Frame
            code_frame = tk.Frame(root, bg="#2B2B2B", padx=10, pady=10)
            code_frame.grid(row=0, column=1, sticky='nsew')

            code_label = tk.Label(
                code_frame,
                text="Generated QuantConnect Code",
                font=("Arial", 16, "bold"),
                fg="#FFFFFF",
                bg="#2B2B2B",
            )
            code_label.pack(pady=(0, 10))

            code_text = scrolledtext.ScrolledText(
                code_frame,
                wrap=tk.NONE,
                font=("Consolas", 12),
                bg="#2B2B2B",
                fg="#F8F8F2",
                insertbackground="#FFFFFF",
            )
            code_text.pack(expand=True, fill='both')

            # Apply syntax highlighting
            self.apply_syntax_highlighting(code, code_text)

            code_text.configure(state='disabled')  # Make it read-only

            # Add copy and save buttons in code_frame
            copy_code_btn = tk.Button(
                code_frame, text="Copy Code", command=lambda: self.copy_to_clipboard(code)
            )
            copy_code_btn.pack(pady=5)

            save_code_btn = tk.Button(
                code_frame, text="Save Code", command=lambda: self.save_code(code)
            )
            save_code_btn.pack(pady=5)

            # Start the Tkinter event loop
            root.mainloop()
        except Exception as e:
            self.logger.error(f"Failed to display GUI: {e}")
            try:
                from tkinter import messagebox
                messagebox.showerror("GUI Error", f"An error occurred while displaying the GUI: {e}")
            except ImportError:
                pass  # Silently fail if tkinter not available

    def apply_syntax_highlighting(self, code: str, text_widget):
        """
        Apply syntax highlighting to the code using Pygments and insert it into the Text widget.
        """
        self.logger.info("Applying syntax highlighting to code.")
        try:
            # Lazy import tkinter
            import tkinter as tk

            lexer = PythonLexer()
            style = get_style_by_name('monokai')  # Choose a Pygments style
            token_colors = {
                'Token.Keyword': '#F92672',
                'Token.Name.Builtin': '#A6E22E',
                'Token.Literal.String': '#E6DB74',
                'Token.Operator': '#F8F8F2',
                'Token.Punctuation': '#F8F8F2',
                'Token.Comment': '#75715E',
                'Token.Name.Function': '#66D9EF',
                'Token.Name.Class': '#A6E22E',
                'Token.Text': '#F8F8F2',  # Default text color
                # Add more mappings as needed
            }

            # Define tags in the Text widget
            for token, color in token_colors.items():
                text_widget.tag_config(token, foreground=color)

            # Tokenize the code using Pygments
            tokens = lex(code, lexer)

            # Enable the widget to insert text
            text_widget.configure(state='normal')
            text_widget.delete(1.0, tk.END)  # Clear existing text

            # Insert tokens with appropriate tags
            for token, content in tokens:
                token_type = str(token)
                tag = token_type if token_type in token_colors else 'Token.Text'
                text_widget.insert(tk.END, content, tag)

            # Re-enable the widget
            text_widget.configure(state='disabled')
        except Exception as e:
            self.logger.error(f"Failed to apply syntax highlighting: {e}")
            text_widget.insert(tk.END, code)  # Fallback: insert without highlighting

    def copy_to_clipboard(self, text: str):
        """
        Copies the given text to the system clipboard.
        """
        self.logger.info("Copying text to clipboard.")
        try:
            # Lazy import tkinter
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()  # Now it stays on the clipboard after the window is closed
            root.destroy()
            messagebox.showinfo("Copied", "Text copied to clipboard.")
        except Exception as e:
            self.logger.error(f"Failed to copy to clipboard: {e}")
            try:
                from tkinter import messagebox
                messagebox.showerror("Copy Error", f"Failed to copy text to clipboard: {e}")
            except ImportError:
                pass  # Silently fail if tkinter not available

    def save_code(self, code: str):
        """
        Saves the generated code to a file selected by the user.
        """
        self.logger.info("Saving code to file.")
        try:
            # Lazy import tkinter
            from tkinter import filedialog, messagebox

            filetypes = [('Python Files', '*.py'), ('All Files', '*.*')]
            filename = filedialog.asksaveasfilename(
                title="Save Code", defaultextension=".py", filetypes=filetypes
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write(code)
                messagebox.showinfo("Saved", f"Code saved to {filename}.")
        except Exception as e:
            self.logger.error(f"Failed to save code: {e}")
            try:
                from tkinter import messagebox
                messagebox.showerror("Save Error", f"Failed to save code: {e}")
            except ImportError:
                pass  # Silently fail if tkinter not available

class ArticleProcessor:
    """Main processor that orchestrates the PDF processing, analysis, and code generation."""

    def __init__(self, max_refine_attempts: int = 6):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pdf_loader = PDFLoader()
        self.preprocessor = TextPreprocessor()
        self.heading_detector = HeadingDetector()
        self.section_splitter = SectionSplitter()
        self.keyword_analyzer = KeywordAnalyzer()
        self.openai_handler = OpenAIHandler(model="gpt-4o-2024-11-20")  # Specify the model here
        self.code_validator = CodeValidator()
        self.code_refiner = CodeRefiner(self.openai_handler)
        self.gui = GUI()
        self.max_refine_attempts = max_refine_attempts  # Maximum number of refinement attempts

    def extract_structure(self, pdf_path: str) -> Dict[str, List[str]]:
        """
        Extract text from PDF, detect structure, and perform keyword analysis.
        """
        self.logger.info(f"Starting extraction process for PDF: {pdf_path}")
        raw_text = self.pdf_loader.load_pdf(pdf_path)
        if not raw_text:
            self.logger.error("No text extracted from PDF.")
            return {}
        
        preprocessed_text = self.preprocessor.preprocess_text(raw_text)
        if not preprocessed_text:
            self.logger.error("Preprocessing failed. Empty text.")
            return {}
        
        headings = self.heading_detector.detect_headings(preprocessed_text)
        if not headings:
            self.logger.warning("No headings detected. Proceeding with default sectioning.")
        
        sections = self.section_splitter.split_into_sections(preprocessed_text, headings)
        keyword_analysis = self.keyword_analyzer.keyword_analysis(sections)
        
        return keyword_analysis

    def extract_structure_and_generate_code(self, pdf_path: str):
        """
        Extract structure from PDF and generate QuantConnect code.
        """
        self.logger.info("Starting structure extraction and code generation.")
        extracted_data = self.extract_structure(pdf_path)
        if not extracted_data:
            self.logger.error("No data extracted for code generation.")
            return

        # Generate summary
        summary = self.openai_handler.generate_summary(extracted_data)
        if not summary:
            self.logger.error("Failed to generate summary.")
            summary = "Summary could not be generated."

        # Generate QuantConnect code with refinement attempts
        qc_code = self.openai_handler.generate_qc_code(summary)  # Pass summary here
        attempt = 0
        while qc_code and not self.code_validator.validate_code(qc_code) and attempt < self.max_refine_attempts:
            self.logger.info(f"Attempt {attempt + 1} to refine code.")
            qc_code = self.code_refiner.refine_code(qc_code)
            if qc_code:
                if self.code_validator.validate_code(qc_code):
                    self.logger.info("Refined code is valid.")
                    break
            attempt += 1

        if not qc_code or not self.code_validator.validate_code(qc_code):
            self.logger.error("Failed to generate valid QuantConnect code after multiple attempts.")
            qc_code = "QuantConnect code could not be generated successfully."

        # Display summary and code in the GUI
        self.gui.display_summary_and_code(summary, qc_code)

        if qc_code != "QuantConnect code could not be generated successfully.":
            self.logger.info("QuantConnect code generation and display completed successfully.")
        else:
            self.logger.error("Failed to generate and display QuantConnect code.")
