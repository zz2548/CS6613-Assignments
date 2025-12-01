```
# Start environment
docker compose up -d

# Pull qwen2.5 into Ollama (choose size based on your hardware)
docker compose exec ollama ollama pull qwen2.5:7b
# or qwen2.5:3b for smaller, qwen2.5:14b for larger

# Verify it's working
docker compose exec ollama ollama list
```