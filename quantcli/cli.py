# quantcli/cli.py

import click
import os
import json
from .gui import launch_gui
from .processor import ArticleProcessor
from .utils import setup_logging, load_api_key, download_pdf
from .search import search_crossref, save_to_html
from .evolver import EvolutionEngine, EvolutionConfig, create_evolution_engine
import logging
import webbrowser

__version__ = "0.4.0"

# Constants for state management
ARTICLES_FILE = "articles.json"
DOWNLOADS_DIR = "downloads"
GENERATED_CODE_DIR = "generated_code"

# Configure a logger for the CLI
logger = logging.getLogger(__name__)

@click.group()
@click.option('--verbose', is_flag=True, help='Enables verbose mode.')
@click.option('--version', is_flag=True, help='Show version information.')
@click.pass_context
def cli(ctx, verbose, version):
    """
    QuantCoder CLI - Generate QuantConnect Trading Algorithms from Research Articles

    QuantCoder uses NLP and LLMs to transform academic research articles into
    executable trading algorithms for the QuantConnect platform.

    WORKFLOW:

        1. Search for articles:     quantcli search "momentum trading"
        2. List found articles:     quantcli list
        3. Download article PDF:    quantcli download 1
        4. Summarize article:       quantcli summarize 1
        5. Generate trading code:   quantcli generate-code 1
        6. Evolve strategy:         quantcli evolve 1

    EVOLUTION MODE (AlphaEvolve-inspired):

        quantcli evolve 1           Evolve algorithm using LLM variations
        quantcli evolve 1 --gens 5  Run for 5 generations
        quantcli evolve --resume <id>  Resume a previous evolution

    INTERACTIVE MODE:

        quantcli interactive        Launch GUI for guided workflow

    For help on a specific command:

        quantcli <command> --help

    Examples:

        quantcli search "algorithmic trading" --num 5
        quantcli download 1
        quantcli generate-code 1
        quantcli evolve 1 --gens 10 --variants 5
    """
    if version:
        click.echo(f"QuantCoder CLI v{__version__}")
        click.echo("Features: Article processing, Code generation, AlphaEvolve optimization")
        ctx.exit()
        
    setup_logging(verbose)
    load_api_key()
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose

@cli.command()
def hello():
    """Test command to verify CLI installation."""
    logger.info("Executing hello command")
    click.echo("Hello from QuantCLI!")

@cli.command()
@click.argument('query')
@click.option('--num', default=5, help='Number of results to return')
def search(query, num):
    """
    Search for academic articles using CrossRef API.
    
    QUERY: Search keywords (e.g., "momentum trading", "mean reversion")
    
    Examples:
    
        quantcli search "algorithmic trading" --num 3
        quantcli search "pairs trading strategies" --num 10
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
    List previously searched articles from the current session.
    
    Displays all articles from the most recent search operation.
    Articles are saved in articles.json.
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
    Download an article's PDF by its list position.

    ARTICLE_ID: The number shown in the 'list' command (1, 2, 3, etc.)

    Example:
    
        quantcli download 1    # Downloads the first article from your search
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
    Generate an AI summary of a downloaded article.

    ARTICLE_ID: The number of the article to summarize
    
    The article must be downloaded first using the 'download' command.
    Summary is saved to downloads/article_<ID>_summary.txt

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
    Generate a QuantConnect trading algorithm from an article.

    ARTICLE_ID: The number of the article to process
    
    Extracts trading strategy logic from the article and generates
    executable Python code for the QuantConnect platform.
    
    Output is saved to generated_code/algorithm_<ID>.py

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
    Open the article's webpage in your default browser.

    ARTICLE_ID: The number of the article to open

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
    Launch the interactive GUI for a guided workflow.

    The GUI provides a visual interface for:
    - Searching articles
    - Viewing search results
    - Downloading PDFs
    - Generating summaries and code

    Recommended for first-time users.
    """
    click.echo("Starting interactive mode...")
    launch_gui()  # Call the launch_gui function to run the GUI


# Evolution constants
EVOLUTIONS_DIR = "data/evolutions"


