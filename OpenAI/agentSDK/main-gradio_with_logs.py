import os
import sys
import pdb
import json
import csv
import logging
import asyncio
import argparse
import traceback
import functools
from typing import Optional

from openai import OpenAI
from rich import print as rprint
from dotenv import find_dotenv, load_dotenv
from agents import Agent, Runner, function_tool, WebSearchTool, set_default_openai_key
import gradio as gr


# ===== CSV & NDJSON tracing =====
TRACE_CSV = "./run_trace.csv"
rprint(f"[yellow]TRACE_CSV: {TRACE_CSV}[/yellow]")
TRACE_NDJSON = "./run_trace.ndjson"
rprint(f"[yellow]TRACE_NDJSON: {TRACE_NDJSON}[/yellow]")
MAX_TRACE_CHARS = int(os.environ.get("MAX_TRACE_CHARS", "20000"))  # cap very large payloads
rprint(f"[yellow]MAX_TRACE_CHARS: {MAX_TRACE_CHARS}[/yellow]")
CSV_FIELDS = [
    "timestamp",
    "event_type",          # first_question | followup_question | tool_called | tool_output | agent_message
    "tool_name",           # optional
    "input",               # optional (JSON string)
    "output",              # optional (JSON string)
    "question",            # for user prompts
]


def _ensure_file(path: str, header: Optional[list[str]] = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if header:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=header).writeheader()
    else:
        if not os.path.exists(path):
            open(path, "w", encoding="utf-8").close()


def _ensure_csv(path: str):
    _ensure_file(path, CSV_FIELDS)


def _truncate(s: str) -> str:
    if s is None:
        return ""
    if len(s) <= MAX_TRACE_CHARS:
        return s
    return s[:MAX_TRACE_CHARS] + f"... [TRUNCATED to {MAX_TRACE_CHARS} chars]"


def _to_jsonable(obj):
    """Aggressive serializer: dataclasses, pydantic, attrs, arbitrary objects -> dict/str."""
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
    except Exception:
        pass
    # pydantic v1/v2
    for meth in ("model_dump", "dict", "to_dict", "_asdict"):
        if hasattr(obj, meth):
            try:
                return getattr(obj, meth)()
            except Exception:
                pass
    # __dict__ fallback
    if hasattr(obj, "__dict__"):
        try:
            return {k: _to_jsonable(v) for k, v in vars(obj).items()}
        except Exception:
            pass
    # iterables
    if isinstance(obj, (list, tuple, set)):
        try:
            return [ _to_jsonable(x) for x in obj ]
        except Exception:
            return list(obj)
    # bytes -> length + preview
    if isinstance(obj, (bytes, bytearray)):
        try:
            return {"__bytes__": True, "len": len(obj)}
        except Exception:
            return "<bytes>"
    return obj


def _json_dump_safe(obj) -> str:
    try:
        return json.dumps(_to_jsonable(obj), ensure_ascii=False, default=str)
    except Exception:
        try:
            return json.dumps(str(obj), ensure_ascii=False)
        except Exception:
            return "<unserializable>"


def append_trace(event_type: str, *, tool_name: Optional[str] = None,
                 input=None, output=None, question: Optional[str] = None,
                 raw: Optional[dict] = None):
    from datetime import datetime
    _ensure_csv(TRACE_CSV)
    _ensure_file(TRACE_NDJSON)
    ts = datetime.utcnow().isoformat() + "Z"

    # CSV (concise, truncated)
    row = {
        "timestamp": ts,
        "event_type": event_type,
        "tool_name": tool_name or "",
        "input": _truncate(_json_dump_safe(input)) if input is not None else "",
        "output": _truncate(_json_dump_safe(output)) if output is not None else "",
        "question": question or "",
    }
    with open(TRACE_CSV, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)

    # NDJSON (verbose, includes raw payload)
    nd = {
        "timestamp": ts,
        "event_type": event_type,
        "tool_name": tool_name,
        "input": input,
        "output": output,
        "question": question,
        "raw": raw,
    }
    try:
        with open(TRACE_NDJSON, "a", encoding="utf-8") as f:
            f.write(_json_dump_safe(nd) + "\n")
    except Exception:
        # never fail the run because tracing failed
        pass


# ===== Debug decorator =====

