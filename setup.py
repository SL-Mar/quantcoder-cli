from setuptools import setup, find_packages
from pathlib import Path

readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="quantcli",
    version="0.4.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "Click>=8.0",
        "requests",
        "pdfplumber",
        "spacy>=3.0",
        "openai",
        "python-dotenv",
        "pygments",
        "InquirerPy",
    ],
    entry_points={
        "console_scripts": [
            "quantcli=quantcli.cli:cli",
        ],
    },
    author="SL-MAR",
    author_email="smr.laignel@gmail.com",
    description="A CLI tool for generating and evolving QuantConnect algorithms from research articles using AlphaEvolve-inspired optimization.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SL_Mar/QuantCoder",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
