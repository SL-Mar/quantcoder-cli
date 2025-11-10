# quantcli/cli.py

import click
import os
import json
from .gui import launch_gui  
from .processor import ArticleProcessor
from .utils import setup_logging, load_api_key, download_pdf
from .search import search_crossref, save_to_html
import logging
import webbrowser

# Constants for state management
ARTICLES_FILE = "articles.json"
DOWNLOADS_DIR = "downloads"
GENERATED_CODE_DIR = "generated_code"

# Configure a logger for the CLI
logger = logging.getLogger(__name__)

@click.group()
@click.option('--verbose', is_flag=True, help='Enables verbose mode.')
@click.pass_context
def cli(ctx, verbose):
    """
    QuantCoder CLI Tool
    """
    setup_logging(verbose)
    load_api_key()
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose

@cli.command()
def hello():
    """A simple command to test the CLI."""
    logger.info("Executing hello command")
    click.echo("Hello from QuantCLI!")

@cli.command()
@click.argument('query')
@click.option('--num', default=5, help='Number of results to return')
def search(query, num):
    """
    Search for articles based on QUERY.
    
    Example:
        quantcli search "algorithmic trading" --num 3
    """
    logger.info(f"Searching for articles with query: {query}, number of results: {num}")
    articles = search_crossref(query, rows=num)
    if not articles:
        click.echo("No articles found or an error occurred during the search.")
        return
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=4)
    click.echo(f"Found {len(articles)} articles:")
    for idx, article in enumerate(articles, 1):
        published = f" ({article['published']})" if article.get('published') else ""
        click.echo(f"{idx}: {article['title']} by {article['authors']}{published}")
    
    # Save and display HTML option
    save_html = click.confirm("Would you like to save the results to an HTML file and view it?", default=True)
    if save_html:
        save_to_html(articles)
        click.echo("Results saved to output.html and opened in the default web browser.")

@cli.command()
def list():
    """
    List previously searched articles.
    """
    if not os.path.exists(ARTICLES_FILE):
        click.echo("No articles found. Please perform a search first.")
        return
    with open(ARTICLES_FILE, 'r') as f:
        articles = json.load(f)
    if not articles:
        click.echo("No articles found in the current search.")
        return
    click.echo("Articles:")
    for idx, article in enumerate(articles, 1):
        published = f" ({article['published']})" if article.get('published') else ""
        click.echo(f"{idx}: {article['title']} by {article['authors']}{published}")

@cli.command()
@click.argument('article_id', type=int)
def download(article_id):
    """
    Download an article's PDF by ARTICLE_ID.

    Example:
        quantcli download 1
    """
    if not os.path.exists(ARTICLES_FILE):
        click.echo("No articles found. Please perform a search first.")
        return
    with open(ARTICLES_FILE, 'r') as f:
        articles = json.load(f)
    if article_id > len(articles) or article_id < 1:
        click.echo(f"Article with ID {article_id} not found.")
        return
    
    article = articles[article_id - 1]
    # Define the save path
    filename = f"article_{article_id}.pdf"
    save_path = os.path.join(DOWNLOADS_DIR, filename)
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # Attempt to download the PDF
    doi = article.get("DOI")
    success = download_pdf(article["URL"], save_path, doi=doi)
    if success:
        click.echo(f"Article downloaded to {save_path}")
    else:
        click.echo("Failed to download the PDF. You can open the article's webpage instead.")
        open_manual = click.confirm("Would you like to open the article URL in your browser for manual download?", default=True)
        if open_manual:
            webbrowser.open(article["URL"])
            click.echo("Opened the article URL in your default web browser.")

@cli.command()
@click.argument('article_id', type=int)
def summarize(article_id):
    """
    Summarize a downloaded article by ARTICLE_ID.

    Example:
        quantcli summarize 1
    """
    filepath = os.path.join(DOWNLOADS_DIR, f"article_{article_id}.pdf")
    if not os.path.exists(filepath):
        click.echo("Article not downloaded. Please download it first.")
        return

    processor = ArticleProcessor()
    extracted_data = processor.extract_structure(filepath)
    if not extracted_data:
        click.echo("Failed to extract data from the article.")
        return

    summary = processor.openai_handler.generate_summary(extracted_data)
    if summary:
        # Save summary to a file
        summary_path = os.path.join(DOWNLOADS_DIR, f"article_{article_id}_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        click.echo(f"Summary saved to {summary_path}")
        click.echo("Summary:")
        click.echo(summary)
    else:
        click.echo("Failed to generate summary.")

@cli.command(name='generate-code')
@click.argument('article_id', type=int)
def generate_code_cmd(article_id):
    """
    Generate QuantConnect code from a summarized article.

    Example:
        quantcli generate-code 1
    """
    filepath = os.path.join(DOWNLOADS_DIR, f"article_{article_id}.pdf")
    if not os.path.exists(filepath):
        click.echo("Article not downloaded. Please download it first.")
        return

    processor = ArticleProcessor()
    results = processor.extract_structure_and_generate_code(filepath)

    summary = results.get("summary")
    code = results.get("code")

    if summary:
        click.echo("Summary:")
        click.echo(summary)

    if code:
        code_path = os.path.join(GENERATED_CODE_DIR, f"algorithm_{article_id}.py")
        os.makedirs(GENERATED_CODE_DIR, exist_ok=True)
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        click.echo(f"Code generated at {code_path}")
    else:
        click.echo("Failed to generate QuantConnect code.")

@cli.command(name='open-article')
@click.argument('article_id', type=int)
def open_article(article_id):
    """
    Open the article's URL in the default web browser.

    Example:
        quantcli open-article 1
    """
    if not os.path.exists(ARTICLES_FILE):
        click.echo("No articles found. Please perform a search first.")
        return
    with open(ARTICLES_FILE, 'r') as f:
        articles = json.load(f)
    if article_id > len(articles) or article_id < 1:
        click.echo(f"Article with ID {article_id} not found.")
        return
    
    article = articles[article_id - 1]
    webbrowser.open(article["URL"])
    click.echo(f"Opened article URL: {article['URL']}")

@cli.command()
def interactive():
    """
    Perform an interactive search and process with a GUI.
    """
    click.echo("Starting interactive mode...")
    launch_gui()  # Call the launch_gui function to run the GUI

if __name__ == '__main__':
    cli()
