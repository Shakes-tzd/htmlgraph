# JavaScript Test Suite

This directory contains unit tests for the HtmlGraph JavaScript library.

## Running Tests

### Browser-based Tests

Open `test_htmlgraph.html` in a web browser:

```bash
# Using Python's built-in HTTP server
python -m http.server 8000

# Then open: http://localhost:8000/tests/js/test_htmlgraph.html
```

Or using the htmlgraph CLI:

```bash
htmlgraph serve
# Then open: http://localhost:8080/tests/js/test_htmlgraph.html
```

### Test Coverage

The test suite covers:

1. **Basic Node Operations**
   - Adding nodes to the graph
   - Retrieving nodes by ID
   - Node properties

2. **Edge Index**
   - Incoming/outgoing edge tracking
   - Relationship filtering
   - Bi-directional lookups

3. **Query Builder**
   - Fluent query API
   - Condition operators (eq, gt, gte, lt, lte, etc.)
   - Logical operators (AND, OR, NOT)

4. **Find API**
   - Finding nodes by type and filters
   - Django-style lookup suffixes
   - Related node traversal

5. **Graph Traversal**
   - Ancestors/descendants
   - Connected components
   - Subgraph extraction

6. **Shortest Path**
   - Path finding between nodes
   - Relationship-filtered paths

7. **HTML Parsing**
   - DOMParser-based HTML loading
   - Node extraction from HTML
   - Edge extraction
   - Property parsing
   - Step extraction

8. **CSS Selector Queries**
   - Data attribute queries
   - Multiple condition matching

## Test Results

The test suite displays:
- Total number of tests
- Passed/failed counts
- Individual test results with error messages
- Visual indicators (✅ for pass, ❌ for fail)

## Adding New Tests

To add new tests, edit `test_htmlgraph.html` and follow this pattern:

```javascript
runner.section('Your Test Section');

// Simple assertion
runner.assert('Test name', condition, 'Error message');

// Equality assertion
runner.assertEqual('Test name', actualValue, expectedValue);

// Exception testing
runner.assertThrows('Test name', () => {
    // Code that should throw
}, 'Expected error message substring');
```

## Notes

- Tests run entirely in the browser (no Node.js required)
- DOMParser is used for HTML parsing (native browser API)
- Tests are synchronous (async tests require modification)
- The test framework is minimal and self-contained
