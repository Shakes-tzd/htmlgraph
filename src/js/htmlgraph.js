/**
 * HtmlGraph - "HTML is All You Need"
 *
 * A lightweight graph database framework using HTML files as nodes,
 * hyperlinks as edges, and CSS selectors as the query language.
 *
 * @version 0.6.1
 */

/**
 * Edge reference for the edge index
 */
class EdgeRef {
  constructor(sourceId, targetId, relationship) {
    this.sourceId = sourceId;
    this.targetId = targetId;
    this.relationship = relationship;
  }
}

/**
 * Bi-directional edge index for O(1) reverse lookups
 */
class EdgeIndex {
  constructor() {
    this._incoming = new Map(); // target -> [EdgeRef]
    this._outgoing = new Map(); // source -> [EdgeRef]
  }

  /**
   * Add an edge to the index
   */
  add(sourceId, targetId, relationship) {
    const ref = new EdgeRef(sourceId, targetId, relationship);

    // Add to incoming index
    if (!this._incoming.has(targetId)) {
      this._incoming.set(targetId, []);
    }
    this._incoming.get(targetId).push(ref);

    // Add to outgoing index
    if (!this._outgoing.has(sourceId)) {
      this._outgoing.set(sourceId, []);
    }
    this._outgoing.get(sourceId).push(ref);
  }

  /**
   * Get incoming edges for a node
   */
  getIncoming(targetId, relationship = null) {
    const edges = this._incoming.get(targetId) || [];
    if (relationship) {
      return edges.filter(e => e.relationship === relationship);
    }
    return edges;
  }

  /**
   * Get outgoing edges for a node
   */
  getOutgoing(sourceId, relationship = null) {
    const edges = this._outgoing.get(sourceId) || [];
    if (relationship) {
      return edges.filter(e => e.relationship === relationship);
    }
    return edges;
  }

  /**
   * Rebuild the index from nodes
   */
  rebuild(nodes) {
    this._incoming.clear();
    this._outgoing.clear();

    for (const node of nodes.values()) {
      for (const [relationship, edges] of Object.entries(node.edges || {})) {
        for (const edge of edges) {
          this.add(node.id, edge.targetId, relationship);
        }
      }
    }
  }
}

/**
 * Query condition operators
 */
const Operator = {
  EQ: 'eq',
  NE: 'ne',
  GT: 'gt',
  GTE: 'gte',
  LT: 'lt',
  LTE: 'lte',
  IN: 'in',
  NOT_IN: 'not_in',
  CONTAINS: 'contains',
  ICONTAINS: 'icontains',
  STARTSWITH: 'startswith',
  ENDSWITH: 'endswith',
  MATCHES: 'matches',
  BETWEEN: 'between',
  ISNULL: 'isnull'
};

/**
 * Query condition
 */
class Condition {
  constructor(attribute, operator, value, negate = false) {
    this.attribute = attribute;
    this.operator = operator;
    this.value = value;
    this.negate = negate;
  }

  /**
   * Check if a node matches this condition
   */
  matches(node) {
    const actualValue = this._getNestedValue(node, this.attribute);
    let result;

    switch (this.operator) {
      case Operator.EQ:
        result = actualValue === this.value;
        break;
      case Operator.NE:
        result = actualValue !== this.value;
        break;
      case Operator.GT:
        result = actualValue > this.value;
        break;
      case Operator.GTE:
        result = actualValue >= this.value;
        break;
      case Operator.LT:
        result = actualValue < this.value;
        break;
      case Operator.LTE:
        result = actualValue <= this.value;
        break;
      case Operator.IN:
        result = Array.isArray(this.value) && this.value.includes(actualValue);
        break;
      case Operator.NOT_IN:
        result = !Array.isArray(this.value) || !this.value.includes(actualValue);
        break;
      case Operator.CONTAINS:
        result = typeof actualValue === 'string' && actualValue.includes(this.value);
        break;
      case Operator.ICONTAINS:
        result = typeof actualValue === 'string' &&
          actualValue.toLowerCase().includes(this.value.toLowerCase());
        break;
      case Operator.STARTSWITH:
        result = typeof actualValue === 'string' && actualValue.startsWith(this.value);
        break;
      case Operator.ENDSWITH:
        result = typeof actualValue === 'string' && actualValue.endsWith(this.value);
        break;
      case Operator.MATCHES:
        result = typeof actualValue === 'string' && new RegExp(this.value).test(actualValue);
        break;
      case Operator.BETWEEN:
        result = actualValue >= this.value[0] && actualValue <= this.value[1];
        break;
      case Operator.ISNULL:
        result = (actualValue === null || actualValue === undefined) === this.value;
        break;
      default:
        result = false;
    }

    return this.negate ? !result : result;
  }

