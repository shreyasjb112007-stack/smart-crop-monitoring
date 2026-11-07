# Smart Crop Disease Monitoring Robot — DA1 Report

## 1. EER Model

### 1.1 Entities and key attributes

| Entity | Key attributes |
|---|---|
| **Farmer** | farmer_id (PK), name, phone, address |
| **Farm** | farm_id (PK), farmer_id (FK), location, area_acres |
| **Crop** | crop_id (PK), farm_id (FK), crop_name, planting_date |
| **Robot** | robot_id (PK), model, status |
| **Inspection** | inspection_id (PK), crop_id (FK), robot_id (FK), inspection_date |
| **Image** | image_id (PK), inspection_id (FK), image_path, embedding |
| **Disease** | disease_id (PK), disease_name, crop_name |
| **Treatment** | treatment_id (PK), disease_id (FK), severity, recommended_action |

### 1.2 Relationships and cardinality

| Relationship | Participating entities | Cardinality |
|---|---|---|
| owns | Farmer – Farm | 1 : N |
| contains | Farm – Crop | 1 : N |
| inspected_by | Crop – Inspection | 1 : N |
| performs | Robot – Inspection | 1 : N |
| captures | Inspection – Image | 1 : N |
| diagnosed_as | Image – Disease | N : M (via the vector-search result — an image is matched against candidate diseases with a similarity score) |
| treated_by | Disease – Treatment | 1 : N (a disease can have severity-graded treatments) |

The `diagnosed_as` relationship is the interesting one: it is **not a stored fact**, it is the *output of the Milvus similarity search* at query time (image embedding → nearest disease embedding). We still model it as an EER relationship because it needs to be captured for the relational/report layer (e.g. logging every diagnosis made, with its similarity score, for audit and analytics).

See `EER_diagram.png` in this folder for the full diagram (also reproducible from `eer_diagram.py`).

### 1.3 Notes on design decisions

- `Image.embedding` is modelled as an attribute of Image in the conceptual EER diagram, but physically it is **not stored in a relational table** — it lives in Milvus as a 512-D vector, linked back by `image_id`. This is deliberate: Section 13 explains why.
- `Disease.crop_name` is a controlled redundancy — a disease like "Early Blight" behaves differently (and has a different treatment) depending on the crop, so `(crop_name, disease_name)` together identify a diagnosis class, not `disease_name` alone.

---

## 2. Normalization (UNF → BCNF)

### 2.1 Starting point: the unnormalized log table

