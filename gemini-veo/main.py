import os
import pdb
import time
import traceback

from rich import print as rich_print
from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types


def init_client():
    load_dotenv(find_dotenv())

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    return genai.Client(api_key=GEMINI_API_KEY)

def generate_text(client, prompt):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response

def generate_video(client, prompt, sleep_time, output_video_path, config=None, image=None):
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",  # or "veo-3.0-fast-generate-preview"
        prompt=prompt,
        config=config,
        image=image,
    )

    # Waiting for the video(s) to be generated
    while not operation.done:
        time.sleep(sleep_time)
        operation = client.operations.get(operation)
    """
        GenerateVideosOperation(
            done=True,
            name='models/veo-3.0-generate-preview/operations/kkjc5xue6qf2',
            response=GenerateVideosResponse(
                generated_videos=[
                    GeneratedVideo(
                        video=Video(
                            uri='https://generativelanguage.googleapis.com/v1beta/files/lugjtb9fvyhg:download?alt=media',
                            video_bytes=b'...'
                        )
                    ),
                ]
            ),
            result=GenerateVideosResponse(
                generated_videos=[
                    GeneratedVideo(
                        video=Video(
                            uri='https://generativelanguage.googleapis.com/v1beta/files/lugjtb9fvyhg:download?alt=media',
                            video_bytes=b'...'
                        )
                    ),
                ]
            )
        )
    """

    # Download the resulting MP4 with native audio
    generated_video = operation.result.generated_videos[0]
    client.files.download(file=generated_video.video)
    generated_video.video.save(output_video_path)
    print(f"Saved {output_video_path}")


    return operation, generated_video


def main():
    try:
        print("Hello from gemini-veo!")

        # gemini client
        rich_print("[yellow]Gemini client[/yellow]")
        client = init_client()

        # normal text generation
        rich_print("[yellow]Normal text generation[/yellow]")
        response = generate_text(client, "Hello, world!")
        print(response.text)

        # text to video (image grounding)
        rich_print("[yellow]Text to video (image grounding)[/yellow]")
        prompt = "Panning wide shot of a calico kitten sleeping in the sunshine"
        imagen = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
        )
        """
            GenerateImagesResponse(
                generated_images=[
                    GeneratedImage(
                    image=Image(
                        image_bytes=b'\x89PNG\r\n...\rIHDR... Raw profile type iptc...{\x9f"G...',
                        mime_type='image/png'
                    ),
                    safety_attributes=SafetyAttributes()
                    ),
                    GeneratedImage(
                    image=Image(
                        image_bytes=b'\x89PNG\r\n...\rIHDR... Raw profile type iptc...{\x9f"G...',
                        mime_type='image/png'
                    ),
                    safety_attributes=SafetyAttributes()
                    ),
                    GeneratedImage(
                    image=Image(
                        image_bytes=b'\x89PNG\r\n...\rIHDR... Raw profile type iptc...{\x9f"G...',
                        mime_type='image/png'
                    ),
                    safety_attributes=SafetyAttributes()
                    ),
                    GeneratedImage(
                    image=Image(
                        image_bytes=b'\x89PNG\r\n...\rIHDR... Raw profile type iptc...{\x9f"G...',
                        mime_type='image/png'
                    ),
                    safety_attributes=SafetyAttributes()
                    ),
                ]
            )
        """
        # save images
        for i, generated_image in enumerate(imagen.generated_images):
            generated_image.image.save(f"veo3_image_3_{i}.png")

        # text to video
        operation, generated_video = generate_video(
            client,
            prompt=prompt,
            image=imagen.generated_images[0].image,
            sleep_time=10,
            output_video_path="veo3_video_3.mp4",
        )

        # text to video (aspect ratio, negative prompt)
        rich_print("[yellow]Text to video (aspect ratio, negative prompt)[/yellow]")
        prompt = (
            "Cinematic drone flyover of terraced rice fields at golden hour; "
            "soft ambient wind; birds chirping; subtle whoosh as camera passes."
        )
        config = types.GenerateVideosConfig(
            aspect_ratio="16:9",
            negative_prompt="cartoon, low quality"
        )
        operation, generated_video = generate_video(
            client,
            prompt=prompt,
            config=config,
            sleep_time=10,
            output_video_path="veo3_video_2.mp4",
        )

    except Exception as e:
        print(e)
        traceback.print_exc()
        pdb.set_trace()

    pdb.set_trace()

if __name__ == "__main__":
    main()
