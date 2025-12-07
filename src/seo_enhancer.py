"""
src/seo_enhancer.py  (UPGRADED)

Enhanced SEO helper for autoblog posts with robust defaults and safe keys.
"""

import os
import re
import json
import datetime
import random
import unicodedata
from typing import Dict, List, Optional, Any

# ---- CONFIG ----
AUTHOR = {
    "name": "Joseph Henry",
    "title": "Founder, GlideX Outsourcing",
    "linkedin": "https://www.linkedin.com/in/joseph-henry-280b4b121?trk=public-profile-join-page",
    "email": "jhenry@glidexoutsourcing.com"
}

SITE_URL = "https://www.glidexoutsourcing.com"
DEFAULT_IMAGE_FOLDER = "static/images"
CALENDLY = "https://calendly.com/glide-xpp/30min"
ORG_NAME = "GlideX Outsourcing"

# ---- helpers ----
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)

def short_summary(text: str, max_len=160) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    idx = text.find(". ", max_len//2)
    if idx != -1 and idx < max_len:
        return text[:idx+1]
    return text[:max_len].rsplit(" ", 1)[0] + "..."

def estimate_reading_time(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    return max(1, int(words / 200))  # 200 wpm

def extract_keyword_candidates(title: str, content: str, max_terms=6) -> List[str]:
    title_terms = [w.lower() for w in re.findall(r"\w+", title) if len(w) > 3]
    keywords = []
    for t in title_terms:
        if t not in keywords:
            keywords.append(t)
        if len(keywords) >= max_terms:
            return keywords
    tokens = re.findall(r"\w+", (content or "").lower())
    freq = {}
    for t in tokens:
        if len(t) > 3:
            freq[t] = freq.get(t, 0) + 1
    for token, _ in sorted(freq.items(), key=lambda x: -x[1]):
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= max_terms:
            break
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1) if len(tokens[i])>3 and len(tokens[i+1])>3]
    for bg in bigrams:
        if bg not in keywords and len(keywords) < max_terms:
            keywords.append(bg)
    return keywords[:max_terms]

def ensure_unique_slug(index: List[Dict], desired_slug: str) -> str:
    existing = {p.get("slug") for p in index if p.get("slug")}
    slug = desired_slug
    counter = 1
    while slug in existing:
        counter += 1
        slug = f"{desired_slug}-{counter}"
    return slug

# ---- meta generation ----
def generate_meta_title(title: str, keywords: List[str], max_len=60) -> str:
    primary = keywords[0] if keywords else title.split(":")[0]
    candidate = f"{primary.title()} | {ORG_NAME}"
    if len(candidate) > max_len:
        short = title.split(":")[0][:max_len-4].rsplit(" ",1)[0] + "..."
        return f"{short} | {ORG_NAME}"
    return candidate

def generate_meta_description(title: str, content: str, keywords: List[str]) -> str:
    primary = keywords[0].replace("-", " ") if keywords else title
    summary = short_summary(content or title, 155)
    if primary.lower() not in summary.lower():
        return f"{primary.title()} — {summary}"
    return summary

# ---- OpenGraph & Twitter ----
def generate_open_graph(meta: Dict) -> Dict:
    og = {
        "og:title": meta.get("meta_title", ""),
        "og:description": meta.get("meta_description", ""),
        "og:type": "article",
        "og:url": meta.get("canonical_url", ""),
    }
    image = meta.get("image")
    if image:
        og["og:image"] = image if image.startswith("http") else f"{SITE_URL}/{image.lstrip('/')}"
    return og

def generate_twitter_card(meta: Dict) -> Dict:
    tw = {
        "twitter:card": "summary_large_image",
        "twitter:title": meta.get("meta_title", ""),
        "twitter:description": meta.get("meta_description", ""),
    }
    image = meta.get("image")
    if image:
        tw["twitter:image"] = image if image.startswith("http") else f"{SITE_URL}/{image.lstrip('/')}"
    return tw

