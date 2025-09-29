# gpt5_demo.py
import os
import sys
import pdb
import json
import logging
import asyncio
import requests
import argparse
import traceback
import functools
from typing import Optional

from openai import OpenAI
from rich import print as rprint
from dotenv import find_dotenv, load_dotenv
from agents import Agent, Runner, function_tool, WebSearchTool, set_default_openai_key
import gradio as gr


def debug_on_error(func):
    """Decorator to run pdb.post_mortem when an exception occurs."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Catch any exception and launch pdb in post-mortem mode
            rprint(f"[red]Exception occurred in {func.__name__}:[/red]")
            rprint(f"[red]Error: {e}[/red]")
            rprint(f"[red]Traceback: {traceback.format_exc()}[/red]")
            pdb.post_mortem()
            raise  # Re-raise the exception after post-mortem inspection
    return wrapper


def make_client():
    """
    Create a genai.Client. The SDK will auto-pick GOOGLE_API_KEY (or GEMINI_API_KEY).
    If you prefer, pass api_key=... explicitly.
    """
    rprint("[yellow]Creating a OpenAI Client[/yellow]")
    load_dotenv(find_dotenv())
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    set_default_openai_key(os.getenv("OPENAI_API_KEY"))

# -------- Logging: show verbose info in terminal --------
# Print INFO+ to stdout with timestamps and levels
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("demo")


# -------- Calculator tool (demo) --------
@function_tool(name_override="calculator", description_override="Evaluate a math expression (demo).")
def calculator(expression: str) -> str:
    try:
        # DEMO ONLY — replace with a safe parser for production (e.g., sympy/numexpr)
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"


# -------- Agent with two tools --------
agent = Agent(
    name="Gradio Assistant",
    instructions=(
        "You are a helpful assistant."
        
        "Use `web_search` for up-to-date facts; include 1–3 source links when you search. "
        
        "Use `calculator` for arithmetic. "
        "If you use the calculator, include your calculation in the response."

        "Keep answers concise."
    ),        
    tools=[WebSearchTool(), calculator],
)



# -------- Chat handler with streaming + dual outputs --------
# We'll stream events -> update a live log and the assistant text.
async def chat_fn(message, history):
    # Buffers we will stream into the UI
    partial_answer = ""
    log_lines = []

    # Helper to push a UI update (assistant text + log text)
    async def push():
        # ChatInterface (type="messages") accepts returning a string for the assistant,
        # plus any additional_outputs. We'll return (assistant, log).
        yield partial_answer, "\n".join(log_lines[-500:])  # keep log bounded

    # Start streaming the agent run
    stream = Runner.run_streamed(agent, message)

    # Iterate async events
    async for event in stream.stream_events():
        # Raw LLM deltas
        if event.__class__.__name__ == "RawResponsesStreamEvent":
            # Many models send delta tokens in event.data; guard for structure differences
            # Accumulate any textual delta
            delta = getattr(event.data, "delta", None) or getattr(event.data, "output_text", None)
            if isinstance(delta, str) and delta:
                partial_answer += delta
                # Show partial answer with unchanged log
                async for _ in push():
                    pass  # one-frame update

        # Higher-level run items: tool calls, tool outputs, agent messages, etc.
        elif event.__class__.__name__ == "RunItemStreamEvent":
            name = getattr(event, "name", "unknown_event")
            item = getattr(event, "item", None)
            # Build a readable log line
            line = f"[{name}]"
            # Add a little detail where possible
            try:
                if name == "tool_called":
                    tool = getattr(item, "tool_call", None)
                    if tool and getattr(tool, "name", None):
                        line += f" tool={tool.name}"
                elif name == "tool_output":
                    tool = getattr(item, "tool_output", None)
                    if tool and getattr(tool, "name", None):
                        line += f" tool={tool.name} (output received)"
                elif name == "message_output_created":
                    # An assistant message was finalized
                    text = getattr(item, "message_output", None)
                    if text and getattr(text, "text", None):
                        # Some providers deposit full chunks here; append if present
                        partial_answer += text.text
            except Exception as e:
                line += f" (detail error: {e})"

            # Append to log + print to terminal
            log_lines.append(line)
            log.info(line)

            # Push UI with current partial answer and updated log
            async for _ in push():
                pass

        # Agent switch events (rare in a simple demo)
        elif event.__class__.__name__ == "AgentUpdatedStreamEvent":
            line = f"[agent_updated] new_agent={getattr(event, 'new_agent', None)}"
            log_lines.append(line)
            log.info(line)
            async for _ in push():
                pass

        # Small pause prevents UI thrash if events are very chatty
        await asyncio.sleep(0)
    
    # Return what we've collected
    return partial_answer, "\n".join(log_lines[-500:])

    # Finalize the streamed result (collects sources, etc.)
    result = await stream.get_final_result()
    # Ensure final output is reflected
    final_text = result.final_output or partial_answer
    if final_text != partial_answer:
        partial_answer = final_text
        async for _ in push():
            pass

    return partial_answer, "\n".join(log_lines[-500:])


# -------- Gradio UI: two columns (chat left, live log right) --------
with gr.Blocks() as demo:
    gr.Markdown("## Agents SDK × Gradio — Chat + Live Run Log")

    with gr.Row():
        with gr.Column(scale=2, min_width=480):
            # Right here, we use ChatInterface BUT feed an extra output (the log)
            log_box = gr.Textbox(
                label="Run log (live)",
                lines=18,
                value="",
                interactive=False,
                render=False,  # we will render it on the right column
            )

            # ChatInterface will update both the assistant message and log_box
            chat = gr.ChatInterface(
                fn=chat_fn,
                type="messages",
                additional_outputs=[log_box],
                title="Ask me anything",
                description="I’ll call calculator for math and web_search for fresh facts (with sources).",
            )

        with gr.Column(scale=1, min_width=360):
            gr.Markdown("### Execution Log")
            log_box.render()

@debug_on_error
def main(argv: Optional[list[str]] = None) -> None:
    # answer gpt5
    rprint("[yellow]Using Agent SDK[/yellow]")
    make_client()

    demo.launch()


if __name__ == "__main__":
    main()

