FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pymongo \
    requests \
    beautifulsoup4 \
    yt-dlp \
    PyPDF2 \
    python-dotenv \
    jupyter \
    pandas \
    numpy \
    networkx \
    openai

# Keep container running
CMD ["tail", "-f", "/dev/null"]
