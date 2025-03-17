const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// Load the Factorio data
let factorioData;
try {
  const dataPath = path.join(__dirname, 'data', 'vanilla-1.1.110.json');
  factorioData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
} catch (error) {
  console.error('Error loading Factorio data:', error);
  process.exit(1);
}

// Serve static files
app.use(express.static(__dirname));

// Endpoint to get all available items
app.get('/items', (req, res) => {
  const items = {};
  
  // Get items from recipes
  for (const recipeKey in factorioData.recipes) {
    const recipe = factorioData.recipes[recipeKey];
    if (recipe.results && recipe.results.length > 0) {
      recipe.results.forEach(result => {
        items[result.name] = true;
      });
    }
  }
  
  res.json(Object.keys(items).sort());
});

// Generate the complete knowledge graph
function generateCompleteGraph() {
  const nodes = [];
  const links = [];
  const nodeMap = new Map(); // Maps node ID to index
  
  // Helper function to add a node if it doesn't exist
  function addNode(id, type, name, properties = {}) {
    if (!nodeMap.has(id)) {
      const index = nodes.length;
      nodes.push({
        id,
        type,
        name: name || id,
        ...properties
      });
      nodeMap.set(id, index);
    }
    return nodeMap.get(id);
  }
  
  // Helper function to add a link between nodes
  function addLink(source, target, relationship, properties = {}) {
    const sourceIndex = nodeMap.get(source);
    const targetIndex = nodeMap.get(target);
    
    if (sourceIndex !== undefined && targetIndex !== undefined) {
      links.push({
        source: sourceIndex,
        target: targetIndex,
        relationship,
        ...properties
      });
    }
  }
  
  // Add all recipes
  for (const recipeKey in factorioData.recipes) {
    const recipe = factorioData.recipes[recipeKey];
    const recipeId = `recipe:${recipeKey}`;
    
    // Add recipe node
    addNode(recipeId, 'recipe', recipeKey, {
      category: recipe.category,
      time: recipe.energy_required || 0.5
    });
    
    // Add outputs
    if (recipe.results) {
      recipe.results.forEach(result => {
        const itemId = `item:${result.name}`;
        addNode(itemId, 'item', result.name);
        addLink(recipeId, itemId, 'produces', {
          amount: result.amount || 1
        });
      });
    }
    
    // Add inputs
    if (recipe.ingredients) {
      recipe.ingredients.forEach(ingredient => {
        const itemId = `item:${ingredient.name}`;
        addNode(itemId, 'item', ingredient.name);
        addLink(itemId, recipeId, 'consumedBy', {
          amount: ingredient.amount
        });
      });
    }
  }
  
  return {
    nodes: nodes.map(node => ({
      ...node,
      index: undefined
    })),
    links: links.map(link => ({
      source: nodes[link.source].id,
      target: nodes[link.target].id,
      relationship: link.relationship,
      amount: link.amount
    }))
  };
}

