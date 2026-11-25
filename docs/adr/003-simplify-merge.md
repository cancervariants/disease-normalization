# ADR-003 - Simplify concept merging

## Status

**Proposed**

## Context

Currently, we store "source records" and "merged records", consisting of the combination of properties from source records that share a common xref grouping (undirected subgraph of xrefs). Data import consists of loading source records first, then creating merged/aggregated records after all source records are loaded.

* This adds a bunch of time. We effectively have to load data, then download it again, then load it again in a merged fashion.
* This duplicates data. That's less ideal from a defensive programming perspective (data sync issues?)
* This generally means that you have to re-run the aggregation step every time you update any individual source. Ideally, I think you should be able to just update a source and that'd be enough.
* This complicates the database API. The `GET /normalize` endpoint works by taking a query string, trying to locate a source record that best links to it, then finding the merged version of that source record. I think this unnecessarily exposes DB internals to the caller.
  * It also means the DB has to return a dict containing stuff like the `merge_ref` that otherwise doesn't appear in the final response object. That's not the end of the world but it makes me feel like the abstraction is leaking, because that property only gets used to fuel another DB request.

## Decision

Don't merge data in a separate step, but rather, do it on-demand. When a user provides a query, figure out the relevant source record(s) and aggregate the response on-the-fly.


## Consequences

### Update storage schema/DB API

Previously, a normalized lookup would go like

1. Resolve reference (eg an alias or xref) to the best-matching record: `get_ref_by_type`. This would return an object that was the raw reference string, and the concept ID for its source record.
  * Either way, I think we should instead get all possible matches for a ref at once, rather than just working by type -- but we can still do better.
2. Resolve reference from that record to its normalized concept: `get_record_by_id` returns a `merge_ref` as part of the object response
3. Get the normalized concept: `get_record_by_id` with a `merge=True` arg, retrieving the object that is constructed as part of the merge/aggregation step in ETL.

Instead, <figuring this out>

* new DB internal architecture -- should a source record also include values for every other concept that it's an exactMatch to? should there just be a separate table with exactMatch mappings? This is sort of a "graph walk" problem but I'm not sure how to minimize the # of queries in a dynamodb context.
* new DB API: just `get_source_record` and `get_normalized_record`? or something like... given a query string, return all of the possible records, their associated records, etc and let the caller sort/combine/filter them?
