FROM public.ecr.aws/docker/library/python:3.12.10-slim-bookworm

# Set up a non-root user
RUN adduser -uid 1001 nonroot

# Set the working directory
WORKDIR /workspaces_app

# Copy only the files needed to install dependencies
COPY pyproject.toml poetry.lock ./

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-root

# Copy the rest of the application code
COPY workspaces_app ./workspaces_app

# Switch to non-root user
USER nonroot

# Run the application
CMD ["python", "./workspaces_app/main.py"]