Before any modelling, the raw data the robot logs looks like a single flat table (this is what you'd get from a naive CSV export of every inspection event):

**`InspectionLog`** (UNF)

| inspection_id | farmer_name | farmer_phone | farm_location | crop_name | planting_date | robot_model | inspection_date | image_path | disease_name | severity | treatment_action | similarity_score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

This single table mixes farmer data, farm data, crop data, robot data, inspection data, image data, and diagnosis data — classic unnormalized design.

**Functional Dependencies (FDs) observed:**

```
FD1: inspection_id → farmer_name, farmer_phone, farm_location, crop_name,
                      planting_date, robot_model, inspection_date, image_path
FD2: farmer_phone   → farmer_name                (phone uniquely identifies a farmer)
FD3: farm_location  → farmer_phone                (each farm belongs to exactly one farmer)
FD4: disease_name   → treatment_action, severity  (a disease has a standard severity/treatment)
FD5: image_path     → disease_name, similarity_score   (result of the vector search for that image)
```

### 2.2 1NF

The table is already made of atomic values (no repeating groups/multi-valued cells), so `InspectionLog` satisfies **1NF** as given.

### 2.3 2NF — remove partial dependencies

Because `inspection_id` is the only candidate key of the *whole* table but attributes like `disease_name` really depend on `image_path` (not on `inspection_id` directly), and `farmer_name` depends on `farmer_phone` (not on `inspection_id`), we have **partial dependencies** relative to composite reasoning. Decomposing to remove them:

```
Farmer(farmer_phone PK, farmer_name)
FarmInspectionCore(inspection_id PK, farm_location, crop_name, planting_date,
                    robot_model, inspection_date, image_path, farmer_phone FK)
ImageDiagnosis(image_path PK, disease_name, similarity_score)
```

### 2.4 3NF — remove transitive dependencies

`FarmInspectionCore` still has transitive dependencies: `farm_location` determines `farmer_phone` (FD3), and `disease_name` (reachable transitively through `image_path`) determines `treatment_action`/`severity` (FD4) rather than the treatment depending directly on the whole key. Decomposing further:

```
Farmer(farmer_phone PK, farmer_name)
Farm(farm_location PK, farmer_phone FK)
CropRecord(inspection_id PK, farm_location FK, crop_name, planting_date)
Robot(robot_model PK)                      -- trivial 1-attribute relation, folded into Inspection in final schema
Inspection(inspection_id PK, robot_model FK, inspection_date, image_path)
Image(image_path PK, inspection_id FK)
Disease(disease_name PK, treatment_action, severity)
Diagnosis(image_path FK, disease_name FK, similarity_score)   -- composite PK (image_path, disease_name)
```

Every non-key attribute now depends **only on the whole key**, and no non-key attribute determines another non-key attribute. This is **3NF**.

### 2.5 BCNF check

BCNF requires that for every non-trivial FD `X → Y`, `X` must be a **superkey**. Checking each relation above:

| Relation | FDs | Determinant a superkey? | BCNF? |
|---|---|---|---|
| Farmer | farmer_phone → farmer_name | Yes | ✅ |
| Farm | farm_location → farmer_phone | Yes | ✅ |
| CropRecord | inspection_id → farm_location, crop_name, planting_date | Yes | ✅ |
| Inspection | inspection_id → robot_model, inspection_date, image_path | Yes | ✅ |
| Image | image_path → inspection_id | Yes | ✅ |
| Disease | disease_name → treatment_action, severity | Yes | ✅ |
| Diagnosis | (image_path, disease_name) → similarity_score | Yes | ✅ |

Every relation is in **BCNF** — every determinant is a candidate key, so there are no anomalies left to remove.

### 2.6 Final relational schema (used for the metadata side of the system)

```
Farmer(farmer_id PK, name, phone UNIQUE, address)
Farm(farm_id PK, farmer_id FK → Farmer, location, area_acres)
Crop(crop_id PK, farm_id FK → Farm, crop_name, planting_date)
Robot(robot_id PK, model, status)
Inspection(inspection_id PK, crop_id FK → Crop, robot_id FK → Robot, inspection_date)
Image(image_id PK, inspection_id FK → Inspection, image_path)
Disease(disease_id PK, disease_name, crop_name)
Treatment(treatment_id PK, disease_id FK → Disease, severity, recommended_action)
Diagnosis(image_id FK → Image, disease_id FK → Disease, similarity_score,
          PRIMARY KEY(image_id, disease_id))
```

This is the schema you would hand-write for the "database schema/model design" part of the report. `farmer_id`/`crop_id`/etc. (surrogate integer keys) are used instead of natural keys like `phone`/`location` in the final schema for stability, but the FD/normalization *reasoning* above is what justifies the decomposition.

**Important distinction (see Section 13 of the project doc):** this BCNF analysis applies to the **relational/metadata side** of the system (Farmer, Farm, Crop, Robot, Inspection, Disease, Treatment, Diagnosis-log). It does **not** apply to Milvus — Milvus is a vector database, not a relational one, and normal forms are a relational-model concept that don't map onto how Milvus stores/indexes vectors. The `CropDiseaseImages` Milvus collection is a deliberately **denormalized** document-like structure (crop_name, disease_name, severity, treatment, image_path, embedding all in one collection) — this is normal and correct for Milvus, because:

1. Milvus doesn't support multi-collection JOINs, so normalizing would force joins back in application code for every single search.
2. The scalar fields (crop_name, disease_name, severity, treatment) are stored purely to make **metadata filtering** possible alongside vector search — they are a queryable payload, not a normalized relation.

---

## 3. Comparative Analysis — Why Milvus over a relational DB (MySQL/PostgreSQL)

| Requirement | Relational DB (MySQL/PostgreSQL) | Milvus |
|---|---|---|
| Store farmer/farm/crop/treatment metadata | ✅ Excellent fit (structured, relational) | ⚠️ Possible but awkward — no real relational/JOIN support |
| "Find images visually similar to this new crop photo" | ❌ Not natively possible. Would need a `pgvector`-style extension bolted on, or brute-force distance computation in application code — doesn't scale | ✅ Purpose-built: ANN (approximate nearest neighbor) indexing (HNSW/IVF/AUTOINDEX) makes this fast even at millions of vectors |
| High-dimensional vector storage (512-D ResNet embeddings) | Requires extensions; not a first-class type in standard MySQL | ✅ First-class `FLOAT_VECTOR` type |
| Similarity metric (cosine similarity) | Must be implemented manually (e.g., a stored function calculating cosine distance row-by-row — O(n) per query) | ✅ Built-in COSINE/L2/IP metrics with indexed search — sub-linear query time |
| Combine similarity search + structured filtering (e.g. "only Tomato, only High severity") | Filtering is trivial, but there's no similarity search to combine it with | ✅ Native **hybrid search**: vector search + scalar (`filter=`) expression in a single query |
| Scalability to a large image dataset (10⁴–10⁷ images) | Full-table distance scans become infeasible | ✅ Designed for this scale via ANN indexing |
| ACID transactions across farmer/farm/treatment records | ✅ Strong | ⚠️ Weaker consistency guarantees — not built for transactional metadata |

**Conclusion used in the report/PPT:**
> The application's core operation — "given a new crop image, find the most visually similar previously stored disease images" — is fundamentally a high-dimensional nearest-neighbor search problem, which relational databases are not designed to solve efficiently. Milvus is purpose-built for exactly this (embedding storage + ANN similarity search + metadata filtering in one query), which is why it is the primary database technology for this project, with a normalized relational schema conceptually backing the structured metadata (Farmer/Farm/Crop/Treatment).

---

## 4. Core Operations Demonstrated (maps to code)

| # | Operation | Function | File |
|---|---|---|---|
| 1 | Create Collection (schema definition) | `create_collection()` | `milvus_db.py` |
| 2 | Insert Dataset (metadata + embeddings) | `insert_records()` | `milvus_db.py` |
| 3 | Vector Similarity Search (cosine) | `search_similar()` | `milvus_db.py` |
| 4 | Metadata Filtering (scalar `filter=` expr, e.g. `crop_name == "Tomato"`) | `search_similar(..., filter_expr=...)` | `milvus_db.py` |
| 5 | Retrieve Results (by ID / row count / distinct crops) | `get_by_id()`, `count()`, `distinct_crops()` | `milvus_db.py` |

All five were tested directly (see commit history / terminal output during development) with a 6-record and then a 40-record synthetic dataset — inserts, cosine search, and combined `crop_name == "Tomato" and severity == "High"`-style filters all return correct results, including after reconnecting to the Milvus Lite file fresh (simulating separate `streamlit run` sessions).
