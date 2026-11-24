# ADR-003 - Simplify concept merging

## Status

**Proposed**

## Context

Currently, we store "source records" and "merged records", consisting of the combination of properties from source records that share a common xref grouping (undirected subgraph of xrefs). Data import consists of loading source records first, then creating merged/aggregated records after all source records are loaded.

* This adds a bunch of time. We effectively have to load data, then download it again, then load it again in a merged fashion.
* This duplicates data. That's kind of scary from a defensive programming perspective (data sync issues?)
* This complicates retrieval. The `GET /normalize` endpoint works by taking a query string, trying to locate a source record that best links to it, then finding the merged version of that source record. I think this unnecessarily exposes DB activity to the caller.

## Decision

Don't merge data in a separate step, but rather, do it on-demand. When a user provides a query, figure out the relevant source record(s) and aggregate the response on-the-fly.


## Consequences
