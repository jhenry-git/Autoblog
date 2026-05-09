
import os
import time
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# Initialize Client
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Set it in your .env file.")

client = genai.Client(api_key=API_KEY) if API_KEY else None

# ---------------------------------------------------------------------------
# Retry Decorator
# ---------------------------------------------------------------------------
def retry_on_failure(max_retries=3, delay=2, backoff=2):
    """Decorator to retry a function on failure with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = delay * (backoff ** attempt)
                    print(f"⚠️ Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator

# ---------------------------------------------------------------------------
# Prompt Enhancement
# ---------------------------------------------------------------------------
def enhance_prompt(role, raw_context):
    """
    Refines the prompt based on the role (hero/section).
    
    Args:
        role (str): 'hero' or 'section'
        raw_context (str): The raw prompt/context provided by the content generator.
    """
    if not client: 
        return raw_context
    
    print(f"✨ Enhancing image prompt ({role}): '{raw_context[:50]}...'")
    enhancer_model = "gemini-2.5-flash"
    
    if role == "hero":
        system_instruction = (
            "You are an expert AI art director. Refine this text into a prompt for a "
            "HIGH-IMPACT FEATURED BLOG IMAGE. Style: Modern, Editorial, Cinematic Lighting, 16:9 aspect ratio vibes. "
            "Avoid text in the image. Return ONLY the prompt."
        )
    else:
        system_instruction = (
            "You are an expert AI illustrator. Refine this text into a prompt for an "
            "IN-ARTICLE SECTION ILLUSTRATION. Style: Clean, Vector-art or Minimalist Tech style, informative. "
            "Focus on the specific concept described. Return ONLY the prompt."
        )
    
    try:
        response = client.models.generate_content(
            model=enhancer_model,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
            contents=[raw_context]
        )
        return response.text.strip()
    except Exception:
        return raw_context

# ---------------------------------------------------------------------------
# Single Image Generation (with retry)
# ---------------------------------------------------------------------------
@retry_on_failure(max_retries=3, delay=2, backoff=2)
def _generate_single_image(role: str, prompt_context: str, output_dir: str = "generated_images") -> Optional[str]:
    """
    Internal function to generate a single image. Wrapped with retry logic.
    """
    if not client:
        print("⚠️ Skipping image generation (No API Key).")
        return None

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # 1. Enhance the prompt
    final_prompt = enhance_prompt(role, prompt_context)
    
    print(f"🎨 Generating {role} image...")
    
    # 2. Safety Config
    safety_config = [
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
    ]

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
                
                # Name the file based on role and timestamp
                safe_name = f"{role}_{int(time.time())}_{hash(prompt_context) % 1000}"
                filename = f"{output_dir}/{safe_name}.png"
                
                img.save(filename)
                print(f"✅ Image saved: {filename}")
                return filename
    
    print("❌ Image generation failed (No data returned).")
    return None

def generate_blog_image(role, prompt_context, output_dir="generated_images"):
    """
    Main function to generate a single image for a blog post.
    This is a convenience wrapper around _generate_single_image.
    
    Args:
        role (str): 'hero' or 'section'
        prompt_context (str): The detailed prompt context.
        output_dir (str): Directory to save images.
    """
    return _generate_single_image(role, prompt_context, output_dir)

# ---------------------------------------------------------------------------
# Parallel Image Generation
# ---------------------------------------------------------------------------
def generate_all_blog_images(image_jobs: List[Dict], max_workers: int = 3, output_dir: str = "generated_images") -> Dict[str, Optional[str]]:
    """
    Generate multiple blog images in parallel using ThreadPoolExecutor.
    
    Args:
        image_jobs: List of dicts, each containing:
            - 'role': 'hero' or 'section'
            - 'prompt': The prompt context string
            - 'id': Unique identifier for this job (e.g., 'hero' or 'section_1')
        max_workers: Maximum number of concurrent threads
        output_dir: Directory to save images
        
    Returns:
        dict: Mapping of job_id -> file_path or None if failed.
        Example: {'hero': 'generated_images/hero_12345.png', 'section_1': None}
    """
    if not client:
        print("⚠️ Skipping parallel image generation (No API Key).")
        return {}
    
    if not image_jobs:
        return {}
    
    print(f"🚀 Starting parallel generation for {len(image_jobs)} images (max {max_workers} workers)...")
    
    results = {}
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all image generation tasks
        future_to_job = {
            executor.submit(_generate_single_image, job['role'], job['prompt'], output_dir): job['id']
            for job in image_jobs
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_job):
            job_id = future_to_job[future]
            try:
                result = future.result()
                results[job_id] = result
                completed_count += 1
                if result:
                    print(f"  ✅ [{job_id}] Generated successfully")
                else:
                    print(f"  ⚠️ [{job_id}] Generation returned None")
            except Exception as e:
                print(f"  ❌ [{job_id}] Generation failed: {e}")
                results[job_id] = None
    
    success_count = sum(1 for r in results.values() if r is not None)
    print(f"🏁 Parallel generation complete: {success_count}/{len(image_jobs)} images generated.")
    
    return results

def prepare_jobs_from_article(article) -> List[Dict]:
    """
    Prepare image generation jobs from an Article object.
    
    Args:
        article: Article model instance from src.models
        
    Returns:
        List of job dicts for generate_all_blog_images()
    """
    jobs = []
    
    # Hero image
    if article.hero_image and article.hero_image.prompt:
        jobs.append({
            'role': 'hero',
            'prompt': article.hero_image.prompt,
            'id': 'hero'
        })
    
    # Section images
    for i, section in enumerate(article.sections):
        if section.image and section.image.prompt:
            jobs.append({
                'role': 'section',
                'prompt': section.image.prompt,
                'id': f'section_{i}'
            })
    
    return jobs