  _getNestedValue(obj, path) {
    const parts = path.split('.');
    let value = obj;
    for (const part of parts) {
      if (value === null || value === undefined) return undefined;
      value = value[part];
    }
    return value;
  }
}

/**
 * Condition builder for fluent API
 */
class ConditionBuilder {
  constructor(queryBuilder, attribute, negate = false) {
    this._queryBuilder = queryBuilder;
    this._attribute = attribute;
    this._negate = negate;
  }

  eq(value) {
    return this._addCondition(Operator.EQ, value);
  }

  ne(value) {
    return this._addCondition(Operator.NE, value);
  }

  gt(value) {
    return this._addCondition(Operator.GT, value);
  }

  gte(value) {
    return this._addCondition(Operator.GTE, value);
  }

  lt(value) {
    return this._addCondition(Operator.LT, value);
  }

  lte(value) {
    return this._addCondition(Operator.LTE, value);
  }

  in_(values) {
    return this._addCondition(Operator.IN, values);
  }

  notIn(values) {
    return this._addCondition(Operator.NOT_IN, values);
  }

  contains(value) {
    return this._addCondition(Operator.CONTAINS, value);
  }

  icontains(value) {
    return this._addCondition(Operator.ICONTAINS, value);
  }

  startswith(value) {
    return this._addCondition(Operator.STARTSWITH, value);
  }

  endswith(value) {
    return this._addCondition(Operator.ENDSWITH, value);
  }

  matches(pattern) {
    return this._addCondition(Operator.MATCHES, pattern);
  }

  between(min, max) {
    return this._addCondition(Operator.BETWEEN, [min, max]);
  }

  isnull(value = true) {
    return this._addCondition(Operator.ISNULL, value);
  }

  _addCondition(operator, value) {
    const condition = new Condition(this._attribute, operator, value, this._negate);
    this._queryBuilder._addCondition(condition, 'and');
    return this._queryBuilder;
  }
}

/**
 * Fluent query builder
 */
class QueryBuilder {
  constructor(nodes) {
    this._nodes = nodes;
    this._conditions = [];
    this._logicalOps = [];
  }

  /**
   * Add a where condition
   */
  where(attribute, value = undefined) {
    if (value !== undefined) {
      const condition = new Condition(attribute, Operator.EQ, value);
      this._addCondition(condition, 'and');
      return this;
    }
    return new ConditionBuilder(this, attribute);
  }

  /**
   * Add an AND condition
   */
  and_(attribute, value = undefined) {
    if (value !== undefined) {
      const condition = new Condition(attribute, Operator.EQ, value);
      this._addCondition(condition, 'and');
      return this;
    }
    return new ConditionBuilder(this, attribute);
  }

  /**
   * Add an OR condition
   */
  or_(attribute, value = undefined) {
    if (value !== undefined) {
      const condition = new Condition(attribute, Operator.EQ, value);
      this._addCondition(condition, 'or');
      return this;
    }
    const builder = new ConditionBuilder(this, attribute);
    builder._logicalOp = 'or';
    return builder;
  }

  /**
   * Add a NOT condition
   */
  not_(attribute) {
    return new ConditionBuilder(this, attribute, true);
  }

  /**
   * Filter by node type
   */
  ofType(nodeType) {
    return this.where('type', nodeType);
  }

