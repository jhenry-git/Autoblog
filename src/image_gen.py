
import os
import time
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# Initialize Client
# We use os.getenv so it works with the environment variable or falls back if needed
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # Optional: Hardcode for local testing if env var fails
    # API_KEY = "YOUR_HARDCODED_KEY_HERE"
    pass

client = genai.Client(api_key=API_KEY) if API_KEY else None

def enhance_prompt(raw_prompt):
    """Refines the blog topic into a detailed image prompt."""
    if not client: return raw_prompt
    
    print(f"✨ Enhancing image prompt for: '{raw_prompt}'...")
    enhancer_model = "gemini-2.5-flash"
    
    system_instruction = (
        "You are an expert AI image prompt engineer. Your task is to take a blog topic "
        "and rewrite it into a detailed, descriptive prompt for a featured blog image. "
        "Focus on professional, editorial, or futuristic styles depending on the topic. "
        "Output ONLY the refined prompt text."
    )
    
    try:
        response = client.models.generate_content(
            model=enhancer_model,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
            contents=[raw_prompt]
        )
        return response.text.strip()
    except Exception:
        return raw_prompt

# --- THIS IS THE FUNCTION YOUR MAIN.PY IS LOOKING FOR ---
def generate_blog_image(topic, output_dir="generated_images"):
    """Main function to generate an image for a blog post."""
    if not client:
        print("⚠️ Skipping image generation (No API Key).")
        return None

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # 1. Enhance the prompt based on the blog topic
    final_prompt = enhance_prompt(topic)
    
    print(f"🎨 Generating image for topic: {topic}...")
    
    # 2. Safety Config (High tolerance for creative blogs)
    safety_config = [
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
    ]

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[final_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=safety_config,
            )
        )
        
        # 3. Save Image
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img = Image.open(BytesIO(part.inline_data.data))
                    
                    # Name the file based on the topic (sanitized)
                    safe_name = "".join([c if c.isalnum() else "_" for c in topic[:20]])
                    filename = f"{output_dir}/{safe_name}_{int(time.time())}.png"
                    
                    img.save(filename)
                    print(f"✅ Image saved: {filename}")
                    return filename
        
        print("❌ Image generation failed (No data returned).")
        return None

    except Exception as e:
        print(f"❌ Image generation error: {e}")
        return None
