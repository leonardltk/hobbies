#!/usr/bin/env python3
"""
Python replication of `google-gemini/veo-3-nano-banana-gemini-api-quickstart`.

Features:
- Generate images with Imagen 4 or Gemini's native image model (Gemini 2.5 Flash Image preview).
- Edit/compose images by providing one or more input images + a text instruction (Gemini native).
- Generate Veo 3 videos (text-to-video or image-to-video), poll the long-running operation, and download.

Requires:
  pip install google-genai Pillow
Environment:
  export GOOGLE_API_KEY=...   # or GEMINI_API_KEY=...
"""

import os
import pdb
import time
import argparse
import traceback
import functools
from io import BytesIO

from rich import print as rich_print
from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types
from PIL import Image


# ----- Models (from official docs) -----
IMAGEN4 = "imagen-4.0-generate-001"                     # Imagen 4 (image generation)
GEMINI_NATIVE_IMAGE = "gemini-2.5-flash-image-preview"  # Gemini's native image generation/edit/compose (aka Nano Banana)
VEO3 = "veo-3.0-generate-001"                           # Veo 3 (video with audio)
VEO3_FAST = "veo-3.0-fast-generate-001"                 # Optional faster Veo 3 variant

def debug_on_error(func):
    """Decorator to run pdb.post_mortem when an exception occurs."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Catch any exception and launch pdb in post-mortem mode
            rich_print(f"[red]Exception occurred in {func.__name__}:[/red]")
            rich_print(f"[red]Error: {e}[/red]")
            rich_print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            pdb.post_mortem()
            raise  # Re-raise the exception after post-mortem inspection
    return wrapper


def make_client():
    """
    Create a genai.Client. The SDK will auto-pick GOOGLE_API_KEY (or GEMINI_API_KEY).
    If you prefer, pass api_key=... explicitly.
    """
    rich_print("[yellow]Creating a genai.Client[/yellow]")
    load_dotenv(find_dotenv())
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    return genai.Client(api_key=GEMINI_API_KEY)


# ---------------- Image helpers ----------------

def save_pil_bytes(image_bytes: bytes, out_path: str):
    img = Image.open(BytesIO(image_bytes))
    img.save(out_path)
    return out_path


def cmd_img_generate(args):
    """
    Generate image(s) with either:
      - Imagen 4 (high-fidelity image generator)
      - Gemini 2.5 Flash Image preview (Gemini-native image generation)
    """
    client = make_client()

    rich_print("""[yellow]Generating image(s) with either:
      - Imagen 4 (high-fidelity image generator)
      - Gemini 2.5 Flash Image preview (Gemini-native image generation)[/yellow]
    """)
    rich_print(f"[yellow]Prompt: {args.prompt}[/yellow]")
    rich_print(f"[yellow]Number of images: {args.n}[/yellow]")
    rich_print(f"[yellow]Aspect ratio: {args.aspect}[/yellow]")
    rich_print(f"[yellow]Size: {args.size}[/yellow]")
    rich_print(f"[yellow]Output prefix: {args.out_prefix}[/yellow]")

    if args.engine == "imagen4":
        # Imagen supports config such as number_of_images, aspect_ratio, sample_image_size (1K/2K).
        cfg = {}
        if args.n:
            cfg["number_of_images"] = args.n
        if args.aspect:
            cfg["aspect_ratio"] = args.aspect
        # this is not supported yet
        # if args.size:
        #     cfg["sample_image_size"] = args.size  # '1K' or '2K' (Std/Ultra/Fast) per docs

        resp = client.models.generate_images(
            model=IMAGEN4,
            prompt=args.prompt,
            config=types.GenerateImagesConfig(**cfg) if cfg else None,
        )
        for i, gi in enumerate(resp.generated_images, start=1):
            # gi.image holds the image payload; write as PNG by default.
            out = f"{args.out_prefix or 'imagen4'}-{i}.png"
            # The SDK exposes raw bytes on gi.image.image_bytes; use PIL for safety.
            save_pil_bytes(gi.image.image_bytes, out)
            print(f"Saved {out}")

    else:
        # Gemini-native image generation returns images interleaved as inline_data parts.
        resp = client.models.generate_content(
            model=GEMINI_NATIVE_IMAGE,
            contents=[args.prompt],
        )
        idx = 1
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                out = f"{args.out_prefix or 'gemini-image'}-{idx}.png"
                save_pil_bytes(part.inline_data.data, out)
                print(f"Saved {out}")
                idx += 1
            # If the model returns any text parts, you could print them for tips/debug:
            elif getattr(part, "text", None):
                print(part.text)

def cmd_img_edit(args):
    """
    Edit/compose images with Gemini-native image model.
    Provide 1+ --input images along with an instruction prompt.
    """
    client = make_client()

    rich_print("""[yellow]Editing/composing images with Gemini-native image model.
      Provide 1+ --input images along with an instruction prompt.[/yellow]
    """)
    rich_print(f"[yellow]Prompt: {args.prompt}[/yellow]")
    rich_print(f"[yellow]Input images: {args.input}[/yellow]")
    rich_print(f"[yellow]Output prefix: {args.out_prefix}[/yellow]")

    # Load all input images; the SDK accepts PIL Images directly or bytes via types.Part.
    pil_images = [Image.open(p) for p in args.input]

    resp = client.models.generate_content(
        model=GEMINI_NATIVE_IMAGE,
        contents=[args.prompt, *pil_images],
    )
    idx = 1
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            rich_print(f"[yellow]Saving image {idx}[/yellow]")
            out = f"{args.out_prefix or 'gemini-edit'}-{idx}.png"
            save_pil_bytes(part.inline_data.data, out)
            print(f"Saved {out}")
            idx += 1
        elif getattr(part, "text", None):
            print(part.text)

# ---------------- Video helpers (Veo 3) ----------------

def poll_operation(client, operation, interval: int = 10):
    """
    Poll a long-running operation until it is done; returns the final operation.
    """
    while not operation.done:
        print("Waiting for video generation to complete...")
        time.sleep(interval)
        operation = client.operations.get(operation)
    return operation


def cmd_video_generate(args):
    """
    Generate a Veo 3 video (with audio). Optionally provide an initial image (image-to-video).
    """
    client = make_client()

    rich_print("""[yellow]Generating a Veo 3 video (with audio).
      Optionally provide an initial image (image-to-video).[/yellow]
    """)
    rich_print(f"[yellow]Prompt: {args.prompt}[/yellow]")
    rich_print(f"[yellow]Aspect ratio: {args.aspect}[/yellow]")
    rich_print(f"[yellow]Resolution: {args.resolution}[/yellow]")
    rich_print(f"[yellow]Negative prompt: {args.negative_prompt}[/yellow]")

    # Build config for Veo
    video_cfg = {}
    if args.aspect:
        video_cfg["aspect_ratio"] = args.aspect  # "16:9" or "9:16" (1080p only for 16:9)
    if args.resolution:
        video_cfg["resolution"] = args.resolution  # "720p" | "1080p" (16:9 only)
    if args.negative_prompt:
        video_cfg["negative_prompt"] = args.negative_prompt
    if args.person_generation:
        video_cfg["person_generation"] = args.person_generation  # region-dependent
    if args.seed is not None:
        video_cfg["seed"] = args.seed

    model = VEO3_FAST if args.fast else VEO3

    # Optional image input
    image_arg = None
    if args.image:
        # Use SDK helper that infers mime type (recommended)
        image_arg = types.Image.from_file(location=args.image)

    operation = client.models.generate_videos(
        model=model,
        prompt=args.prompt,
        image=image_arg,
        config=types.GenerateVideosConfig(**video_cfg) if video_cfg else None,
    )

    print(f"Started operation: {operation.name}")

    if args.no_wait:
        return  # Just print the op name and exit.

    # Poll until done and download.
    operation = poll_operation(client, operation, interval=args.poll)
    vid = operation.response.generated_videos[0].video

    # Download then save to disk
    client.files.download(file=vid)
    out_path = args.out or "veo3_output.mp4"
    vid.save(out_path)
    print(f"Saved {out_path}")


# ---------------- CLI wiring ----------------

def build_parser():
    p = argparse.ArgumentParser(description="Gemini API (Imagen/Gemini-native/Veo 3) Python quickstart")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Image generate
    pi = sub.add_parser("img", help="Generate images")
    pi.add_argument("--engine", choices=["imagen4", "gemini"], default="imagen4",
                    help="imagen4 = Imagen 4; gemini = Gemini-native image model")
    pi.add_argument("--prompt", required=True, help="Text prompt")
    pi.add_argument("--n", type=int, default=1, help="Number of images (Imagen 4)")
    pi.add_argument("--aspect", choices=["1:1", "3:4", "4:3", "9:16", "16:9"], help="Aspect ratio (Imagen 4)")
    pi.add_argument("--size", choices=["1K", "2K"], help="Output size (Imagen 4 Std/Ultra/Fast)")
    pi.add_argument("--out-prefix", help="Filename prefix (default: imagen4/gemini-image)")
    pi.set_defaults(func=cmd_img_generate)

    # Image edit/compose (Gemini-native)
    pe = sub.add_parser("edit", help="Edit/compose images (Gemini-native model)")
    pe.add_argument("--prompt", required=True, help="Edit/compose instruction")
    pe.add_argument("--input", nargs="+", required=True, help="One or more input image paths")
    pe.add_argument("--out-prefix", help="Filename prefix (default: gemini-edit)")
    pe.set_defaults(func=cmd_img_edit)

    # Video generate (Veo 3)
    pv = sub.add_parser("video", help="Generate a Veo 3 video (with audio)")
    pv.add_argument("--prompt", required=True, help="Video prompt (supports audio cues/dialogue)")
    pv.add_argument("--image", help="Optional starting image (image-to-video)")
    pv.add_argument("--fast", action="store_true", help="Use Veo 3 Fast")
    pv.add_argument("--aspect", choices=["16:9", "9:16"], help="Aspect ratio")
    pv.add_argument("--resolution", choices=["720p", "1080p"], help="Resolution (1080p only for 16:9)")
    pv.add_argument("--negative-prompt", help="Negative prompt text")
    pv.add_argument("--person-generation", choices=["allow_all", "allow_adult", "dont_allow"],
                    help="Controls people generation (region restricted; see docs)")
    pv.add_argument("--seed", type=int, help="Seed (not fully deterministic)")
    pv.add_argument("--poll", type=int, default=10, help="Polling interval in seconds")
    pv.add_argument("--no-wait", action="store_true", help="Start and print op name; do not poll")
    pv.add_argument("--out", help="Output mp4 path (default: veo3_output.mp4)")
    pv.set_defaults(func=cmd_video_generate)

    return p

@debug_on_error
def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