  _addCondition(condition, logicalOp) {
    this._conditions.push(condition);
    this._logicalOps.push(logicalOp);
  }

  /**
   * Execute the query and return matching nodes
   */
  execute() {
    const results = [];

    for (const node of this._nodes.values()) {
      if (this._matchesAllConditions(node)) {
        results.push(node);
      }
    }

    return results;
  }

  /**
   * Get the first matching node
   */
  first() {
    for (const node of this._nodes.values()) {
      if (this._matchesAllConditions(node)) {
        return node;
      }
    }
    return null;
  }

  /**
   * Get count of matching nodes
   */
  count() {
    return this.execute().length;
  }

  _matchesAllConditions(node) {
    if (this._conditions.length === 0) return true;

    let result = this._conditions[0].matches(node);

    for (let i = 1; i < this._conditions.length; i++) {
      const conditionResult = this._conditions[i].matches(node);
      const logicalOp = this._logicalOps[i];

      if (logicalOp === 'or') {
        result = result || conditionResult;
      } else {
        result = result && conditionResult;
      }
    }

    return result;
  }
}

/**
 * Find API with Django-style lookup suffixes
 */
class FindAPI {
  constructor(nodes, edgeIndex) {
    this._nodes = nodes;
    this._edgeIndex = edgeIndex;
  }

  /**
   * Find first matching node
   */
  find(type = null, filters = {}) {
    for (const node of this._nodes.values()) {
      if (this._matchesFilters(node, type, filters)) {
        return node;
      }
    }
    return null;
  }

  /**
   * Find all matching nodes
   */
  findAll(type = null, limit = null, filters = {}) {
    const results = [];

    for (const node of this._nodes.values()) {
      if (this._matchesFilters(node, type, filters)) {
        results.push(node);
        if (limit && results.length >= limit) break;
      }
    }

    return results;
  }

  /**
   * Find related nodes
   */
  findRelated(nodeId, relationship = null, direction = 'outgoing') {
    const results = [];

    if (direction === 'outgoing') {
      const edges = this._edgeIndex.getOutgoing(nodeId, relationship);
      for (const edge of edges) {
        const node = this._nodes.get(edge.targetId);
        if (node) results.push(node);
      }
    } else {
      const edges = this._edgeIndex.getIncoming(nodeId, relationship);
      for (const edge of edges) {
        const node = this._nodes.get(edge.sourceId);
        if (node) results.push(node);
      }
    }

    return results;
  }

  /**
   * Find nodes that this node blocks
   */
  findBlocking(nodeId) {
    return this.findRelated(nodeId, 'blocked_by', 'incoming');
  }

  /**
   * Find nodes that block this node
   */
  findBlockedBy(nodeId) {
    return this.findRelated(nodeId, 'blocked_by', 'outgoing');
  }

  _matchesFilters(node, type, filters) {
    // Check type
    if (type && node.type !== type) return false;

    // Check filters with lookup suffixes
    for (const [key, value] of Object.entries(filters)) {
      if (!this._checkFilter(node, key, value)) return false;
    }

    return true;
  }

  _checkFilter(node, key, value) {
    // Parse lookup suffix
    const lookupSuffixes = [
      '__contains', '__icontains', '__startswith', '__endswith',
      '__regex', '__gt', '__gte', '__lt', '__lte',
      '__in', '__not_in', '__isnull'
    ];

    let attribute = key;
    let operator = Operator.EQ;

    for (const suffix of lookupSuffixes) {
      if (key.endsWith(suffix)) {
        attribute = key.slice(0, -suffix.length);
        operator = suffix.slice(2); // Remove __
        break;
      }
    }

    // Convert attribute path (double underscore to dot for nested access)
    attribute = attribute.replace(/__/g, '.');

    const condition = new Condition(attribute, operator, value);
    return condition.matches(node);
  }
}

/**
 * Main HtmlGraph class
 */
class HtmlGraph {
  constructor() {
    this._nodes = new Map();
    this._edgeIndex = new EdgeIndex();
    this._findAPI = new FindAPI(this._nodes, this._edgeIndex);
  }

