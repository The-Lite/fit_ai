
PROMPOT_Flayer="""You are a data extraction system.

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
}If multiple products appear in one block, extract them separately only when the name and price match clearly."""