def debug_on_error(func):
    """Decorator to run pdb.post_mortem when an exception occurs."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            rprint(f"[red]Exception occurred in {func.__name__}:[/red]")
            rprint(f"[red]Error: {e}[/red]")
            rprint(f"[red]Traceback: {traceback.format_exc()}[/red]")
            pdb.post_mortem()
            raise
    return wrapper


# ===== OpenAI client init =====

def make_client():
    rprint("[yellow]Creating a OpenAI Client[/yellow]")
    load_dotenv(find_dotenv())
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    set_default_openai_key(OPENAI_API_KEY)


# -------- Logging: show verbose info in terminal --------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("demo")


# -------- Calculator tool (demo) --------
@function_tool(name_override="calculator", description_override="Evaluate a math expression (demo).")
def calculator(expression: str) -> str:
    try:
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


# -------- Chat handler with streaming + dual outputs + tool I/O visibility + CSV traces --------
async def chat_fn(message, history):
    # Buffers we will stream into the UI
    partial_answer = ""
    log_lines = []

    # Record first question vs follow-up
    try:
        if history:
            append_trace("followup_question", question=message)
        else:
            append_trace("first_question", question=message)
    except Exception:
        pass

    async def push():
        yield partial_answer, "\n".join(log_lines[-500:])

    # Start streaming the agent run
    stream = Runner.run_streamed(agent, message)

    # Iterate async events
    async for event in stream.stream_events():
        cname = event.__class__.__name__

        # 1) Raw LLM token deltas
        if cname == "RawResponsesStreamEvent":
            delta = getattr(event.data, "delta", None) or getattr(event.data, "output_text", None)
            if isinstance(delta, str) and delta:
                partial_answer += delta
                async for _ in push():
                    pass

        # 2) Higher-level run items: tool calls/outputs, message creation, etc.
        elif cname == "RunItemStreamEvent":
            name = getattr(event, "name", "unknown_event")
            item = getattr(event, "item", None)
            line = f"[{name}]"

            try:
                # Helper: extract tool name and arguments from *many* possible SDK shapes
                def extract_tool_call(tc):
                    tool_name = None
                    args = None
                    raw = _to_jsonable(tc)
                    # Try common attributes first
                    for n in ("name", "tool_name", "function_name"):
                        if hasattr(tc, n):
                            tool_name = getattr(tc, n)
                            if tool_name:
                                break
                        if isinstance(tc, dict) and n in tc:
                            tool_name = tc[n]
                            break
                    # Arguments / params under a variety of keys
                    for key in ("arguments", "args", "input", "params", "parameters", "kwargs", "payload"):
                        if hasattr(tc, key):
                            args = getattr(tc, key)
                            break
                        if isinstance(tc, dict) and key in tc:
                            args = tc[key]
                            break
                    return tool_name or "unknown_tool", args, raw

                def extract_tool_output(to):
                    tool_name = None
                    out = None
                    raw = _to_jsonable(to)
                    for n in ("name", "tool_name", "function_name"):
                        if hasattr(to, n):
                            tool_name = getattr(to, n)
                            if tool_name:
                                break
                        if isinstance(to, dict) and n in to:
                            tool_name = to[n]
                            break
                    for key in ("output", "result", "data", "content", "text", "message", "messages"):
                        if hasattr(to, key):
                            out = getattr(to, key)
                            break
                        if isinstance(to, dict) and key in to:
                            out = to[key]
                            break
                    return tool_name or "unknown_tool", out, raw

                if name == "tool_called":
                    tc = getattr(item, "tool_call", None) or getattr(item, "tool", None) or getattr(item, "data", None) or item
                    tool_name, args, raw = extract_tool_call(tc)
                    line += f" tool={tool_name} input={_truncate(_json_dump_safe(args))}"
                    append_trace("tool_called", tool_name=tool_name, input=args, raw={"tool_call": raw})

                elif name == "tool_output":
                    tobj = getattr(item, "tool_output", None) or getattr(item, "data", None) or item
                    tool_name, out, raw = extract_tool_output(tobj)
                    line += f" tool={tool_name} (output received) output={_truncate(_json_dump_safe(out))}"
                    append_trace("tool_output", tool_name=tool_name, output=out, raw={"tool_output": raw})

                elif name == "message_output_created":
                    text_obj = getattr(item, "message_output", None)
                    if text_obj and getattr(text_obj, "text", None):
                        partial_answer += text_obj.text

            except Exception as e:
                line += f" (detail error: {e})"

            log_lines.append(line)
            log.info(line)
            async for _ in push():
                pass

        elif cname == "AgentUpdatedStreamEvent":
            line = f"[agent_updated] new_agent={getattr(event, 'new_agent', None)}"
            log_lines.append(line)
            log.info(line)
            async for _ in push():
                pass

        await asyncio.sleep(0)

    # Finalize: capture final result for CSV & NDJSON
    try:
        result = await stream.get_final_result()
        final_text = getattr(result, "final_output", None)
        if final_text:
            append_trace("agent_message", output=final_text, raw=_to_jsonable(result))
    except Exception:
        pass

    return partial_answer, "\n".join(log_lines[-500:])


# -------- Gradio UI --------
with gr.Blocks() as demo:
    gr.Markdown("## Agents SDK × Gradio — Chat + Live Run Log + Tool I/O + CSV Trace")

    with gr.Row():
        with gr.Column(scale=2, min_width=480):
            log_box = gr.Textbox(
                label="Run log (live)",
                lines=18,
                value="",
                interactive=False,
                render=False,
            )

            chat = gr.ChatInterface(
                fn=chat_fn,
                type="messages",
                additional_outputs=[log_box],
                title="Ask me anything",
                description=(
                    "I’ll call calculator for math and web_search for fresh facts (with sources).\n"
                    "Tool calls show their inputs and outputs live."
                ),
            )

        with gr.Column(scale=1, min_width=360):
            gr.Markdown("### Execution Log")
            log_box.render()


@debug_on_error
def main(argv: Optional[list[str]] = None) -> None:
    rprint("[yellow]Using Agent SDK[/yellow]")
    make_client()
    demo.launch()


if __name__ == "__main__":
    main()