  /**
   * Load nodes from an array
   */
  load(nodes) {
    for (const node of nodes) {
      this._nodes.set(node.id, node);
    }
    this._edgeIndex.rebuild(this._nodes);
  }

  /**
   * Add a node
   */
  add(node) {
    this._nodes.set(node.id, node);
    // Update edge index for this node's edges
    for (const [relationship, edges] of Object.entries(node.edges || {})) {
      for (const edge of edges) {
        this._edgeIndex.add(node.id, edge.targetId, relationship);
      }
    }
  }

  /**
   * Get a node by ID
   */
  get(nodeId) {
    return this._nodes.get(nodeId) || null;
  }

  /**
   * Update a node
   */
  update(node) {
    this._nodes.set(node.id, node);
    this._edgeIndex.rebuild(this._nodes);
  }

  /**
   * Remove a node
   */
  remove(nodeId) {
    this._nodes.delete(nodeId);
    this._edgeIndex.rebuild(this._nodes);
  }

  /**
   * Get all nodes
   */
  nodes() {
    return this._nodes.values();
  }

  /**
   * CSS selector query (requires DOM context)
   */
  query(selector) {
    // In browser context, this would query the DOM
    // For node.js, this would need a DOM parser
    console.warn('CSS selector queries require DOM context');
    return [];
  }

  /**
   * Create a query builder
   */
  queryBuilder() {
    return new QueryBuilder(this._nodes);
  }

  /**
   * Find first matching node
   */
  find(type = null, filters = {}) {
    return this._findAPI.find(type, filters);
  }

  /**
   * Find all matching nodes
   */
  findAll(type = null, limit = null, filters = {}) {
    return this._findAPI.findAll(type, limit, filters);
  }

  /**
   * Find related nodes
   */
  findRelated(nodeId, relationship = null, direction = 'outgoing') {
    return this._findAPI.findRelated(nodeId, relationship, direction);
  }

  /**
   * Find nodes that this node blocks
   */
  findBlocking(nodeId) {
    return this._findAPI.findBlocking(nodeId);
  }

  /**
   * Find nodes that block this node
   */
  findBlockedBy(nodeId) {
    return this._findAPI.findBlockedBy(nodeId);
  }

  // Edge Index methods

  /**
   * Get incoming edges for a node
   */
  getIncomingEdges(nodeId, relationship = null) {
    return this._edgeIndex.getIncoming(nodeId, relationship);
  }

  /**
   * Get outgoing edges for a node
   */
  getOutgoingEdges(nodeId, relationship = null) {
    return this._edgeIndex.getOutgoing(nodeId, relationship);
  }

  /**
   * Get all neighbors of a node
   */
  getNeighbors(nodeId) {
    const neighbors = new Set();
    for (const edge of this._edgeIndex.getIncoming(nodeId)) {
      neighbors.add(edge.sourceId);
    }
    for (const edge of this._edgeIndex.getOutgoing(nodeId)) {
      neighbors.add(edge.targetId);
    }
    return Array.from(neighbors);
  }

  // Graph Traversal methods

  /**
   * Get all ancestors of a node
   */
  ancestors(nodeId, relationship = 'blocked_by', maxDepth = null) {
    if (!this._nodes.has(nodeId)) return [];

    const ancestors = [];
    const visited = new Set([nodeId]);
    const queue = [[nodeId, 0]];

    while (queue.length > 0) {
      const [current, depth] = queue.shift();

      if (maxDepth !== null && depth >= maxDepth) continue;

      const node = this._nodes.get(current);
      if (!node) continue;

      const edges = node.edges?.[relationship] || [];
      for (const edge of edges) {
        if (!visited.has(edge.targetId)) {
          visited.add(edge.targetId);
          ancestors.push(edge.targetId);
          if (this._nodes.has(edge.targetId)) {
            queue.push([edge.targetId, depth + 1]);
          }
        }
      }
    }

    return ancestors;
  }