# ---- JSON-LD templates ----
def build_article_jsonld(post_meta: Dict, author: Dict, site_url=SITE_URL) -> Dict:
    url = post_meta.get("canonical_url", f"{site_url}/blog/{post_meta.get('slug','')}")
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": post_meta.get("title", ""),
        "datePublished": post_meta.get("date", ""),
        "dateModified": post_meta.get("dateModified", post_meta.get("date","")),
        "author": {"@type": "Person","name": author.get("name",""),"sameAs": author.get("linkedin")},
        "publisher": {"@type": "Organization","name": ORG_NAME,"url": site_url},
        "description": post_meta.get("meta_description","")[:300],
    }
    if post_meta.get("image"):
        ld["image"] = post_meta["image"] if post_meta["image"].startswith("http") else f"{site_url}/{post_meta['image'].lstrip('/')}"
    if post_meta.get("reading_time"):
        ld["timeRequired"] = f"PT{int(post_meta['reading_time'])*1}M"
    return ld

def build_faq_jsonld(faqs: List[Dict]) -> Optional[Dict]:
    if not faqs:
        return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity":[]}
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type":"Question","name":q.get("q",""),"acceptedAnswer":{"@type":"Answer","text":q.get("a","")}} for q in faqs]
    }

def build_breadcrumb_jsonld(post_meta: Dict, site_url=SITE_URL) -> Dict:
    return {
        "@context":"https://schema.org",
        "@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":site_url},
            {"@type":"ListItem","position":2,"name":"Blog","item":f"{site_url}/blog"},
            {"@type":"ListItem","position":3,"name":post_meta.get("title",""),"item":post_meta.get("canonical_url", f"{site_url}/blog/{post_meta.get('slug','')}")}
        ]
    }

def build_organization_jsonld(site_url=SITE_URL) -> Dict:
    return {"@context":"https://schema.org","@type":"Organization","name":ORG_NAME,"url":site_url,"logo":f"{site_url}/logo.png"}

# ---- internal linking & related posts ----
def choose_internal_links(index: List[Dict], current_slug: str, max_links=3) -> List[Dict]:
    current_cat = next((x.get("category") for x in index if x.get("slug")==current_slug), None)
    same_cat = [p for p in index if p.get("category") == current_cat and p.get("slug") != current_slug]
    picks = []
    if same_cat:
        picks.extend(random.sample(same_cat, min(len(same_cat), max_links)))
    if len(picks) < max_links:
        others = [p for p in index if p.get("slug") != current_slug and p not in picks]
        if others:
            picks.extend(random.sample(others, min(max_links - len(picks), len(others))))
    return [{"title":p.get("title",""),"slug":p.get("slug",""),"excerpt":p.get("excerpt","")[:140],"image":p.get("image")} for p in picks]

# ---- image renaming and alt tags ----
def rename_and_alt_images(images: List[str], keywords: List[str], dest_folder=DEFAULT_IMAGE_FOLDER) -> List[Dict]:
    out = []
    primary = "-".join(re.sub(r"\s+","-",kw) for kw in keywords[:2]) if keywords else "glidex-image"
    for i,img_path in enumerate(images):
        ext = os.path.splitext(img_path)[1] or ".png"
        new_name = f"{primary}-{i+1}{ext}"
        new_path = os.path.join(dest_folder,new_name)
        try:
            if os.path.exists(img_path) and img_path != new_path:
                os.makedirs(dest_folder,exist_ok=True)
                os.replace(img_path,new_path)
            else:
                new_path = img_path
        except Exception:
            new_path = img_path
        alt = f"{keywords[0].replace('-', ' ').title()} image" if keywords else "GlideX Outsourcing image"
        out.append({"path":new_path,"alt":alt,"caption":None})
    return out

# ---- FAQ generation ----
def generate_faqs(title: str, keywords: List[str]) -> List[Dict]:
    primary = keywords[0].replace("-", " ") if keywords else title.split(":")[0]
    faqs = [
        {"q": f"What does {primary} mean for my business?", "a": f"{primary.title()} helps reduce admin load and improve efficiency."},
        {"q": "Are these services compliant and secure?", "a": "GlideX follows strict data protocols and compliance standards."},
        {"q": "How quickly can we onboard a VA unit?", "a": "Typical onboarding is 1–3 weeks depending on role complexity and training needs."}
    ]
    return faqs

