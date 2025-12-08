# Erica AI Tutor - GraphRAG System

## Contributor

Jerry Zou (zz2548@nyu.edu)

## Date of Submission

December 7, 2025

## Project Structure

```
├── docker-compose.yml                       # Service orchestration (MongoDB, Ollama, Jupyter)
├── Dockerfile                               # Development container
│
├── ingestion/                               # M2: Data ingestion module, used to contain more files, moved to M2 notebook
│   └── mongo_helper.py                      # MongoDB utility class
│
├── M2_Complete_Ingestion_Pipeline.ipynb     # M2: Data ingestion (185 webpages, ~780K words)
├── M3_GraphRAG_Construction.ipynb           # M3: Knowledge graph construction 
├── M4_Query_Generation.ipynb                # M4: Query processing and answer generation
│
├── knowledge_graph.pkl                      # Serialized NetworkX graph
├── knowledge_graph_full.png                 # Full graph visualization
├── concept_prerequisite_dag.png             # Concept hierarchy visualization
├── M2_ingested_urls.txt                     # List of all ingested URLs
├── m4_prompts.txt                           # System prompts for test questions
└── README.md                                # This file
```

## Instructions

### Setup

1. Start Docker services:
```bash
docker-compose up -d
```

This starts MongoDB (port 27017), Ollama (port 11434), and Jupyter Lab (port 8889).

2. Access Jupyter notebook:
Inside the dev container, run:
```bash
jupyter notebook --ip=0.0.0.0 --port=8889 --no-browser --allow-root
```
Open `http://localhost:8888` in your browser. Use the token from the terminal output to log in.

3. Pull the LLM model (first time only):
```bash
docker exec -it ollama ollama pull qwen2.5:7b
```

### Running the Notebooks

Execute notebooks in order:
1. **M2_Complete_Ingestion_Pipeline.ipynb** - Scrapes course website, extracts PDFs/PPTX
2. **M3_GraphRAG_Construction.ipynb** - Builds knowledge graph from ingested content
3. **M4_Query_Generation.ipynb** - Tests query processing with 3 required questions

Each notebook is self-contained with setup cells at the beginning.

## System Overview

**GraphRAG Pipeline:**
1. Query → Extract candidate concepts (using LLM)
2. Concepts → Build subgraph (prerequisites + related concepts + resources)
3. Subgraph → Generate answer (progressive explanation from simple to complex)

**Knowledge Graph:**
- **309 concept nodes** with difficulty levels and prerequisites
- **237 resource nodes** with exact page/section references
- **75 prerequisite edges** forming a DAG structure
- **230 near-transfer edges** connecting related concepts

## Key Implementation Details

### M2: Data Ingestion
- Recursive webpage crawler with BFS traversal
- PDF/PPTX text extraction with PyPDF2 and python-pptx
- Chunking: 8000 characters with 800 overlap (optimized from initial 2000-char chunks)
- Storage: MongoDB with metadata (word count, timestamps, URLs)

### M3: Knowledge Graph Construction
- LLM-based concept extraction from chunks
- Prerequisite relationship detection
- DAG enforcement via cycle removal and transitive reduction
- Difficulty computation based on prerequisite depth (1-5 scale)

### M4: Query Processing
- Three-tier concept matching: exact, fuzzy, and alias-based
- Subgraph construction: 2-hop prerequisite chains + near-transfer concepts
- Answer generation: Topological sort for progressive scaffolding
- Test questions answered: Attention in Transformers, CLIP, Variational Lower Bound

## Comments

**Chunking optimization:** Initial 2000-character chunks caused processing explosion (2000+ total chunks). Increasing to 8000 characters with 800 overlap reduced chunks by ~75% while improving concept extraction quality.

**Bounded knowledge:** System correctly refuses to answer questions about topics not in the knowledge graph rather than hallucinating, which is pedagogically appropriate for a tutor.

**Performance:** Query pipeline takes 30-60 seconds per question (LLM inference is the main bottleneck at 20-40 seconds).

**Video ingestion:** Attempted but abandoned due to complexity and time constraints. Future work could explore video transcription and integration.

## Acknowledgement

I acknowledge the use of Claude AI (Anthropic) for code debugging, optimization suggestions, and documentation assistance throughout this project.