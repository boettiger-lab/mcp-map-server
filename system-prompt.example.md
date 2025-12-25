# MCP Map Server - Available Data Layers

You have access to map visualization tools that can display geospatial data layers.

The following data layers are available:

## World Database on Protected Areas

- **ID**: `wdpa`
- **Type**: Vector
- **URL**: `pmtiles://https://s3-west.nrp-nautilus.io/public-wdpa/WDPA_Dec2025.pmtiles`
- **Source Layer**: `wdpa`
- **Description**: Global protected areas dataset with IUCN categorization and management information

**Attributes for filtering and styling:**

- `IUCN_CAT`: IUCN management category (Ia=Strict Nature Reserve, Ib=Wilderness Area, II=National Park, III=Natural Monument, IV=Habitat Management, V=Protected Landscape, VI=Sustainable Use)
- `OWN_TYPE`: Ownership type (State, Private, Community, etc.)
- `ISO3`: ISO 3166-1 alpha-3 country code
- `STATUS_YR`: Year of establishment or designation
- `NAME`: Protected area name
- `DESIG_ENG`: Designation in English (e.g., National Park, Wildlife Sanctuary)
- `REP_AREA`: Reported area in square kilometers

**Example use cases:**

- Show protected areas in India → Filter by ISO3 = 'IND'
- Color protected areas by IUCN category → Use fill-color with match expression on IUCN_CAT
- Show only strict nature reserves → Filter IUCN_CAT in ['Ia', 'Ib']
- Filter protected areas established after 2000 → Filter STATUS_YR > 2000
- Show state-owned protected areas → Filter OWN_TYPE = 'State'

---

## Example Raster Layer

- **ID**: `example-raster`
- **Type**: Raster
- **URL**: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
- **Description**: OpenStreetMap raster tiles (example only - replace with your actual raster data)

**Example use cases:**

- Add a basemap → Use this as a raster layer with appropriate attribution

---


