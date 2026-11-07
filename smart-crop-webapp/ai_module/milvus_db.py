"""
milvus_db.py
------------
All Milvus-related database operations for the Smart Crop Disease
Monitoring Robot project.

Uses Milvus Lite (embedded, file-based Milvus) so no server install is
needed -- perfect for a college DA1 demo running off a laptop.

Core operations implemented (mapped to the DA1 rubric):
    1. create_collection()   -> Operation 1: Create Collection
    2. insert_records()      -> Operation 2: Insert Dataset
    3. search_similar()      -> Operation 3: Vector Similarity Search
    4. search_similar(..., filter_expr=...) -> Operation 4: Metadata Filtering
    5. get_by_id() / count() -> Operation 5: Retrieve Results
"""

from pymilvus import MilvusClient, DataType
import numpy as np

DB_PATH = "crop_disease.db"          # Milvus Lite local file (auto-created)
COLLECTION_NAME = "CropDiseaseImages"
EMBEDDING_DIM = 512                  # ResNet18 feature vector size


def get_client(db_path: str = DB_PATH) -> MilvusClient:
    """Connect to (or create) the local Milvus Lite database file."""
    return MilvusClient(uri=db_path)


def create_collection(client: MilvusClient, drop_existing: bool = False):
    """
    Operation 1 - Create Collection.

    Schema (matches the CropDiseaseImages design in the project doc):
        image_id      INT64        (primary key)
        crop_name     VARCHAR(64)
        disease_name  VARCHAR(64)
        severity      VARCHAR(32)
        treatment     VARCHAR(512)
        image_path    VARCHAR(256)
        embedding     FLOAT_VECTOR(512)
    """
    if drop_existing and client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)

    if client.has_collection(COLLECTION_NAME):
        return  # already exists, nothing to do

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(field_name="image_id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="crop_name", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="disease_name", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="severity", datatype=DataType.VARCHAR, max_length=32)
    schema.add_field(field_name="treatment", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="image_path", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
    )
    client.load_collection(COLLECTION_NAME)


def ensure_loaded(client: MilvusClient):
    """Milvus Lite releases the collection between connections; reload it
    before any search/query/get call. Safe to call repeatedly."""
    if client.has_collection(COLLECTION_NAME):
        client.load_collection(COLLECTION_NAME)


def insert_records(client: MilvusClient, records: list[dict]):
    """
    Operation 2 - Insert Dataset.

    `records` is a list of dicts, each shaped like:
        {
            "image_id": 1,
            "crop_name": "Tomato",
            "disease_name": "Early Blight",
            "severity": "Moderate",
            "treatment": "Remove affected leaves and apply fungicide.",
            "image_path": "dataset/tomato_early_blight_01.png",
            "embedding": [0.01, 0.02, ...]   # 512 floats
        }
    """
    if not records:
        return {"insert_count": 0}
    return client.insert(collection_name=COLLECTION_NAME, data=records)


def search_similar(
    client: MilvusClient,
    query_embedding: np.ndarray | list,
    top_k: int = 5,
    filter_expr: str | None = None,
):
    """
    Operation 3 - Vector Similarity Search (cosine similarity).
    Operation 4 - Metadata Filtering (pass e.g. filter_expr='crop_name == "Tomato"').

    Returns a list of hits, each with entity fields + a 'distance'
    (cosine similarity score, higher = more similar, since metric_type=COSINE).
    """
    vec = np.asarray(query_embedding, dtype=np.float32).tolist()
    ensure_loaded(client)

    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[vec],
        limit=top_k,
        filter=filter_expr or "",
        output_fields=["crop_name", "disease_name", "severity", "treatment", "image_path"],
    )
    return results[0] if results else []


def get_by_id(client: MilvusClient, image_id: int):
    """Operation 5 - Retrieve a single record by primary key."""
    ensure_loaded(client)
    res = client.get(collection_name=COLLECTION_NAME, ids=[image_id])
    return res[0] if res else None


def count(client: MilvusClient) -> int:
    """Number of vectors currently stored (shown in the sidebar)."""
    if not client.has_collection(COLLECTION_NAME):
        return 0
    stats = client.get_collection_stats(COLLECTION_NAME)
    return int(stats.get("row_count", 0))


def distinct_crops(client: MilvusClient) -> list[str]:
    """Helper for the Streamlit filter dropdown."""
    if count(client) == 0:
        return []
    ensure_loaded(client)
    rows = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["crop_name"],
        limit=1000,
    )
    return sorted({r["crop_name"] for r in rows})
