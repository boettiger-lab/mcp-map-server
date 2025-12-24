# MCP Map Server Usage Examples

These examples show how an LLM (via MCP client like Claude Desktop) would use the map server tools.

## Example 1: Show Protected Areas in India

**User:** "Show me protected areas in India"

**LLM tool calls:**

```json
// First, add the WDPA layer if not already present
{
  "tool": "add_layer",
  "arguments": {
    "id": "wdpa",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://minio.carlboettiger.info/public-pmtiles/wdpa_global.pmtiles"
    },
    "layers": [{
      "id": "wdpa-fill",
      "type": "fill",
      "source": "wdpa",
      "source-layer": "default",
      "paint": {
        "fill-color": "#4CAF50",
        "fill-opacity": 0.5
      }
    }]
  }
}

// Filter to India (ISO3 = "IND")
{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa-fill",
    "filter": ["==", "ISO3", "IND"]
  }
}

// Set map view to India
{
  "tool": "set_map_view",
  "arguments": {
    "center": [78.9629, 20.5937],
    "zoom": 5
  }
}
```

**LLM response:** "I've displayed protected areas in India on the map. The map now shows all WDPA protected areas filtered to India (ISO3: IND) and is centered on the country."

---

## Example 2: Color Protected Areas by IUCN Category

**User:** "Color the protected areas by their IUCN category"

**LLM tool calls:**

```json
{
  "tool": "set_layer_paint",
  "arguments": {
    "layer_id": "wdpa-fill",
    "property": "fill-color",
    "value": [
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
    ]
  }
}
```

**LLM response:** "I've color-coded the protected areas by IUCN category:
- Ia (Strict Nature Reserve): Red
- Ib (Wilderness Area): Orange
- II (National Park): Green
- III (Natural Monument): Blue
- IV (Habitat Management): Purple
- V (Protected Landscape): Brown
- VI (Sustainable Use): Pink
- Other: Gray"

---

## Example 3: Show Strict Protection Areas Only

**User:** "Show me only the strictest protected areas (IUCN Ia and Ib)"

**LLM tool calls:**

```json
{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa-fill",
    "filter": ["in", "IUCN_CAT", "Ia", "Ib"]
  }
}
```

**LLM response:** "Now showing only the most strictly protected areas (IUCN categories Ia - Strict Nature Reserve and Ib - Wilderness Area)."

---

## Example 4: Add Carbon Layer and Show Overlap

**User:** "Show me where vulnerable carbon overlaps with protected areas"

**LLM tool calls:**

```json
// Add carbon layer
{
  "tool": "add_layer",
  "arguments": {
    "id": "carbon",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://minio.carlboettiger.info/public-cog/carbon/vulnerable/{z}/{x}/{y}.png"],
      "tileSize": 256
    },
    "visible": true
  }
}

// Make WDPA semi-transparent to see carbon underneath
{
  "tool": "set_layer_paint",
  "arguments": {
    "layer_id": "wdpa-fill",
    "property": "fill-opacity",
    "value": 0.3
  }
}

// Clear IUCN filter to show all protected areas
{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa-fill",
    "filter": null
  }
}
```

**LLM response:** "I've added the vulnerable carbon layer and made the protected areas semi-transparent so you can see where high carbon areas overlap with protection. Darker areas under the green protected zones indicate carbon-rich ecosystems."

---

## Example 5: Compare State vs Private Protected Areas

**User:** "Show me the difference between state-owned and privately-owned protected areas"

**LLM tool calls:**