// Generate a subgraph focused on a specific item
function generateItemSubgraph(itemName, maxDepth = 2) {
  const nodes = [];
  const links = [];
  const nodeMap = new Map(); // Maps node ID to index
  
  // Helper function to add a node if it doesn't exist
  function addNode(id, type, name, properties = {}) {
    if (!nodeMap.has(id)) {
      const index = nodes.length;
      nodes.push({
        id, 
        type,
        name: name || id,
        ...properties,
        index
      });
      nodeMap.set(id, index);
    }
    return nodeMap.get(id);
  }
  
  // Helper function to add a link
  function addLink(source, target, relationship, properties = {}) {
    const sourceIndex = nodeMap.get(source);
    const targetIndex = nodeMap.get(target);
    
    if (sourceIndex !== undefined && targetIndex !== undefined) {
      // Check if link already exists
      const exists = links.some(link => 
        link.source === sourceIndex && 
        link.target === targetIndex &&
        link.relationship === relationship
      );
      
      if (!exists) {
        links.push({
          source: sourceIndex,
          target: targetIndex,
          relationship,
          ...properties
        });
      }
    }
  }
  
  // Recursively explore the graph
  function exploreItem(itemName, currentDepth = 0, visited = new Set()) {
    if (currentDepth > maxDepth) return;
    if (visited.has(itemName)) return;
    
    visited.add(itemName);
    const itemId = `item:${itemName}`;
    
    // Try to find item properties in factorioData
    const itemProperties = factorioData.items[itemName] || {};
    
    addNode(itemId, 'item', itemName, {
      group: itemProperties.group,
      subgroup: itemProperties.subgroup
    });
    
    // Find recipes that produce this item
    for (const recipeKey in factorioData.recipes) {
      const recipe = factorioData.recipes[recipeKey];
      
      // Check if recipe produces this item
      if (recipe.results && recipe.results.some(result => result.name === itemName)) {
        const recipeId = `recipe:${recipeKey}`;
        
        addNode(recipeId, 'recipe', recipeKey, {
          category: recipe.category,
          time: recipe.energy_required || 0.5
        });
        
        // Find the amount
        const outputAmount = recipe.results.find(result => result.name === itemName)?.amount || 1;
        
        addLink(recipeId, itemId, 'produces', {
          amount: outputAmount
        });
        
        // Add ingredients
        if (recipe.ingredients) {
          recipe.ingredients.forEach(ingredient => {
            const ingredientId = `item:${ingredient.name}`;
            
            const ingredientProperties = factorioData.items[ingredient.name] || {};
            
            addNode(ingredientId, 'item', ingredient.name, {
              group: ingredientProperties.group,
              subgroup: ingredientProperties.subgroup
            });
            
            addLink(ingredientId, recipeId, 'consumedBy', {
              amount: ingredient.amount
            });
            
            // Recursively explore ingredients
            if (currentDepth < maxDepth) {
              exploreItem(ingredient.name, currentDepth + 1, new Set(visited));
            }
          });
        }
      }
      
      // Check if recipe consumes this item
      if (recipe.ingredients && recipe.ingredients.some(ingredient => ingredient.name === itemName)) {
        const recipeId = `recipe:${recipeKey}`;
        
        addNode(recipeId, 'recipe', recipeKey, {
          category: recipe.category,
          time: recipe.energy_required || 0.5
        });
        
        // Find the amount
        const inputAmount = recipe.ingredients.find(ingredient => ingredient.name === itemName)?.amount || 1;
        
        addLink(itemId, recipeId, 'consumedBy', {
          amount: inputAmount
        });
        
        // Add products
        if (recipe.results) {
          recipe.results.forEach(result => {
            const productId = `item:${result.name}`;
            
            const productProperties = factorioData.items[result.name] || {};
            
            addNode(productId, 'item', result.name, {
              group: productProperties.group,
              subgroup: productProperties.subgroup
            });
            
            addLink(recipeId, productId, 'produces', {
              amount: result.amount || 1
            });
            
            // Recursively explore products
            if (currentDepth < maxDepth) {
              exploreItem(result.name, currentDepth + 1, new Set(visited));
            }
          });
        }
      }
    }
  }
  
  // Start exploration from the target item
  exploreItem(itemName);
  
  return {
    nodes: nodes.map(node => ({
      ...node,
      index: undefined
    })),
    links: links.map(link => ({
      source: nodes[link.source].id,
      target: nodes[link.target].id,
      relationship: link.relationship,
      amount: link.amount || 1
    }))
  };
}

