const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();
const PORT = process.env.PORT || 3000;

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

// Endpoint to calculate production requirements
app.post('/calculate', (req, res) => {
  const { itemName, rate, format } = req.body;
  
  if (!itemName || !rate) {
    return res.status(400).json({ error: 'Missing itemName or rate' });
  }

  try {
    // Find the recipe for the requested item
    const recipe = findRecipeForItem(itemName);
    if (!recipe) {
      return res.status(404).json({ error: `Recipe for ${itemName} not found` });
    }

    // Calculate the required resources and machines
    const result = calculateRequirements(recipe, rate);
    
    // Format response based on requested format
    if (format === 'sankey') {
      result.sankey = generateSankeyData(recipe, rate);
    } else if (format === 'tree') {
      result.tree = generateRecipeTree(recipe, rate);
    } else if (format === 'table') {
      result.table = generateRecipeTable(recipe, rate);
    }
    
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// New endpoint specifically for Sankey diagram data
app.post('/sankey', (req, res) => {
  const { itemName, rate } = req.body;
  
  if (!itemName || !rate) {
    return res.status(400).json({ error: 'Missing itemName or rate' });
  }

  try {
    // Find the recipe for the requested item
    const recipe = findRecipeForItem(itemName);
    if (!recipe) {
      return res.status(404).json({ error: `Recipe for ${itemName} not found` });
    }

    // Generate Sankey diagram data
    const sankeyData = generateSankeyData(recipe, rate);
    
    res.json(sankeyData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

function findRecipeForItem(itemName) {
  // Find recipe that produces the requested item
  for (const recipeKey in factorioData.recipes) {
    const recipe = factorioData.recipes[recipeKey];
    if (recipe.results && recipe.results.some(result => result.name === itemName)) {
      return {
        key: recipeKey,
        ...recipe
      };
    }
  }
  return null;
}

function calculateRequirements(recipe, targetRate) {
  // Get recipe time and output amount
  const craftingTime = recipe.energy_required || 0.5;
  const outputItem = recipe.results[0].name;
  const outputAmount = recipe.results[0].amount || 1;
  
  // Calculate machines needed (assembling-machine-3 as default)
  const craftingSpeed = 1.25; // Speed of assembling-machine-3
  const machinesNeeded = (targetRate * craftingTime) / (outputAmount * craftingSpeed);
  
  // Calculate ingredient requirements
  const ingredients = recipe.ingredients.map(ingredient => {
    const amountPerSecond = (ingredient.amount * targetRate) / outputAmount;
    
    // Find recipe for this ingredient (for recursion if needed)
    const ingredientRecipe = findRecipeForItem(ingredient.name);
    
    return {
      name: ingredient.name,
      amountPerSecond,
      recipe: ingredientRecipe ? ingredientRecipe.key : null
    };
  });
  
  // Recursive calculation of all requirements (optional for deeper analysis)
  const fullRequirements = {};
  calculateFullRequirements(recipe, targetRate, fullRequirements);
  
  return {
    item: outputItem,
    targetRate,
    machinesNeeded: Math.ceil(machinesNeeded * 100) / 100,
    ingredients,
    craftingTime,
    recipe: recipe.key,
    fullRequirements: Object.entries(fullRequirements)
      .map(([name, rate]) => ({ name, rate: Math.round(rate * 100) / 100 }))
      .sort((a, b) => b.rate - a.rate)
  };
}

function calculateFullRequirements(recipe, targetRate, requirements, seen = new Set()) {
  if (!recipe || !recipe.ingredients) return;
  
  const outputAmount = recipe.results[0].amount || 1;
  const recipeKey = recipe.key;
  
  // Prevent infinite recursion for cyclic recipes
  if (seen.has(recipeKey)) return;
  seen.add(recipeKey);
  
  // Process each ingredient
  recipe.ingredients.forEach(ingredient => {
    const ingredientName = ingredient.name;
    const amountNeeded = (ingredient.amount * targetRate) / outputAmount;
    
    // Add to requirements
    requirements[ingredientName] = (requirements[ingredientName] || 0) + amountNeeded;
    
    // Recursively process this ingredient's recipe
    const ingredientRecipe = findRecipeForItem(ingredientName);
    if (ingredientRecipe) {
      calculateFullRequirements(ingredientRecipe, amountNeeded, requirements, new Set(seen));
    }
  });
}

// Generate Sankey diagram data for visualization
function generateSankeyData(recipe, targetRate, depth = 3) {
  const nodes = [];
  const links = [];
  const nodeMap = new Map(); // Maps node name to index
  
  // Helper function to add a node if it doesn't exist
  function addNode(name, type) {
    if (!nodeMap.has(name)) {
      const index = nodes.length;
      nodes.push({
        name,
        id: index,
        type // 'recipe', 'item', or 'raw'
      });
      nodeMap.set(name, index);
    }
    return nodeMap.get(name);
  }
  
  // Helper function to add a link between nodes
  function addLink(source, target, value) {
    links.push({
      source,
      target,
      value: Math.max(0.01, value) // Ensure non-zero value for visibility
    });
  }
  
  // Recursively build the Sankey diagram data
  function buildSankeyData(recipe, rate, currentDepth = 0, visited = new Set()) {
    if (!recipe || currentDepth > depth) return;
    
    const recipeKey = recipe.key;
    const recipeName = `Recipe: ${recipe.key}`;
    const outputItem = recipe.results[0].name;
    const outputAmount = recipe.results[0].amount || 1;
    
    // Prevent cycles
    if (visited.has(recipeKey)) return;
    visited.add(recipeKey);
    
    // Add recipe node
    const recipeNodeId = addNode(recipeName, 'recipe');
    
    // Add output item node
    const outputNodeId = addNode(outputItem, 'item');
    
    // Add link from recipe to output
    addLink(recipeNodeId, outputNodeId, rate);
    
    // Process each ingredient
    recipe.ingredients.forEach(ingredient => {
      const ingredientName = ingredient.name;
      const ingredientRate = (ingredient.amount * rate) / outputAmount;
      
      // Add ingredient node
      const ingredientNodeId = addNode(ingredientName, 'item');
      
      // Add link from ingredient to recipe
      addLink(ingredientNodeId, recipeNodeId, ingredientRate);
      
      // Recursively process ingredient recipe
      if (currentDepth < depth) {
        const ingredientRecipe = findRecipeForItem(ingredientName);
        if (ingredientRecipe) {
          buildSankeyData(
            ingredientRecipe, 
            ingredientRate, 
            currentDepth + 1, 
            new Set(visited)
          );
        } else {
          // Mark as raw material
          nodes[ingredientNodeId].type = 'raw';
        }
      }
    });
  }
  
  // Start building Sankey data from the target recipe
  buildSankeyData(recipe, targetRate);
  
  return {
    nodes,
    links
  };
}

// Helper function to get item display name
function getItemName(itemKey) {
  // Try to find localized name
  if (factorioData.items[itemKey] && factorioData.items[itemKey].localized_name) {
    return factorioData.items[itemKey].localized_name.en || itemKey;
  }
  return itemKey;
}

// Generate a tree representation of the recipe chain
function generateRecipeTree(recipe, targetRate, depth = 5) {
  if (!recipe) return null;
  
  const outputItem = recipe.results[0].name;
  const outputAmount = recipe.results[0].amount || 1;
  const craftingTime = recipe.energy_required || 0.5;
  
  // Calculate machines needed (assembling-machine-3 as default)
  const craftingSpeed = 1.25; // Speed of assembling-machine-3
  const machinesNeeded = (targetRate * craftingTime) / (outputAmount * craftingSpeed);
  
  const result = {
    item: outputItem,
    recipe: recipe.key,
    rate: targetRate,
    machines: Math.ceil(machinesNeeded * 100) / 100,
    time: craftingTime,
    children: []
  };
  
  // Stop recursion if we've reached max depth
  if (depth <= 0) return result;
  
  // Process each ingredient
  recipe.ingredients.forEach(ingredient => {
    const ingredientName = ingredient.name;
    const ingredientRate = (ingredient.amount * targetRate) / outputAmount;
    
    const childNode = {
      item: ingredientName,
      rate: Math.round(ingredientRate * 100) / 100
    };
    
    // Recursively process this ingredient's recipe
    const ingredientRecipe = findRecipeForItem(ingredientName);
    if (ingredientRecipe) {
      const subTree = generateRecipeTree(ingredientRecipe, ingredientRate, depth - 1);
      if (subTree) {
        Object.assign(childNode, {
          recipe: subTree.recipe,
          machines: subTree.machines,
          time: subTree.time,
          children: subTree.children
        });
      }
    } else {
      // Mark as raw material
      childNode.type = 'raw';
    }
    
    result.children.push(childNode);
  });
  
  return result;
}

// Generate a tabular representation of recipes
function generateRecipeTable(recipe, targetRate) {
  const table = {
    recipes: {},
    items: {},
    rawMaterials: {}
  };
  
  // Helper function to process a recipe and add to table
  function processRecipe(recipe, rate, seen = new Set()) {
    if (!recipe) return;
    
    const recipeKey = recipe.key;
    const outputItem = recipe.results[0].name;
    const outputAmount = recipe.results[0].amount || 1;
    const craftingTime = recipe.energy_required || 0.5;
    
    // Prevent cycles
    if (seen.has(recipeKey)) return;
    seen.add(recipeKey);
    
    // Calculate machines needed
    const craftingSpeed = 1.25; // Speed of assembling-machine-3
    const machinesNeeded = (rate * craftingTime) / (outputAmount * craftingSpeed);
    
    // Add to recipe table
    if (!table.recipes[recipeKey]) {
      table.recipes[recipeKey] = {
        name: recipeKey,
        time: craftingTime,
        machines: Math.ceil(machinesNeeded * 100) / 100,
        outputRate: rate,
        produces: outputItem,
        ingredients: []
      };
    } else {
      // Update existing recipe entry
      table.recipes[recipeKey].machines = Math.ceil((table.recipes[recipeKey].machines + machinesNeeded) * 100) / 100;
      table.recipes[recipeKey].outputRate += rate;
    }
    
    // Add to items table
    if (!table.items[outputItem]) {
      table.items[outputItem] = {
        name: outputItem,
        producedBy: recipeKey,
        producedRate: rate,
        consumedBy: {},
        consumedRate: 0
      };
    } else {
      // Update existing item entry
      table.items[outputItem].producedRate += rate;
    }
    
    // Process each ingredient
    recipe.ingredients.forEach(ingredient => {
      const ingredientName = ingredient.name;
      const ingredientRate = (ingredient.amount * rate) / outputAmount;
      
      // Add to recipe ingredients
      table.recipes[recipeKey].ingredients.push({
        name: ingredientName,
        rate: Math.round(ingredientRate * 100) / 100
      });
      
      // Update item consumption
      if (!table.items[ingredientName]) {
        table.items[ingredientName] = {
          name: ingredientName,
          producedBy: null,
          producedRate: 0,
          consumedBy: {
            [recipeKey]: Math.round(ingredientRate * 100) / 100
          },
          consumedRate: ingredientRate
        };
      } else {
        // Update existing item entry
        table.items[ingredientName].consumedBy[recipeKey] = 
          (table.items[ingredientName].consumedBy[recipeKey] || 0) + 
          Math.round(ingredientRate * 100) / 100;
        table.items[ingredientName].consumedRate += ingredientRate;
      }
      
      // Recursively process this ingredient's recipe
      const ingredientRecipe = findRecipeForItem(ingredientName);
      if (ingredientRecipe) {
        processRecipe(ingredientRecipe, ingredientRate, new Set(seen));
      } else {
        // Add to raw materials
        if (!table.rawMaterials[ingredientName]) {
          table.rawMaterials[ingredientName] = Math.round(ingredientRate * 100) / 100;
        } else {
          table.rawMaterials[ingredientName] += Math.round(ingredientRate * 100) / 100;
        }
      }
    });
  }
  
  // Start processing from the main recipe
  processRecipe(recipe, targetRate);
  
  // Convert objects to arrays for easier consumption
  table.recipes = Object.values(table.recipes);
  table.items = Object.values(table.items);
  table.rawMaterials = Object.entries(table.rawMaterials)
    .map(([name, rate]) => ({ name, rate }))
    .sort((a, b) => b.rate - a.rate);
  
  return table;
}

// New endpoint for tree structure
app.post('/tree', (req, res) => {
  const { itemName, rate } = req.body;
  
  if (!itemName || !rate) {
    return res.status(400).json({ error: 'Missing itemName or rate' });
  }

  try {
    // Find the recipe for the requested item
    const recipe = findRecipeForItem(itemName);
    if (!recipe) {
      return res.status(404).json({ error: `Recipe for ${itemName} not found` });
    }

    // Generate tree data
    const treeData = generateRecipeTree(recipe, rate);
    
    res.json(treeData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// New endpoint for table structure
app.post('/table', (req, res) => {
  const { itemName, rate } = req.body;
  
  if (!itemName || !rate) {
    return res.status(400).json({ error: 'Missing itemName or rate' });
  }

  try {
    // Find the recipe for the requested item
    const recipe = findRecipeForItem(itemName);
    if (!recipe) {
      return res.status(404).json({ error: `Recipe for ${itemName} not found` });
    }

    // Generate table data
    const tableData = generateRecipeTable(recipe, rate);
    
    res.json(tableData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Factorio calculator API running on port ${PORT}`);
  console.log(`- Access it at http://localhost:${PORT}`);
  console.log(`- Get all items: GET /items`);
  console.log(`- Calculate requirements: POST /calculate with {"itemName": "advanced-circuit", "rate": 10}`);
  console.log(`- Formats available: format=table, format=tree, format=sankey`);
  console.log(`- Direct endpoints: /table, /tree, /sankey`);
});