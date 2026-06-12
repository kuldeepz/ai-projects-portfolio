"""
Smart Research Agent
Uses OpenAI function calling to orchestrate a multi-step research pipeline:
web search (via DuckDuckGo) → page fetch → summarize → compile report.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client
console = Console()

CHAT_MODEL = "gpt-4o-mini"
MAX_PAGE_CHARS = 4000
MAX_SEARCH_RESULTS = 5


# ─── Tool implementations ────────────────────────────────────────────────────

def web_search(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    """Search DuckDuckGo and return title + URL snippets."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return [{"error": str(e)}]

    soup = BeautifulSoup(html, "html.parser")
    results = []
    for result in soup.select(".result")[:max_results]:
        title_tag = result.select_one(".result__title a")
        snippet_tag = result.select_one(".result__snippet")
        if title_tag:
            href = title_tag.get("href", "")
            # DuckDuckGo uses redirect URLs — extract real URL
            if "uddg=" in href:
                real_url = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            else:
                real_url = href
            results.append({
                "title": title_tag.get_text(strip=True),
                "url": real_url,
                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else ""
            })
    return results


def fetch_page(url: str) -> str:
    """Fetch a web page and return its cleaned text content."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Error fetching page: {e}"

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_PAGE_CHARS]


def summarize_text(text: str, focus: str) -> str:
    """Summarize a piece of text focused on a specific topic."""
    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a research assistant. Summarize the provided text, focusing only on information relevant to the given topic. Be concise and factual."},
            {"role": "user", "content": f"Topic: {focus}\n\nText to summarize:\n{text}"}
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return response.choices[0].message.content


# ─── Tool definitions for the agent ─────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information on a topic. Returns a list of titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "max_results": {"type": "integer", "description": "Max number of results (default 5)", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch and read the text content of a web page by URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL of the page to fetch"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "Summarize a long piece of text, focused on a specific topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to summarize"},
                    "focus": {"type": "string", "description": "The topic/aspect to focus the summary on"}
                },
                "required": ["text", "focus"]
            }
        }
    }
]

TOOL_MAP = {
    "web_search": web_search,
    "fetch_page": fetch_page,
    "summarize_text": summarize_text,
}


# ─── Agent loop ──────────────────────────────────────────────────────────────

def run_agent(topic: str, depth: str = "standard") -> str:
    """Run the research agent and return a compiled markdown report."""

    depth_instructions = {
        "quick": "Do 1 search and write a brief 200-word summary.",
        "standard": "Do 2-3 searches, read the most relevant page, and write a structured 500-word report.",
        "deep": "Do 3-4 searches, read 2-3 pages, and write a comprehensive 800-word report with sections."
    }

    system_prompt = (
        "You are an expert research agent. Your job is to research a topic thoroughly using your available tools, "
        "then compile a well-structured markdown report.\n\n"
        f"Research depth: {depth_instructions.get(depth, depth_instructions['standard'])}\n\n"
        "Always end your work by writing the final report directly as your last message. "
        "The report should have a title, introduction, key findings, and conclusion."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Research this topic and write a report: {topic}"}
    ]

    console.print(f"\n[cyan]Agent starting research on:[/cyan] [bold]{topic}[/bold]\n")

    max_iterations = 10
    for iteration in range(max_iterations):
        response = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                console.print(f"  [dim]→ Tool:[/dim] [yellow]{fn_name}[/yellow] [dim]{list(fn_args.values())[0] if fn_args else ''}[/dim]")

                result = TOOL_MAP[fn_name](**fn_args)
                result_str = json.dumps(result) if isinstance(result, (list, dict)) else str(result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str
                })
        else:
            # Agent finished — return the final report
            return msg.content

    return "Research agent reached iteration limit. Partial results may be incomplete."


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python agent.py \"<research topic>\" [quick|standard|deep]")
        console.print('[dim]Example: python agent.py "Quantum computing breakthroughs 2024" deep[/dim]')
        sys.exit(1)

    topic = sys.argv[1]
    depth = sys.argv[2] if len(sys.argv) > 2 else "standard"

    if depth not in ("quick", "standard", "deep"):
        console.print("[red]Depth must be: quick, standard, or deep[/red]")
        sys.exit(1)

    with console.status("[bold green]Agent working...[/bold green]", spinner="dots"):
        report = run_agent(topic, depth)

    console.print()
    console.print(Panel(
        Markdown(report),
        title=f"[bold cyan]Research Report: {topic}[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))

    # Save report to file
    safe_name = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")[:50]
    output_file = f"report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, "w") as f:
        f.write(f"# Research Report: {topic}\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(report)

    console.print(f"\n[green]Report saved to:[/green] {output_file}\n")


if __name__ == "__main__":
    main()