// Endpoint to get the complete knowledge graph
app.get('/complete-graph', (req, res) => {
  try {
    const graph = generateCompleteGraph();
    res.json(graph);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to get a subgraph for a specific item
app.get('/item-graph/:itemName', (req, res) => {
  const { itemName } = req.params;
  const depth = parseInt(req.query.depth || '2');
  
  try {
    const graph = generateItemSubgraph(itemName, depth);
    res.json(graph);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to get a subgraph for multiple related items
app.post('/multi-item-graph', (req, res) => {
  const { items, depth = 1 } = req.body;
  
  if (!items || !Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ error: 'Please provide an array of item names' });
  }
  
  try {
    // Create a combined graph from multiple items
    const nodes = [];
    const links = [];
    const nodeMap = new Map();
    const allNodes = new Set();
    const allLinks = new Set();
    
    // Process each item
    items.forEach(itemName => {
      const subgraph = generateItemSubgraph(itemName, depth);
      
      // Merge nodes
      subgraph.nodes.forEach(node => {
        if (!allNodes.has(node.id)) {
          allNodes.add(node.id);
          nodes.push(node);
          nodeMap.set(node.id, nodes.length - 1);
        }
      });
      
      // Merge links
      subgraph.links.forEach(link => {
        const linkId = `${link.source}|${link.target}|${link.relationship}`;
        if (!allLinks.has(linkId)) {
          allLinks.add(linkId);
          links.push({
            source: link.source,
            target: link.target,
            relationship: link.relationship,
            amount: link.amount
          });
        }
      });
    });
    
    res.json({ nodes, links });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Generate visualization data in Cytoscape.js format
app.get('/cytoscape/:itemName', (req, res) => {
  const { itemName } = req.params;
  const depth = parseInt(req.query.depth || '2');
  
  try {
    const graph = generateItemSubgraph(itemName, depth);
    
    // Convert to Cytoscape.js format
    const elements = {
      nodes: graph.nodes.map(node => ({
        data: {
          id: node.id,
          name: node.name,
          type: node.type,
          ...node
        }
      })),
      edges: graph.links.map((link, index) => ({
        data: {
          id: `e${index}`,
          source: link.source,
          target: link.target,
          relationship: link.relationship,
          amount: link.amount,
          label: `${link.relationship} (${link.amount})`
        }
      }))
    };
    
    res.json(elements);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create a simple HTML visualization
app.get('/visualize/:itemName', (req, res) => {
  const { itemName } = req.params;
  const depth = parseInt(req.query.depth || '2');
  
  try {
    const graph = generateItemSubgraph(itemName, depth);
    
    // Create HTML with embedded data and visualization
    const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Factorio Knowledge Graph - ${itemName}</title>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.21.0/cytoscape.min.js"></script>
      <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
        #cy { width: 100%; height: 85vh; }
        #controls { padding: 10px; background: #f0f0f0; }
      </style>
    </head>
    <body>
      <div id="controls">
        <h3>Factorio Knowledge Graph: ${itemName}</h3>
        <button id="toggleLabels">Toggle Labels</button>
        <button id="toggleRecipes">Toggle Recipes</button>
        <button id="download">Download JSON</button>
      </div>
      <div id="cy"></div>
      <script>
        // Graph data
        const graphData = ${JSON.stringify(graph)};
        
        // Convert to Cytoscape format
        const elements = {
          nodes: graphData.nodes.map(node => ({
            data: {
              id: node.id,
              name: node.name,
              type: node.type,
              ...node
            }
          })),
          edges: graphData.links.map((link, index) => ({
            data: {
              id: 'e' + index,
              source: link.source,
              target: link.target,
              relationship: link.relationship,
              amount: link.amount,
              label: link.relationship + ' (' + link.amount + ')'
            }
          }))
        };

        // Initialize Cytoscape
        const cy = cytoscape({
          container: document.getElementById('cy'),
          elements: elements,
          style: [
            {
              selector: 'node',
              style: {
                'background-color': '#666',
                'label': 'data(name)',
                'text-valign': 'center',
                'text-halign': 'center',
                'color': '#fff',
                'font-size': '12px'
              }
            },
            {
              selector: 'node[type="item"]',
              style: {
                'background-color': '#3498db',
                'shape': 'rectangle',
                'width': '120px',
                'height': '40px',
              }
            },
            {
              selector: 'node[type="recipe"]',
              style: {
                'background-color': '#e74c3c',
                'shape': 'roundrectangle',
                'width': '140px',
                'height': '40px',
              }
            },
            {
              selector: 'edge',
              style: {
                'width': 2,
                'line-color': '#ccc',
                'target-arrow-color': '#ccc',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': 'data(label)',
                'font-size': '10px',
                'text-rotation': 'autorotate'
              }
            },
            {
              selector: 'edge[relationship="produces"]',
              style: {
                'line-color': '#2ecc71',
                'target-arrow-color': '#2ecc71'
              }
            },
            {
              selector: 'edge[relationship="consumedBy"]',
              style: {
                'line-color': '#e74c3c',
                'target-arrow-color': '#e74c3c'
              }
            }
          ],
          layout: {
            name: 'cose',
            idealEdgeLength: 100,
            nodeOverlap: 20,
            refresh: 20,
            fit: true,
            padding: 30,
            randomize: false,
            componentSpacing: 100,
            nodeRepulsion: 400000,
            edgeElasticity: 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0
          }
        });
        
        // Add controls
        document.getElementById('toggleLabels').addEventListener('click', function() {
          const showLabels = cy.style().selector('edge').style('label') === '';
          
          if (showLabels) {
            cy.style()
              .selector('edge')
              .style('label', 'data(label)')
              .update();
          } else {
            cy.style()
              .selector('edge')
              .style('label', '')
              .update();
          }
        });
        
        document.getElementById('toggleRecipes').addEventListener('click', function() {
          const recipesVisible = cy.nodes('[type="recipe"]').visible();
          
          if (recipesVisible) {
            cy.nodes('[type="recipe"]').hide();
            
            // Create direct connections between items
            const items = {};
            
            cy.edges().forEach(edge => {
              const sourceType = cy.getElementById(edge.data('source')).data('type');
              const targetType = cy.getElementById(edge.data('target')).data('type');
              
              if (sourceType === 'recipe' && targetType === 'item') {
                const recipe = edge.data('source');
                const product = edge.data('target');
                
                cy.edges(`[target = "${recipe}"]`).forEach(inEdge => {
                  const ingredient = inEdge.data('source');
                  
                  if (!items[ingredient]) {
                    items[ingredient] = {};
                  }
                  
                  items[ingredient][product] = true;
                });
              }
            });
            
            // Add simplified edges
            for (const ingredient in items) {
              for (const product in items[ingredient]) {
                cy.add({
                  group: 'edges',
                  data: {
                    source: ingredient,
                    target: product,
                    relationship: 'transforms',
                    label: 'transforms'
                  }
                });
              }
            }
          } else {
            cy.nodes('[type="recipe"]').show();
            cy.edges('[relationship = "transforms"]').remove();
          }
          
          cy.layout({
            name: 'cose',
            idealEdgeLength: 100,
            nodeOverlap: 20,
            refresh: 20,
            fit: true,
            padding: 30,
            randomize: false,
            componentSpacing: 100,
            nodeRepulsion: 400000,
            edgeElasticity: 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0
          }).run();
        });
        
        document.getElementById('download').addEventListener('click', function() {
          const data = JSON.stringify(graphData, null, 2);
          const blob = new Blob([data], {type: 'application/json'});
          const url = URL.createObjectURL(blob);
          
          const a = document.createElement('a');
          a.download = 'factorio-graph-${itemName}.json';
          a.href = url;
          a.click();
        });
      </script>
    </body>
    </html>
    `;
    
    res.send(html);
  } catch (error) {
    res.status(500).send(`<html><body><h1>Error</h1><p>${error.message}</p></body></html>`);
  }
});

app.listen(PORT, () => {
  console.log(`Factorio Knowledge Graph API running on port ${PORT}`);
  console.log(`- Access it at http://localhost:${PORT}`);
  console.log(`- Get all items: GET /items`);
  console.log(`- Get complete graph: GET /complete-graph`);
  console.log(`- Get item subgraph: GET /item-graph/advanced-circuit?depth=2`);
  console.log(`- Get cytoscape.js data: GET /cytoscape/advanced-circuit?depth=2`);
  console.log(`- Visual graph browser: GET /visualize/advanced-circuit?depth=2`);
});