```json
// First, show only state-owned and color them green
{
  "tool": "add_layer",
  "arguments": {
    "id": "wdpa-state",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://minio.carlboettiger.info/public-pmtiles/wdpa_global.pmtiles"
    },
    "layers": [{
      "id": "wdpa-state-fill",
      "type": "fill",
      "source": "wdpa-state",
      "source-layer": "default",
      "paint": {
        "fill-color": "#2ca02c",
        "fill-opacity": 0.6
      }
    }]
  }
}

{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa-state-fill",
    "filter": ["==", "OWN_TYPE", "State"]
  }
}

// Add private layer
{
  "tool": "add_layer",
  "arguments": {
    "id": "wdpa-private",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://minio.carlboettiger.info/public-pmtiles/wdpa_global.pmtiles"
    },
    "layers": [{
      "id": "wdpa-private-fill",
      "type": "fill",
      "source": "wdpa-private",
      "source-layer": "default",
      "paint": {
        "fill-color": "#ff7f0e",
        "fill-opacity": 0.6
      }
    }]
  }
}

{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa-private-fill",
    "filter": ["==", "OWN_TYPE", "Private"]
  }
}
```

**LLM response:** "I've created two layers to compare ownership:
- Green areas: State-owned protected areas
- Orange areas: Privately-owned protected areas

You can see the distribution and size differences between public and private conservation efforts."

---

## Example 6: Remove All Layers and Start Fresh

**User:** "Clear the map and start over"

**LLM tool calls:**

```json
// Get current layers
{
  "tool": "list_layers",
  "arguments": {}
}

// Remove each layer (example for 3 layers)
{
  "tool": "remove_layer",
  "arguments": {"id": "wdpa"}
}

{
  "tool": "remove_layer",
  "arguments": {"id": "carbon"}
}

{
  "tool": "remove_layer",
  "arguments": {"id": "wdpa-state"}
}

{
  "tool": "remove_layer",
  "arguments": {"id": "wdpa-private"}
}

// Reset to default view
{
  "tool": "set_map_view",
  "arguments": {
    "center": [-98.5795, 39.8283],
    "zoom": 4
  }
}
```

**LLM response:** "I've cleared all layers from the map and reset the view. The map is now blank and ready for new visualizations."

---

## Example 7: Complex Multi-Layer Analysis

**User:** "Show me Ramsar wetlands in Southeast Asia that overlap with high carbon areas"

**LLM tool calls:**

```json
// Add carbon layer first (as background)
{
  "tool": "add_layer",
  "arguments": {
    "id": "carbon",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://minio.carlboettiger.info/public-cog/carbon/vulnerable/{z}/{x}/{y}.png"],
      "tileSize": 256
    }
  }
}

// Add Ramsar sites
{
  "tool": "add_layer",
  "arguments": {
    "id": "ramsar",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://minio.carlboettiger.info/public-pmtiles/ramsar.pmtiles"
    },
    "layers": [{
      "id": "ramsar-fill",
      "type": "fill",
      "source": "ramsar",
      "source-layer": "default",
      "paint": {
        "fill-color": "#0080ff",
        "fill-opacity": 0.5
      }
    }, {
      "id": "ramsar-outline",
      "type": "line",
      "source": "ramsar",
      "source-layer": "default",
      "paint": {
        "line-color": "#0040ff",
        "line-width": 2
      }
    }]
  }
}

// Filter to Southeast Asia countries
{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "ramsar-fill",
    "filter": ["in", "iso3", "THA", "VNM", "MYS", "IDN", "PHL", "KHM", "LAO", "MMR"]
  }
}

// Set view to Southeast Asia
{
  "tool": "set_map_view",
  "arguments": {
    "center": [105, 10],
    "zoom": 5
  }
}
```

**LLM response:** "I've displayed Ramsar wetland sites in Southeast Asia (Thailand, Vietnam, Malaysia, Indonesia, Philippines, Cambodia, Laos, Myanmar) overlaid on the vulnerable carbon layer. The blue outlined areas are internationally recognized wetlands, and you can see which ones coincide with high carbon storage (darker red/brown tones)."

---

## Key Patterns

1. **Layer Addition**: Always specify complete source and layer specs
2. **Filtering**: Use MapLibre filter expressions (array syntax)
3. **Styling**: Use MapLibre expressions for data-driven visualization
4. **Visibility**: Use `toggle_layer` or `remove_layer` to control what's shown
5. **State Management**: Server persists state, so changes survive client restarts
6. **Composition**: Build complex visualizations by layering multiple sources