  /**
   * Get all descendants of a node
   */
  descendants(nodeId, relationship = 'blocked_by', maxDepth = null) {
    if (!this._nodes.has(nodeId)) return [];

    const descendants = [];
    const visited = new Set([nodeId]);
    const queue = [[nodeId, 0]];

    while (queue.length > 0) {
      const [current, depth] = queue.shift();

      if (maxDepth !== null && depth >= maxDepth) continue;

      const incoming = this._edgeIndex.getIncoming(current, relationship);
      for (const ref of incoming) {
        if (!visited.has(ref.sourceId)) {
          visited.add(ref.sourceId);
          descendants.push(ref.sourceId);
          queue.push([ref.sourceId, depth + 1]);
        }
      }
    }

    return descendants;
  }

  /**
   * Extract a subgraph with specific nodes
   */
  subgraph(nodeIds, includeEdges = true) {
    const nodeIdSet = new Set(nodeIds);
    const subgraph = new HtmlGraph();

    for (const nodeId of nodeIds) {
      const node = this._nodes.get(nodeId);
      if (!node) continue;

      // Clone node
      const clonedNode = JSON.parse(JSON.stringify(node));

      if (includeEdges) {
        // Filter edges to only include those within the subgraph
        for (const [relationship, edges] of Object.entries(clonedNode.edges || {})) {
          clonedNode.edges[relationship] = edges.filter(e => nodeIdSet.has(e.targetId));
        }
      } else {
        clonedNode.edges = {};
      }

      subgraph.add(clonedNode);
    }

    return subgraph;
  }

  /**
   * Get all nodes in the same connected component
   */
  connectedComponent(nodeId, relationship = null) {
    if (!this._nodes.has(nodeId)) return new Set();

    const component = new Set();
    const queue = [nodeId];

    while (queue.length > 0) {
      const current = queue.shift();
      if (component.has(current)) continue;
      component.add(current);

      // Get outgoing edges
      const outgoing = this._edgeIndex.getOutgoing(current, relationship);
      for (const ref of outgoing) {
        if (!component.has(ref.targetId) && this._nodes.has(ref.targetId)) {
          queue.push(ref.targetId);
        }
      }

      // Get incoming edges
      const incoming = this._edgeIndex.getIncoming(current, relationship);
      for (const ref of incoming) {
        if (!component.has(ref.sourceId) && this._nodes.has(ref.sourceId)) {
          queue.push(ref.sourceId);
        }
      }
    }

    return component;
  }

  /**
   * Find all paths between two nodes
   */
  allPaths(fromId, toId, relationship = null, maxLength = null) {
    if (!this._nodes.has(fromId)) return [];
    if (!this._nodes.has(toId)) return [];

    if (fromId === toId) return [[fromId]];

    const paths = [];
    const stack = [[fromId, [fromId]]];

    while (stack.length > 0) {
      const [current, path] = stack.pop();

      if (maxLength !== null && path.length > maxLength) continue;

      const outgoing = this._edgeIndex.getOutgoing(current, relationship);
      for (const ref of outgoing) {
        if (path.includes(ref.targetId)) continue;

        const newPath = [...path, ref.targetId];

        if (ref.targetId === toId) {
          paths.push(newPath);
        } else if (this._nodes.has(ref.targetId)) {
          stack.push([ref.targetId, newPath]);
        }
      }
    }

    return paths;
  }

  /**
   * Find shortest path between two nodes
   */
  shortestPath(fromId, toId, relationship = null) {
    const paths = this.allPaths(fromId, toId, relationship);
    if (paths.length === 0) return null;
    return paths.reduce((a, b) => a.length <= b.length ? a : b);
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    HtmlGraph,
    QueryBuilder,
    ConditionBuilder,
    Condition,
    Operator,
    EdgeIndex,
    EdgeRef,
    FindAPI
  };
}

if (typeof window !== 'undefined') {
  window.HtmlGraph = HtmlGraph;
  window.QueryBuilder = QueryBuilder;
  window.EdgeIndex = EdgeIndex;
}
