---
name: coding_best_practices
description: Best practices for writing production code
category: coding
---

# Coding Best Practices Skill

When writing code:

1. **Always read existing code first** - Use list_files and read_file to understand context
2. **Write tests** - Use run_tests to verify
3. **Handle errors** - Try/except, validation
4. **Document** - Docstrings, comments for complex logic
5. **Security** - No hardcoded secrets, validate inputs
6. **Performance** - Avoid N+1, use efficient algorithms
7. **Git** - Commit with clear messages

Workflow:
- Explore -> Plan -> Code -> Test -> Reflect

Example:
```python
def calculate_total(items: list[dict]) -> float:
    """Calculate total price with tax.
    
    Args:
        items: List of dicts with 'price' and 'quantity'
    
    Returns:
        Total with 10% tax
    """
    if not items:
        return 0.0
    subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
    return round(subtotal * 1.1, 2)
```
