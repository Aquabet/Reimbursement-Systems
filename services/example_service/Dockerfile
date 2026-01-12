FROM python:3.10-slim-buster

WORKDIR /app

COPY pyproject.toml poetry.lock* ./ # Copy poetry.lock if using poetry

# Install poetry if needed and then project dependencies
RUN pip install poetry && poetry install --no-root --no-dev

COPY . .

CMD ["python", "-m", "example_service.main"]
