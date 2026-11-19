# RFC: Graph-Based Popularity Metric for Packages

Related to Issue #833

## 1. Motivation

PurlDB aggregates metadata for software packages identified by PURLs (Package URLs).  
However, not all packages have equal importance within an ecosystem.

A structured popularity metric could help:

- Prioritize indexing and mining operations
- Identify critical and widely used packages
- Improve API filtering and ranking
- Focus computational resources on highly connected packages

This RFC proposes a graph-based popularity metric derived from dependency relationships.


## 2. Current Data Model Observations

After setting up PurlDB locally and reviewing `packagedb/models.py`, I observed:

- Dependencies are represented by the `DependentPackage` model.
- Each `DependentPackage` links to a source `Package` via a ForeignKey.
- The dependency target is stored as a PURL string (`purl` field), not as a ForeignKey to another `Package`.

This effectively forms a directed dependency graph:

    Package A  --->  Package B

where B must be resolved from its PURL.


## 3. Proposed Approach

### 3.1 Graph Construction (Initial PoC)

- Nodes: Canonical package identities (ignoring version initially)
- Edges: Dependency relationships
- Direction: A → B if A depends on B

For the initial proof of concept:

- Resolve dependency PURLs to canonical package identities.
- Ignore version to avoid graph fragmentation.
- Restrict computation to a single ecosystem (e.g., PyPI).


## 4. Popularity Signals

### 4.1 Dependency Centrality (Primary Signal)

- In-degree (number of reverse dependencies)
- PageRank-style centrality over the dependency graph

This allows packages depended upon by important packages to receive higher scores.

### 4.2 Possible Enhancements (Future Work)

- Freshness factor (based on `release_date`)
- Mining depth (`mining_level`)
- Optional decay for inactive packages


## 5. Computation Strategy

Two possible strategies:

### Option A: Batch Computation (Recommended)

- Compute popularity periodically via scheduled task
- Store result in database (e.g., `popularity_score` field)
- Expose score via REST API

### Option B: On-Demand Computation

- Compute dynamically during API requests
- Likely too expensive for large graphs

Batch computation appears more scalable.


## 6. Scaling Considerations

- Large ecosystems may contain millions of nodes.
- Version-level graphs may introduce excessive fragmentation.
- Initial implementation should:
  - Operate at package identity level
  - Be ecosystem-scoped
  - Store precomputed scores

Future improvements may include:
- Strongly connected component analysis
- Weighted edges
- Version-aware ranking


## 7. Open Questions

1. Should popularity be computed per ecosystem or globally?
2. Should dependency resolution be materialized in a normalized table?
3. Is ignoring version acceptable for the initial PoC?
4. Should optional dependencies be weighted differently?


## 8. Next Steps

If this direction aligns with project goals:

- Implement a minimal PoC for one ecosystem
- Validate ranking quality
- Iterate on scoring methodology
- Integrate into PurlDB API

Feedback before implementation would be greatly appreciated.