import os
import asyncio
import base64
import io
import json
import re
from anthropic import AsyncAnthropic,DefaultAioHttpClient,Anthropic
from pathlib import Path
from PIL import Image
from termcolor import cprint
from dotenv import load_dotenv
load_dotenv()
key=os.environ.get("ANTHROPIC_API_KEY")
async def get_items_info(path:str)-> None:
    files = os.listdir(path)                                               
    async with AsyncAnthropic(
        api_key=key,
        http_client=DefaultAioHttpClient(),
    ) as client:
        message = await client.messages.create(
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": "Hello, Claude",
                }
            ],
            model="claude-opus-4-6",
        )
        print(message.content)


#asyncio.run(get_items_info())

def get_item_info(file:str, img_type:str, output_path: Path = None) -> None:
    client = Anthropic(api_key=key)                                           
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
                {"type": "text", "text": """You are a data extraction system.

Extract only healthy food items from this grocery flyer and return the result in JSON.

Allowed categories:
- protein
- vegetables
- fruits
- dairy
- legumes
- whole_grains
- healthy_fats
- seafood

Do not extract:
- non-food items
- junk food
- soda
- candy
- chips
- alcohol
- store promotions without a clear food item
- membership ads
- household items

For each accepted item, return:
- item_name
- price
- category

Important rules:
- Output must be ONLY raw JSON
- Do NOT wrap the response in ``` or ```json
- Do NOT add the word "json"
- Do NOT add explanations, comments, or text before or after
- Return exactly one JSON object
- Skip unclear items
- Skip duplicate items
- Keep the price text exactly as shown

Return exactly this structure:
{
  "items": [
    {
      "item_name": "string",
      "price": "string",
      "category": "string"
    }
  ]
}If multiple products appear in one block, extract them separately only when the name and price match clearly."""},
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


if __name__ == "__main__":
    img_path = Path("/home/lite/Desktop/Projects/FitnessAI/fit_ai/backend/data/data_test/flayers/maxi/img/page_00.png")
    img = Image.open(img_path)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    while buffer.tell() > 5 * 1024 * 1024:
        buffer = io.BytesIO()
        img = img.resize((int(img.width * 0.8), int(img.height * 0.8)), Image.LANCZOS)
        img.save(buffer, format="JPEG", quality=85)
    file = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    output = Path("/home/lite/Desktop/Projects/FitnessAI/fit_ai/backend/data/data_test/flayers/maxi/json_data/page_00.json")
    get_item_info(file, "image/jpeg", output_path=output)
 