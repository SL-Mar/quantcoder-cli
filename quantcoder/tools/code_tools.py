"""Tools for code generation and validation."""

import ast
from pathlib import Path
from .base import Tool, ToolResult


class GenerateCodeTool(Tool):
    """Tool for generating QuantConnect code from article summaries."""

    @property
    def name(self) -> str:
        return "generate_code"

    @property
    def description(self) -> str:
        return "Generate QuantConnect trading algorithm code from article summary"

    def execute(self, article_id: int, max_refine_attempts: int = 6) -> ToolResult:
        """
        Generate QuantConnect code from an article.

        Args:
            article_id: Article ID from search results (1-indexed)
            max_refine_attempts: Maximum attempts to refine code

        Returns:
            ToolResult with generated code
        """
        from ..core.processor import ArticleProcessor

        self.logger.info(f"Generating code for article {article_id}")

        try:
            # Find the article file
            filepath = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

            if not filepath.exists():
                return ToolResult(
                    success=False,
                    error=f"Article not downloaded. Please download article {article_id} first."
                )

            # Process the article
            processor = ArticleProcessor(self.config, max_refine_attempts=max_refine_attempts)
            results = processor.extract_structure_and_generate_code(str(filepath))

            summary = results.get("summary")
            code = results.get("code")

            if not code or code == "QuantConnect code could not be generated successfully.":
                return ToolResult(
                    success=False,
                    error="Failed to generate valid QuantConnect code",
                    data={"summary": summary}
                )

            # Save code
            code_dir = Path(self.config.tools.generated_code_dir)
            code_dir.mkdir(parents=True, exist_ok=True)

            code_path = code_dir / f"algorithm_{article_id}.py"
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)

            return ToolResult(
                success=True,
                data={
                    "code": code,
                    "summary": summary,
                    "path": str(code_path)
                },
                message=f"Code generated and saved to {code_path}"
            )

        except Exception as e:
            self.logger.error(f"Error generating code: {e}")
            return ToolResult(success=False, error=str(e))


class ValidateCodeTool(Tool):
    """Tool for validating Python code syntax."""

    @property
    def name(self) -> str:
        return "validate_code"

    @property
    def description(self) -> str:
        return "Validate Python code for syntax errors"

    def execute(self, code: str) -> ToolResult:
        """
        Validate Python code.

        Args:
            code: Python code to validate

        Returns:
            ToolResult with validation status
        """
        self.logger.info("Validating code")

        try:
            ast.parse(code)
            return ToolResult(
                success=True,
                message="Code is syntactically correct"
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Syntax error: {e.msg} at line {e.lineno}",
                data={"line": e.lineno, "offset": e.offset}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}"
            )
