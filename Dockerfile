FROM python:3.12-slim

RUN useradd --create-home --uid 1000 skill

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .
RUN chown -R skill:skill /app

USER skill

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
