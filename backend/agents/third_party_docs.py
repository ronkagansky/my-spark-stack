# TODO: store in db
DOCS = {
    "maps_with_react_leaflet": """
# Maps with React Leaflet

If you need to build a map, use react-leaflet.

## React Usage
1. $ npm install react-leaflet leaflet --force
2. `import { MapContainer, TileLayer, useMap } from 'react-leaflet'` (you do not need css imports)
""".strip(),
    "placeholder_images": """
# Placeholder Images

If you need placeholder images, use sparkstack.app's mock image API.

## Usage
Base URL: https://sparkstack.app/api/mocks/images

### Optional Query Parameters
- orientation=landscape - Set image orientation
- query=topic - Filter images by topic/category

### Example
`https://sparkstack.app/api/mocks/images?orientation=landscape&query=nature`

The API will redirect to a random image matching your criteria.
""".strip(),
}
