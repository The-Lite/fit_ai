import os
import asyncio
import base64
import io
import json
import re
from sys import path
from anthropic import AsyncAnthropic, Anthropic
from pathlib import Path
from PIL import Image
from termcolor import cprint
from dotenv import load_dotenv
from backend.app.agent.prompt.prompts import PROMPOT_Flayer
from backend.utils.global_var import CLAUDE_API_KEY
from backend.utils.load_config import load_config


load_dotenv()


def get_item_info(file:str, img_type:str, output_path: Path = None) -> None:
    client = Anthropic(api_key=CLAUDE_API_KEY)                                           
    #cprint(f"File: {file}", "blue", attrs=["bold"])
    message = client.messages.create(
        max_tokens=1024,
            messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_type,
                        "data": file,
                    },
                },
                {"type": "text", "text": PROMPOT_Flayer},
            ],
        }
    ],

        model="claude-haiku-4-5-20251001",
    )
    raw = message.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {raw}")
    result = json.loads(match.group())
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        cprint(f"Saved to {output_path}", "green")
    return result


_MAX_BYTES = 4 * 1024 * 1024  # 4 MB — stays well under the 5 MB API limit


def _img_to_base64(img_path: Path) -> tuple[str, str]:
    """Convert an image file to base64 string, resizing until under 4 MB. Returns (b64_data, media_type)."""
    img = Image.open(img_path).convert("RGB")
    quality = 85

    def _encode(image: Image.Image, q: int) -> bytes:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=q)
        return buf.getvalue()

    data = _encode(img, quality)

    # aggressive one-shot resize for very large images
    if len(data) > 20 * 1024 * 1024:
        scale = (_MAX_BYTES / len(data)) ** 0.5
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        data = _encode(img, quality)

    # step-down loop: shrink dimensions then drop quality until under limit
    while len(data) > _MAX_BYTES:
        if quality > 60:
            quality -= 10
            data = _encode(img, quality)
        else:
            img = img.resize((int(img.width * 0.8), int(img.height * 0.8)), Image.LANCZOS)
            data = _encode(img, quality)

    cprint(f"Image size: {len(data):,} bytes (quality={quality})", "cyan")
    return base64.standard_b64encode(data).decode("utf-8"), "image/jpeg"


async def _get_item_info_async(client: AsyncAnthropic, img_path: Path, file_ignored: list) -> tuple[str, dict] | None:
    """Async version of get_item_info for a single image. Returns (filename, result) or None if ignored."""
    numbers_in_name = re.findall(r'\d+', img_path.stem)
    if any(n in file_ignored for n in numbers_in_name):
        cprint(f"Skipped {img_path.name} (number in ignored list)", "yellow")
        return None

    b64_data, media_type = _img_to_base64(img_path)
    message = await client.messages.create(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    },
                    {"type": "text", "text": PROMPOT_Flayer},
                ],
            }
        ],
        model="claude-haiku-4-5-20251001",
    )
    raw = message.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response for {img_path.name}: {raw}")
    result = json.loads(match.group())
    cprint(f"Processed {img_path.name}", "cyan")
    return img_path.name, result


async def process_folder_async(folder: str | Path, output_path: Path, file_ignored: list = None) -> dict:
    """
    Process all images in a folder concurrently and save combined results to a single JSON file.

    Args:
        folder: Path to the folder containing images.
        output_path: Path to the output JSON file.
        file_ignored: List of number strings to skip (e.g. ["01", "03"] skips page_01.png, page_03.png).

    Returns:
        Dict mapping filename -> extracted item info.
    """
    folder = Path(folder)
    file_ignored = file_ignored or []
    img_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    img_paths = sorted([p for p in folder.iterdir() if p.suffix.lower() in img_extensions])

    if not img_paths:
        cprint(f"No images found in {folder}", "yellow")
        return {}

    cprint(f"Processing {len(img_paths)} image(s) from {folder} concurrently...", "blue", attrs=["bold"])

    async with AsyncAnthropic(api_key=CLAUDE_API_KEY) as client:
        tasks = [_get_item_info_async(client, p, file_ignored) for p in img_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    combined: dict = {}
    for item in results:
        if item is None:
            pass  # skipped by file_ignored
        elif isinstance(item, Exception):
            cprint(f"Error processing an image: {item}", "red")
        else:
            filename, data = item
            combined[filename] = data

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    cprint(f"Saved {len(combined)} result(s) to {output_path}", "green", attrs=["bold"])

    return combined


if __name__ == "__main__":
    cfg_data=load_config(config_path="config.json")
    _order = ["Metro", "SuperC"]
    files_ignored = {k: cfg_data["flayers"][k]["Pages_ignored"] for k in _order if k in cfg_data["flayers"] and "Pages_ignored" in cfg_data["flayers"][k]}
    list_of_ignored = [data for data in files_ignored.values()]

    path_parent = Path(__file__).parent.parent.parent.parent / "data/data_test/flayers"
    list_of_folders_in = [str(path_parent / folder / "img/") for folder in _order]
    list_of_folders_out = [str(path_parent / folder / "json/") for folder in _order]
    
    for i in range(len(list_of_folders_in)):
        ignored_pages = list_of_ignored[i] if i < len(list_of_ignored) else []
        cprint(f"Processing folder: {list_of_folders_in[i]} with ignored pages: {ignored_pages}", "magenta", attrs=["bold"])
        asyncio.run(process_folder_async(list_of_folders_in[i], Path(list_of_folders_out[i]) / "result.json", file_ignored=ignored_pages))
