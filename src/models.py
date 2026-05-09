from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any
import json

# --- Data Models ---

class ImageData(BaseModel):
    """
    Represents an image within the blog post.
    Can be a 'hero' image or a 'section' image.
    """
    role: str = Field(..., pattern="^(hero|section)$")
    prompt: Optional[str] = None
    asset_id: Optional[str] = None
    heading_ref: Optional[str] = Field(None, description="The heading this image belongs to (for section images)")
    
    # Metadata for the generator to fill
    alt_text: Optional[str] = None

class Section(BaseModel):
    """
    A single section of the blog post.
    """
    heading: str
    body: str  # Markdown content
    image: Optional[ImageData] = None

class Article(BaseModel):
    """
    The Authoritative Content Model for a blog post.
    """
    title: str
    slug: str
    seo_title: str
    meta_description: str
    keywords: List[str]
    excerpt: str
    reading_time_minutes: int
    
    # Structure
    hero_image: Optional[ImageData] = None
    sections: List[Section]

    def to_json(self):
        return self.model_dump_json(indent=2)

# --- Validation Logic ---

def validate_article(article: Article) -> bool:
    """
    Integrity Gate: Ensures the article meets minimum quality standards before publishing.
    """
    errors = []

    # 1. Check Title & Excerpt
    if not article.title or len(article.title) < 5:
        errors.append("Title is missing or too short.")
    if not article.excerpt or len(article.excerpt) < 20:
        errors.append("Excerpt is missing or too short.")

    # 2. Check Hero Image (Must be present in structure, asset_id checked later if strict)
    # For generation phase, we just need the slot to exist.
    # Logic: Hero image MUST be defined in the schema.
    if not article.hero_image:
        errors.append("Article is missing a Hero Image slot.")
    elif article.hero_image.role != "hero":
        errors.append("Hero image has incorrect role.")

    # 3. Check Sections (Min 3)
    if len(article.sections) < 3:
        errors.append(f"Article has too few sections ({len(article.sections)}). Minimum is 3.")

    # 4. Check Section Images (Min 2 defined slots)
    # We count how many sections *intend* to have an image
    section_images = sum(1 for s in article.sections if s.image is not None)
    if section_images < 2:
        errors.append(f"Article has too few section images defined ({section_images}). Minimum is 2.")

    if errors:
        print("\n❌ Article Validation Failed:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print("\n✅ Article Validation Passed!")
    return True
