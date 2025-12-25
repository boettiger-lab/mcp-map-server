# MCP Map Server Usage Examples

These examples show how an LLM (via MCP client like Claude Desktop) would use the map server tools. Each example shows the natural language user request followed by the tool calls that accomplish the task.

The server includes comprehensive information about available data layers, so no additional configuration is needed for these examples to work.

---

## Example 1: Simple Base Map

**User:** "Show me a basic world map"

**LLM response:** "I'll create a basic world map using OpenStreetMap tiles."

**Tool calls:**
```json
{
  "tool": "add_layer",
  "arguments": {
    "id": "osm-base",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      "attribution": "© OpenStreetMap contributors"
    }
  }
}
```

---

## Example 2: Protected Areas in a Country

**User:** "Show me protected areas in Brazil"

**LLM response:** "I'll create a map showing protected areas in Brazil using the World Database on Protected Areas."

**Tool calls:**
```json
{
  "tool": "add_layer",
  "arguments": {
    "id": "osm-base",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      "attribution": "© OpenStreetMap contributors"
    }
  }
}

{
  "tool": "add_layer",
  "arguments": {
    "id": "wdpa",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://s3-west.nrp-nautilus.io/public-wdpa/WDPA_Dec2025.pmtiles"
    },
    "layers": [{
      "id": "wdpa-fill",
      "type": "fill",
      "source": "wdpa",
      "source-layer": "wdpa",
      "paint": {
        "fill-color": "#228B22",
        "fill-opacity": 0.6
      }
    }, {
      "id": "wdpa-outline",
      "type": "line",
      "source": "wdpa",
      "source-layer": "wdpa",
      "paint": {
        "line-color": "#006400",
        "line-width": 1
      }
    }]
  }
}

{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa",
    "filter": ["==", ["get", "ISO3"], "BRA"]
  }
}

{
  "tool": "set_map_view",
  "arguments": {
    "center": [-55.0, -10.0],
    "zoom": 4
  }
}
```

---

## Example 3: Color Protected Areas by IUCN Category

**User:** "Show protected areas in the US and color them by their conservation category"

**LLM response:** "I'll display US protected areas with color coding by IUCN management category - strict reserves in red, national parks in green, etc."

**Tool calls:**
```json
{
  "tool": "add_layer",
  "arguments": {
    "id": "carto-base",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"],
      "attribution": "© OpenStreetMap contributors © CARTO"
    }
  }
}

{
  "tool": "add_layer",
  "arguments": {
    "id": "wdpa",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://s3-west.nrp-nautilus.io/public-wdpa/WDPA_Dec2025.pmtiles"
    },
    "layers": [{
      "id": "wdpa-fill",
      "type": "fill",
      "source": "wdpa",
      "source-layer": "wdpa",
      "paint": {
        "fill-color": [
          "match",
          ["get", "IUCN_CAT"],
          "Ia", "#d62728",
          "Ib", "#ff7f0e", 
          "II", "#2ca02c",
          "III", "#1f77b4",
          "IV", "#9467bd",
          "V", "#8c564b",
          "VI", "#e377c2",
          "#999999"
        ],
        "fill-opacity": 0.7
      }
    }]
  }
}

{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa",
    "filter": ["==", ["get", "ISO3"], "USA"]
  }
}

{
  "tool": "set_map_view",
  "arguments": {
    "center": [-98.5, 39.8],
    "zoom": 4
  }
}
```

---

## Example 4: Administrative Boundaries with Satellite Base

**User:** "Show me US state boundaries over satellite imagery"

**LLM response:** "I'll display US state boundaries over high-resolution satellite imagery using Overture Maps administrative data."

**Tool calls:**
```json
{
  "tool": "add_layer",
  "arguments": {
    "id": "satellite-base",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      "attribution": "Tiles © Esri"
    }
  }
}

{
  "tool": "add_layer",
  "arguments": {
    "id": "states",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://overturemaps.azureedge.net/release/2024-11-13.0/theme=admins.pmtiles"
    },
    "layers": [{
      "id": "states-outline",
      "type": "line",
      "source": "states",
      "source-layer": "admins",
      "paint": {
        "line-color": "#FFD700",
        "line-width": 2,
        "line-opacity": 0.8
      }
    }]
  }
}

{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "states",
    "filter": [
      "all",
      ["==", ["get", "admin_level"], 4],
      ["==", ["get", "iso_country_code_alpha_2"], "US"]
    ]
  }
}

{
  "tool": "set_map_view",
  "arguments": {
    "center": [-98.5, 39.8],
    "zoom": 4
  }
}
```

---

## Available Tools Summary

- **add_layer**: Add raster (tiles) or vector (PMTiles) data sources
- **remove_layer**: Remove layers by ID
- **set_map_view**: Set center coordinates and zoom level  
- **filter_layer**: Apply attribute-based filters to vector layers
- **set_layer_paint**: Modify colors, opacity, and other visual properties
- **list_layers**: List all active layers
- **get_map_config**: Get current map state as JSON

## Common Patterns

- Always start with a base layer (OSM, CartoDB, Esri)
- Use light base maps when overlaying data
- Filter large datasets by geography first (ISO3, admin_level)
- Apply meaningful colors and legends for data visualization
- Use appropriate zoom levels for the data scale
