#!/usr/bin/env python3
"""
build_cafe_faiss_index.py

Builds a persistent FAISS index from MongoDB menu items.
Outputs:
  - storage/cafe_faiss/index.faiss
  - storage/cafe_faiss/metadata.jsonl
  - storage/cafe_faiss/config.json

Run manually or in CI/CD when menu changes.
"""

import os
import json
import sys
import datetime
from typing import Dict, List

import faiss
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# -----------------------------
# Configuration (edit if needed)
# -----------------------------

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "rabusteCafe"

MENUITEMS_COLLECTION = "menuitems"
CATEGORIES_COLLECTION = "menucategories"
SUBCATEGORIES_COLLECTION = "menuSubCategories"
GROUPS_COLLECTION = "menugroups"

STORAGE_DIR = "storage/cafe_faiss"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIMENSION = 384
FAISS_INDEX_TYPE = "IndexFlatIP"

# -----------------------------
# Helpers
# -----------------------------


def fatal(msg: str):
    print(f"\n[FATAL] {msg}\n", file=sys.stderr)
    sys.exit(1)


def ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def load_lookup_maps(db):
    """Load category, subcategory, group names for denormalization."""
    categories = {
        c["_id"]: c.get("name", "")
        for c in db[CATEGORIES_COLLECTION].find({})
    }
    subcategories = {
        s["_id"]: s.get("name", "")
        for s in db[SUBCATEGORIES_COLLECTION].find({})
    }
    groups = {
        g["_id"]: g.get("name", "")
        for g in db[GROUPS_COLLECTION].find({})
    }
    return categories, subcategories, groups


def serialize_menu_item(
    item: Dict,
    categories: Dict,
    subcategories: Dict,
    groups: Dict,
) -> str:
    """Convert a MongoDB menu item into canonical embedding text."""

    name = item.get("name", "").strip()
    if not name:
        fatal(f"Menu item missing name: {item}")

    price = None
    prices = item.get("prices", [])
    if prices and isinstance(prices, list):
        price = prices[0].get("price")

    if price is None:
        fatal(f"Menu item missing price: {item.get('_id')}")

    category_name = categories.get(item.get("categoryId"), "")
    subcategory_name = subcategories.get(item.get("subCategoryId"), "")
    group_name = groups.get(item.get("groupId"), "")

    availability = "In stock" if item.get("inStock", False) else "Out of stock"

    text = (
        f"Item: {name}\n"
        f"Category: {category_name}\n"
        f"Subcategory: {subcategory_name}\n"
        f"Section: {group_name}\n"
        f"Price: {price} INR\n"
        f"Availability: {availability}"
    )

    return text


# -----------------------------
# Main build routine
# -----------------------------


def main():
    print("🔧 Building Cafe FAISS Index...\n")

    ensure_storage_dir()

    # ---- MongoDB connection
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
    except Exception as e:
        fatal(f"Failed to connect to MongoDB: {e}")

    # ---- Load lookup tables
    categories, subcategories, groups = load_lookup_maps(db)

    # ---- Fetch menu items
    menu_items = list(db[MENUITEMS_COLLECTION].find({}))
    if not menu_items:
        fatal("No menu items found in MongoDB.")

    print(f"✔ Loaded {len(menu_items)} menu items")

    # ---- Load embedding model
    print(f"✔ Loading embedding model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    texts: List[str] = []
    metadata: List[Dict] = []

    # ---- Serialize items
    for idx, item in enumerate(menu_items):
        text = serialize_menu_item(
            item=item,
            categories=categories,
            subcategories=subcategories,
            groups=groups,
        )
        texts.append(text)

        metadata.append(
            {
                "vector_id": idx,
                "item_id": str(item["_id"]),
                "name": item.get("name"),
                "price": item.get("prices", [{}])[0].get("price"),
                "inStock": item.get("inStock", False),
                "categoryId": item.get("categoryId"),
                "subCategoryId": item.get("subCategoryId"),
                "groupId": item.get("groupId"),
            }
        )

    # ---- Generate embeddings
    print("✔ Generating embeddings")
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    if embeddings.shape[1] != VECTOR_DIMENSION:
        fatal(
            f"Embedding dimension mismatch: "
            f"expected {VECTOR_DIMENSION}, got {embeddings.shape[1]}"
        )

    # ---- Build FAISS index
    print("✔ Building FAISS index")
    index = faiss.IndexFlatIP(VECTOR_DIMENSION)
    index.add(embeddings)

    if index.ntotal != len(metadata):
        fatal("FAISS index count mismatch")

    # ---- Persist artifacts
    index_path = os.path.join(STORAGE_DIR, "index.faiss")
    metadata_path = os.path.join(STORAGE_DIR, "metadata.jsonl")
    config_path = os.path.join(STORAGE_DIR, "config.json")

    print("✔ Writing FAISS index to disk")
    faiss.write_index(index, index_path)

    print("✔ Writing metadata.jsonl")
    with open(metadata_path, "w", encoding="utf-8") as f:
        for record in metadata:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("✔ Writing config.json")
    config = {
        "embedding_model": EMBEDDING_MODEL_NAME,
        "dimension": VECTOR_DIMENSION,
        "index_type": FAISS_INDEX_TYPE,
        "menu_version": datetime.date.today().isoformat(),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "num_items": len(metadata),
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print("\n✅ Cafe FAISS index build complete")
    print(f"📁 Output directory: {STORAGE_DIR}")
    print(f"   - index.faiss")
    print(f"   - metadata.jsonl")
    print(f"   - config.json")


# -----------------------------
# Entrypoint
# -----------------------------

if __name__ == "__main__":
    main()
