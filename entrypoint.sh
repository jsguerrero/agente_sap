#!/bin/bash

# Crear directorio output si no existe
mkdir -p /app/output

# Ejecutar el comando principal
exec "$@" 