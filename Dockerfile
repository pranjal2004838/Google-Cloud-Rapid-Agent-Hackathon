FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for MongoDB MCP server
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install MongoDB MCP server globally via npm
RUN npm install -g mongodb-mcp-server

# Install Python dependencies
COPY cliniqai/requirements.txt .
# Add google-cloud-logging, google-cloud-kms, google-cloud-pubsub, google-cloud-tasks
RUN echo "google-cloud-logging>=3.8.0" >> requirements.txt && \
    echo "google-cloud-kms>=2.21.0" >> requirements.txt && \
    echo "google-cloud-pubsub>=2.19.0" >> requirements.txt && \
    echo "google-cloud-tasks>=2.15.0" >> requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY cliniqai/ ./cliniqai/

# Set PYTHONPATH so Python can find the agent module
ENV PYTHONPATH=/app/cliniqai:$PYTHONPATH

# Create a non-root user for security (optional but recommended for production)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Start command using uvicorn
CMD ["python", "-m", "uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "8080"]