# ---- TOC ----
def extract_headings_for_toc(content: str) -> List[Dict]:
    headings = []
    if not content:
        return headings
    for match in re.finditer(r'^(#{2,4})\s+(.*)', content, flags=re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        hid = slugify(text)[:60]
        headings.append({"level":level,"text":text,"id":hid})
    return headings

# ---- meta/html builders ----
def build_meta_html(meta: Dict) -> str:
    lines = []
    lines.append(f"<title>{meta.get('meta_title') or meta.get('title')}</title>")
    lines.append(f'<meta name="description" content="{meta.get("meta_description","")}" />')
    canonical = meta.get("canonical_url") or f"{SITE_URL}/blog/{meta.get('slug','')}"
    lines.append(f'<link rel="canonical" href="{canonical}" />')
    og = generate_open_graph(meta)
    for k,v in og.items():
        if v: lines.append(f'<meta property="{k}" content="{v}" />')
    tw = generate_twitter_card(meta)
    for k,v in tw.items():
        if v: lines.append(f'<meta name="{k}" content="{v}" />')
    if meta.get("image_alt"):
        lines.append(f'<meta name="image:alt" content="{meta.get("image_alt")}" />')
    if meta.get("date"):
        lines.append(f'<meta property="article:published_time" content="{meta.get("date")}" />')
    if meta.get("author_name"):
        lines.append(f'<meta name="author" content="{meta.get("author_name")}" />')
    return "\n".join(lines)

def build_jsonld_scripts(jsonld_dict: Dict[str, Any]) -> str:
    scripts = []
    for key in ["article","faq","breadcrumb","organization"]:
        obj = jsonld_dict.get(key)
        if not obj: continue
        scripts.append(f'<script type="application/ld+json">\n{json.dumps(obj, indent=2)}\n</script>')
    return "\n".join(scripts)

# ---- main enhancer ----
def enhance_post(post: Dict, index: List[Dict], author: Dict = AUTHOR) -> Dict:
    post_meta = post.copy()
    if not post_meta.get("title"):
        raise ValueError("Post must include a title.")
    if not post_meta.get("slug"):
        desired = slugify(post_meta["title"])
        post_meta["slug"] = ensure_unique_slug(index, desired)
    else:
        post_meta["slug"] = ensure_unique_slug(index, slugify(post_meta["slug"]))
    if not post_meta.get("date"):
        post_meta["date"] = datetime.date.today().isoformat()
    if not post_meta.get("excerpt"):
        post_meta["excerpt"] = short_summary(post_meta.get("content",""),140)
    keywords = extract_keyword_candidates(post_meta["title"], post_meta.get("content",""))
    post_meta["keywords"] = keywords
    post_meta["meta_title"] = generate_meta_title(post_meta["title"], keywords)
    post_meta["meta_description"] = generate_meta_description(post_meta["title"], post_meta.get("content",""), keywords)
    post_meta["canonical_url"] = f"{SITE_URL}/blog/{post_meta['slug']}"
    post_meta["reading_time"] = estimate_reading_time(post_meta.get("content",""))
    post_meta["author_name"] = author.get("name")
    post_meta["author_link"] = author.get("linkedin")
    images_meta = rename_and_alt_images(post_meta.get("images",[]), keywords)
    if images_meta:
        post_meta["image"] = images_meta[0]["path"]
        post_meta["image_alt"] = images_meta[0]["alt"]
        post_meta["image_caption"] = images_meta[0].get("caption")
    related = choose_internal_links(index, post_meta["slug"])
    faqs = generate_faqs(post_meta["title"], keywords)
    article_ld = build_article_jsonld(post_meta, author)
    faq_ld = build_faq_jsonld(faqs)
    breadcrumb_ld = build_breadcrumb_jsonld(post_meta)
    organization_ld = build_organization_jsonld()
    jsonld = {"article":article_ld,"faq":faq_ld,"breadcrumb":breadcrumb_ld,"organization":organization_ld}
    toc = extract_headings_for_toc(post_meta.get("content",""))
    meta_html = build_meta_html(post_meta)
    jsonld_html = build_jsonld_scripts(jsonld)
    post_meta["related_posts"] = related
    post_meta["faqs"] = faqs
    post_meta["calendly_cta"] = CALENDLY
    post_meta["toc"] = toc
    return {
        "meta": post_meta,
        "jsonld": jsonld,
        "meta_html": meta_html,
        "jsonld_html": jsonld_html,
        "internal_links": related,
        "images": images_meta,
        "toc": toc
    }

# ---- index helpers ----
def load_index(path="posts_index.json") -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path,"r",encoding="utf-8") as f:
        try: return json.load(f)
        except json.JSONDecodeError: return []

def save_index(index: List[Dict], path="posts_index.json"):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(index,f,ensure_ascii=False,indent=2)
