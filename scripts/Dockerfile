FROM python:3.9-slim

WORKDIR /app/scripts

# Instalar dependências necessárias
COPY requirements.txt /app/scripts/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o script Python
COPY populate_db.py /app/scripts/

# Definir entrypoint
ENTRYPOINT ["python"]
CMD ["/app/scripts/populate_db.py"]