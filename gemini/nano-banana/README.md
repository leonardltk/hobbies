# Nano banana usage
Inspired by https://github.com/google-gemini/veo-3-nano-banana-gemini-api-quickstart

# set up
```bash
uv init
uv add rich dotenv jupyterlab
uv add google-genai Pillow

uv add xxx
uv add xxx
uv add xxx
```

# Image generation
```bash
uv run main.py img \
    --engine imagen4 \
    --prompt "Robot holding a red skateboard" \
    --n 1 \
    --aspect 1:1 \

uv run main.py img \
    --engine gemini \
    --prompt "Robot holding a red skateboard" \
    --n 1 \
    --aspect 1:1 \

```

# Image edit
```bash
uv run main.py edit \
    --prompt "Let robot A from image 1 spray blue paint on on Robot B's skateboard from image 2; warm film look" \
    --input "imagen4-1.png" "gemini-image-1.png"

```

# Video generation
## Text to Video
```bash
uv run main.py video \
    --prompt "In the Ilios map with the hole, Tracer blinking around Roadhog, with Roadhog trying to hook her" \
    --aspect 16:9 \
    --resolution 1080p
```
## Text + Image to Video
```bash
uv run main.py video \
    --prompt "Let this man run to a boat in the lake of Varenna and drive off into the sunset in a 007 fashion" \
    --image "LL-varenna.png" \
    --aspect 16:9 \
    --resolution 720p

```
