# API Contract (iTranvias A Coruna)

## Endpoints

1. Static-ish catalog (stops + lines):
- `GET https://itranvias.com/queryitr_v3.php?dato=20160101T000000_gl_0_20160101T000000&func=7`

2. Live arrivals for one stop:
- `GET https://itranvias.com/queryitr_v3.php?func=0&dato={stop_id}`

## Payload keys used by this skill

### Catalog (`func=7`)
- `iTranvias.actualizacion.paradas[]`
  - `id`
  - `nombre`
  - `posx` / `posy`
  - `enlaces[]` (line IDs linked to stop)
- `iTranvias.actualizacion.lineas[]`
  - `id`
  - `lin_comer`
  - `color`

### Arrivals (`func=0`)
- `buses.lineas[]`
  - `linea`
  - `buses[]`
    - `bus`
    - `tiempo`
    - `distancia`
    - `estado`
    - `ult_parada`

## Runtime strategy

- Keep local static catalog in `assets/coruna_catalog.json`.
- During normal user queries, call only `func=0`.
- Refresh catalog with `func=7` only as maintenance.

## Static catalog fields added by this skill

For each line in `catalog.lines[]`:
- `id`: technical line id (e.g. `300`)
- `commercial_name`: human-facing name (e.g. `3`, `3A`)
- `origin_name` / `destination_name`
- `directions`: detected directions (`ida`, `vuelta`) from routes
- `has_ida` / `has_vuelta`
- `route_variants[]`:
  - `route_id`, `route_index`
  - `direction_code` (if provided by API)
  - `direction` (inferred: `ida`, `vuelta`, `variante`, `cocheras`)
  - `stop_ids`, `stop_count`
