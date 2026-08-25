import sys
import argparse
from pathlib import Path
from typing import List

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

from ingestion import PDFParser, TextChunker
from vectorstore import VectorStoreManager
from rag import RAGEngine
import config

def print_header():
    title = "AMPM Service POS Troubleshooting Assistant (Phase 1 CLI)"
    if HAS_RICH:
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))
    else:
        print("=" * 60)
        print(title)
        print("=" * 60)

def cmd_ingest(args):
    target_dir = Path(args.dir)
    if not target_dir.exists():
        print(f"Error: Directory '{args.dir}' does not exist.")
        sys.exit(1)

    doc_files = (
        list(target_dir.glob("*.pdf")) + list(target_dir.glob("*.PDF")) +
        list(target_dir.glob("*.chm")) + list(target_dir.glob("*.CHM"))
    )
    if not doc_files:
        print(f"No PDF or CHM files found in '{args.dir}'.")
        return

    print(f"Found {len(doc_files)} document file(s) in '{args.dir}'. Parsing...")
    chunker = TextChunker()
    vector_store = VectorStoreManager()

    from ingestion import parse_document

    total_chunks = 0
    for doc_path in doc_files:
        print(f"  -> Ingesting {doc_path.name}...")
        try:
            pages = parse_document(str(doc_path))
            chunks = chunker.chunk_pages(pages)
            added = vector_store.add_chunks(chunks)
            total_chunks += added
            print(f"     Parsed {len(pages)} topic(s)/page(s), created {added} chunk(s).")
        except Exception as e:
            print(f"     [Error] Failed to ingest {doc_path.name}: {e}")

    print(f"\n[Success] Ingested {len(doc_files)} file(s), total {total_chunks} chunk(s) stored in vector store.")
    print(f"Current collection total chunks: {vector_store.count()}")

def cmd_query(args):
    vector_store = VectorStoreManager()
    if vector_store.count() == 0:
        print("[Warning] Vector store is empty! Please run ingestion first: python cli.py ingest --dir ./sample_docs")

    engine = RAGEngine(vector_store=vector_store)
    query_text = args.question

    if not query_text:
        print("Error: Please provide a question string or use --interactive mode.")
        sys.exit(1)

    provider = args.provider or config.DEFAULT_LLM_PROVIDER
    print(f"\nQuerying RAG Engine using provider: [ {provider.upper()} ]...")
    result = engine.query(question=query_text, provider_name=provider, top_k=args.top_k, category=args.category)

    if HAS_RICH:
        console.print("\n[bold green]Answer:[/bold green]")
        console.print(Markdown(result["answer"]))

        if result["citations"]:
            table = Table(title="Sources & Citations")
            table.add_column("Document", style="cyan")
            table.add_column("Page", style="magenta")
            table.add_column("Category", style="yellow")
            for c in result["citations"]:
                table.add_row(c["file_name"], str(c["page_number"]), c["category"])
            console.print("\n", table)
    else:
        print("\n--- Answer ---")
        print(result["answer"])
        print("\n--- Sources & Citations ---")
        for c in result["citations"]:
            print(f"- File: {c['file_name']} | Page: {c['page_number']} | Category: {c['category']}")

def cmd_interactive(args):
    print_header()
    vector_store = VectorStoreManager()
    engine = RAGEngine(vector_store=vector_store)
    provider = args.provider or config.DEFAULT_LLM_PROVIDER

    print(f"Active Provider: {provider.upper()}")
    print(f"Docs in Vector Store: {vector_store.count()}")
    print("Type your symptom or question (or 'exit' / 'quit' to exit):\n")

    while True:
        try:
            user_input = input("Tech Question > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting troubleshooting assistant. Goodbye!")
                break

            result = engine.query(question=user_input, provider_name=provider, top_k=args.top_k, category=args.category)
            
            if HAS_RICH:
                console.print("\n[bold green]Answer:[/bold green]")
                console.print(Markdown(result["answer"]))
                console.print("-" * 50)
            else:
                print("\n--- Answer ---")
                print(result["answer"])
                print("-" * 50)

        except KeyboardInterrupt:
            print("\nExiting.")
            break

def main():
    parser = argparse.ArgumentParser(description="AMPM Service POS Troubleshooting Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Ingest subcommand
    ingest_parser = subparsers.add_parser("ingest", help="Ingest PDFs from directory into vector DB")
    ingest_parser.add_argument("--dir", "-d", default="./sample_docs", help="Directory containing PDF documentation")

    # Query subcommand
    query_parser = subparsers.add_parser("query", help="Query the RAG troubleshooting assistant")
    query_parser.add_argument("question", nargs="?", default="", help="Symptom description or question")
    query_parser.add_argument("--provider", "-p", choices=["gemini", "groq", "ollama"], help="LLM Provider choice")
    query_parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of retrieved context chunks")
    query_parser.add_argument("--category", "-c", help="Filter by document category")

    # Interactive subcommand
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive CLI chat session")
    interactive_parser.add_argument("--provider", "-p", choices=["gemini", "groq", "ollama"], help="LLM Provider choice")
    interactive_parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of retrieved context chunks")
    interactive_parser.add_argument("--category", "-c", help="Filter by document category")

    args = parser.parse_args()

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "interactive":
        cmd_interactive(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
