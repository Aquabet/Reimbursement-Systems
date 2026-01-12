FROM python:3.10-slim-buster

WORKDIR /app

COPY pyproject.toml .
RUN pip install poetry && poetry install --no-root --no-dev

COPY . .

# Set the FLASK_APP environment variable
ENV FLASK_APP=run.py

# Expose the port the app runs on
EXPOSE 5000

# Run the app
CMD ["flask", "run", "--host=0.0.0.0"]
