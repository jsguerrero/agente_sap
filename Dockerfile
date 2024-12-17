FROM python:3.9-slim

WORKDIR /app

# Copiar archivos de configuración primero
COPY requirements.txt .
COPY entrypoint.sh /entrypoint.sh

# Establecer permisos del entrypoint
RUN chmod +x /entrypoint.sh

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear usuario no root y establecer permisos
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

# Cambiar al usuario no privilegiado
USER appuser

# Usar el entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py"]