@cli.command()
@click.argument('article_id', type=int, required=False)
@click.option('--resume', 'resume_id', help='Resume a previous evolution by ID')
@click.option('--gens', 'max_generations', default=10, help='Maximum generations to run')
@click.option('--variants', 'variants_per_gen', default=5, help='Variants per generation')
@click.option('--elite', 'elite_size', default=3, help='Elite pool size')
@click.option('--patience', default=3, help='Stop after N generations without improvement')
@click.option('--qc-user', envvar='QC_USER_ID', help='QuantConnect user ID')
@click.option('--qc-token', envvar='QC_API_TOKEN', help='QuantConnect API token')
@click.option('--qc-project', envvar='QC_PROJECT_ID', type=int, help='QuantConnect project ID')
@click.pass_context
def evolve(ctx, article_id, resume_id, max_generations, variants_per_gen,
           elite_size, patience, qc_user, qc_token, qc_project):
    """
    Evolve a trading algorithm using AlphaEvolve-inspired optimization.

    This command takes a generated algorithm and evolves it through multiple
    generations of LLM-generated variations, evaluated via QuantConnect backtests.

    ARTICLE_ID: The article number to evolve (must have generated code first)

    Unlike traditional parameter optimization, this explores STRUCTURAL variations:
    - Indicator changes (SMA -> EMA, add RSI, etc.)
    - Risk management modifications
    - Entry/exit logic changes
    - Universe selection tweaks

    The elite pool ensures the best solutions are never lost, even if a
    generation produces worse results.

    REQUIREMENTS:

        Set QuantConnect credentials via environment variables or options:
        - QC_USER_ID or --qc-user
        - QC_API_TOKEN or --qc-token
        - QC_PROJECT_ID or --qc-project

    Examples:

        quantcli evolve 1                    # Evolve article 1's algorithm
        quantcli evolve 1 --gens 5           # Run for 5 generations
        quantcli evolve 1 --variants 3       # Generate 3 variants per generation
        quantcli evolve --resume abc123      # Resume evolution abc123
    """
    # Validate QuantConnect credentials
    if not all([qc_user, qc_token, qc_project]):
        click.echo("Error: QuantConnect credentials required.")
        click.echo("")
        click.echo("Set via environment variables:")
        click.echo("  export QC_USER_ID=your_user_id")
        click.echo("  export QC_API_TOKEN=your_api_token")
        click.echo("  export QC_PROJECT_ID=your_project_id")
        click.echo("")
        click.echo("Or use command options:")
        click.echo("  quantcli evolve 1 --qc-user ID --qc-token TOKEN --qc-project PROJECT")
        ctx.exit(1)

    # Handle resume mode
    if resume_id:
        click.echo(f"Resuming evolution: {resume_id}")
        baseline_code = None
        source_paper = None
    else:
        # Need article_id for new evolution
        if not article_id:
            click.echo("Error: ARTICLE_ID required for new evolution.")
            click.echo("Use --resume <id> to resume an existing evolution.")
            ctx.exit(1)

        # Load the generated code for this article
        code_path = os.path.join(GENERATED_CODE_DIR, f"algorithm_{article_id}.py")
        if not os.path.exists(code_path):
            click.echo(f"Error: No generated code found for article {article_id}.")
            click.echo(f"Run 'quantcli generate-code {article_id}' first.")
            ctx.exit(1)

        with open(code_path, 'r') as f:
            baseline_code = f.read()

        # Get article info for reference
        source_paper = f"article_{article_id}"
        if os.path.exists(ARTICLES_FILE):
            with open(ARTICLES_FILE, 'r') as f:
                articles = json.load(f)
            if 0 < article_id <= len(articles):
                source_paper = articles[article_id - 1].get('title', source_paper)

    # Create evolution engine
    click.echo("")
    click.echo("=" * 60)
    click.echo("AlphaEvolve Strategy Optimization")
    click.echo("=" * 60)
    click.echo(f"Max generations:    {max_generations}")
    click.echo(f"Variants/gen:       {variants_per_gen}")
    click.echo(f"Elite pool size:    {elite_size}")
    click.echo(f"Convergence patience: {patience}")
    click.echo("=" * 60)
    click.echo("")

    try:
        engine = create_evolution_engine(
            qc_user_id=qc_user,
            qc_api_token=qc_token,
            qc_project_id=qc_project,
            max_generations=max_generations,
            variants_per_generation=variants_per_gen,
            elite_pool_size=elite_size,
            convergence_patience=patience
        )

        # Set up progress callback
        def on_generation_complete(state, gen):
            best = state.elite_pool.get_best()
            if best and best.fitness:
                click.echo(f"\nGeneration {gen} complete. Best fitness: {best.fitness:.4f}")

        engine.on_generation_complete = on_generation_complete

        # Run evolution
        if resume_id:
            result = engine.evolve(baseline_code="", source_paper="", resume_id=resume_id)
        else:
            result = engine.evolve(baseline_code, source_paper)

        # Report results
        click.echo("")
        click.echo("=" * 60)
        click.echo("EVOLUTION COMPLETE")
        click.echo("=" * 60)
        click.echo(result.get_summary())

        # Export best variant
        best = engine.get_best_variant()
        if best:
            output_path = os.path.join(
                GENERATED_CODE_DIR,
                f"evolved_{result.evolution_id}.py"
            )
            os.makedirs(GENERATED_CODE_DIR, exist_ok=True)
            engine.export_best_code(output_path)
            click.echo(f"\nBest algorithm saved to: {output_path}")

        click.echo(f"\nEvolution ID: {result.evolution_id}")
        click.echo(f"To resume: quantcli evolve --resume {result.evolution_id}")

    except Exception as e:
        logger.error(f"Evolution failed: {e}")
        click.echo(f"Error: Evolution failed - {e}")
        ctx.exit(1)


@cli.command(name='list-evolutions')
def list_evolutions():
    """
    List all saved evolution runs.

    Shows evolution IDs, status, and best fitness for each saved evolution.
    Use the evolution ID to resume with: quantcli evolve --resume <id>
    """
    if not os.path.exists(EVOLUTIONS_DIR):
        click.echo("No evolutions found.")
        return

    evolution_files = [f for f in os.listdir(EVOLUTIONS_DIR) if f.endswith('.json')]

    if not evolution_files:
        click.echo("No evolutions found.")
        return

    click.echo("Saved evolutions:")
    click.echo("-" * 60)

    for filename in sorted(evolution_files):
        try:
            filepath = os.path.join(EVOLUTIONS_DIR, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)

            evo_id = data.get('evolution_id', 'unknown')
            status = data.get('status', 'unknown')
            generation = data.get('current_generation', 0)
            elite = data.get('elite_pool', {}).get('variants', [])
            best_fitness = elite[0].get('fitness', 'N/A') if elite else 'N/A'

            click.echo(f"  {evo_id}: Gen {generation}, Status: {status}, Best: {best_fitness}")
        except Exception as e:
            click.echo(f"  {filename}: Error reading - {e}")

    click.echo("-" * 60)
    click.echo("Resume with: quantcli evolve --resume <id>")


if __name__ == '__main__':
    cli()
