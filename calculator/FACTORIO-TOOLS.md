# Factorio Calculation Tools

This document provides an overview of the tools developed for working with Factorio recipe and production calculations.

## Calculator API Server

A Node.js server that provides API endpoints for calculating production requirements.

### Setup

```bash
npm init -y
npm install express
node factorio-calculator-api.js
```

The server will run on port 3000 by default.

### Available Endpoints

- **GET `/items`**: List all available items
- **POST `/calculate`**: Calculate production requirements
  ```json
  {
    "itemName": "advanced-circuit",
    "rate": 10
  }
  ```
- **POST `/table`**: Generate a tabular representation of recipes
- **POST `/tree`**: Generate a tree representation of the recipe chain

### Format Options

Use the `format` parameter with the `/calculate` endpoint:

```json
{
  "itemName": "advanced-circuit",
  "rate": 10,
  "format": "table"
}
```

Available formats:
- `table`: Structured tables of recipes, items, and raw materials
- `tree`: Hierarchical view of the production chain
- `sankey`: Sankey diagram data for visualizing flows

### Example Curl Request

```bash
curl -X POST http://localhost:3000/calculate \
  -H "Content-Type: application/json" \
  -d '{"itemName": "advanced-circuit", "rate": 10}' | jq
```

## Knowledge Graph Server

A Node.js server that provides interactive visualizations of Factorio's recipe relationships.

### Setup

```bash
npm install express
node factorio-knowledge-graph.js
```

The server will run on port 3001 by default.

### Available Endpoints

- **GET `/items`**: List all available items
- **GET `/item-graph/:itemName`**: Get graph data for a specific item
  - Optional `depth` parameter controls recursion depth (default: 2)
- **GET `/complete-graph`**: Get the entire recipe graph
- **GET `/cytoscape/:itemName`**: Get data in Cytoscape.js format
- **GET `/visualize/:itemName`**: Interactive visual graph browser
- **POST `/multi-item-graph`**: Get a combined graph for multiple items

### Interactive Visualization

The visual graph browser is available at:
```
http://localhost:3001/visualize/advanced-circuit
```

Features:
- Blue nodes represent items
- Red nodes represent recipes
- Green edges represent production relationships
- Red edges represent consumption relationships
- Toggle labels with the "Toggle Labels" button
- Toggle recipe nodes with the "Toggle Recipes" button
- Download graph data with the "Download JSON" button

## Running the Original Calculator

The original Factorio Calculator can be run with:

```bash
python3 -m http.server 8000
```

Then access it at: http://localhost:8000/calc.html