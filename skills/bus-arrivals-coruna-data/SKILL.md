---
name: bus-arrivals-coruna-data
description: Consultar llegadas de buses de A Coruna en formato solo datos con llamadas HTTP/HTTPS directas al API de iTranvias (sin MCP ni HTML). Usar cuando el usuario pida (1) llegadas de una parada, (2) llegada de un bus concreto en una parada concreta, o (3) proximas llegadas de una linea en una parada.
---

# Bus Arrivals Coruna Data

## Overview

Resolver consultas de buses llamando directamente al API remoto y parseando JSON.
No usar tools MCP para esta skill.

## API Contract

1. Catalogo de lineas y paradas (mas o menos estatico):
- `https://itranvias.com/queryitr_v3.php?dato=20160101T000000_gl_0_20160101T000000&func=7`
2. Llegadas en tiempo real por parada:
- `https://itranvias.com/queryitr_v3.php?func=0&dato={stop_id}`

En operacion normal:
- Usar solo `func=0` para consultas.
- Resolver nombres de parada y linea con el catalogo local `assets/coruna_catalog.json`.
- No filtrar por lineas de interes: devolver cualquier linea presente.

El catalogo local guarda por linea:
- `commercial_name` (ej. `3`, `3A`).
- `directions` y flags `has_ida` / `has_vuelta`.
- `route_variants` con detalle por recorrido y sentido inferido.

## Scripts

### Consultas
`scripts/query_arrivals.py`
- Consulta una parada concreta.
- Consulta un bus concreto en una parada concreta.
- Consulta una linea concreta en una parada.

### Refresco de catalogo estatico (mantenimiento)
`scripts/refresh_catalog.py`
- Llama a `func=7`.
- Regenera `assets/coruna_catalog.json`.
- Ejecutar solo cuando se quiera actualizar el catalogo local.

## Workflow

1. Identificar tipo de consulta:
- parada completa
- bus concreto en parada
- linea concreta en parada
2. Resolver parada:
- Preferir `--stop-id`.
- Si llega nombre, resolver con catalogo local.
3. Ejecutar `uv run python scripts/query_arrivals.py ...`.
4. Devolver salida JSON parseada en respuesta breve.
5. Si falta catalogo para resolver nombres, pedir `stop_id` o `line_id` o refrescar catalogo.

## Commands (always uv)

### Parada (todas las lineas)
```bash
uv run python skills/bus-arrivals-coruna-data/scripts/query_arrivals.py --stop-id 42 --pretty
```

### Bus concreto en parada
```bash
uv run python skills/bus-arrivals-coruna-data/scripts/query_arrivals.py --stop-id 42 --bus-id 3519 --pretty
```

### Linea concreta en parada
```bash
uv run python skills/bus-arrivals-coruna-data/scripts/query_arrivals.py --stop-id 42 --line-id 3 --pretty
```

### Refrescar catalogo
```bash
uv run python skills/bus-arrivals-coruna-data/scripts/refresh_catalog.py --pretty
```

### Si aparece 403 del API
```bash
uv run python skills/bus-arrivals-coruna-data/scripts/query_arrivals.py --stop-id 42 --request-profile browser --retry-403 4 --pretty
```
El script ya prueba `auto` por defecto (cabeceras normal + navegador y fallback https/http), pero este comando fuerza el perfil mas compatible.

## Output Rules

1. No generar HTML, CSS ni UI.
2. Responder con datos concretos (IDs, ETA, distancia, estado).
3. Mantener coincidencia flexible por nombre cuando exista catalogo.
4. Si el bus o linea no aparece en la parada, devolver `ok: false` con `message`.
5. Para evitar llamadas extra, no consultar `func=7` durante consultas normales.
