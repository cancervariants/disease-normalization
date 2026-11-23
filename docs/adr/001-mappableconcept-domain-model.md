# ADR-001 - Use GKM objects instead of bespoke domain models for interface layers

## Status

**Proposed**

## Context

Currently, we use a very old `Disease` class to describe disease records during ingest and retrieval, and in the `GET /search` endpoint:

```python
class Disease(BaseModel):
    """Define disease record."""

    label: StrictStr
    concept_id: StrictStr
    aliases: list[StrictStr] = []
    xrefs: list[StrictStr] = []
    associated_with: list[StrictStr] = []
    pediatric_disease: bool | None = None
    oncologic_disease: bool | None = None
```

This is old and tailored narrowly to our use cases in this library. Since then, we have also adopted the `MappableConcept` (and the more specific `Condition`) as output from our `GET /normalize` endpoint. This class is taken from the GA4GH Genomic Knowledge Models initiative (see here: https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html).

As a result, we are now maintaining two separate descriptions of the same object, performing transformations between them, etc. This is becoming burdensome. It's also quite weird that our two main HTTP endpoints return similar information in a very different structure -- one standard and one non-standard.

## Decision

* Use GKM classes to describe objects at every interface layer -- IE, between ETL modules and the database, between the database and the query class, and as the output of the query class/retrieval HTTP endpoints.
  * Use `Condition` (basically `MappableConcept`) for diseases
  * Use `DataSet` to describe data sources
* Database should store objects as JSON blobs instead of structured key/value pairs or columns. IE, when retrieving an object from the DB, the DB handler method should be able to just unpack it into a `Condition(**data)` and return it to the caller

### Advantages

* Reuse established, interoperable data structure instead of also keeping our own internally. Ensures that what we store internally matches what we can communicate externally.
* Lower maintenance complexity -- don't have to think about data object translation at any layer.
* DB-neutral object structure. It's a little redundant but makes retrieval much simpler, entails less to remember about how postgres stores stuff versus DynamoDB.

### Disadvantages

* Imperfect data match -- `MappableConcept` is a very general data structure that is built for more than just disease representation. This is true, but it's also the ultimate product that we want to be transmitting, so we might as well cut the middleman.
* Schema drift -- if `MappableConcept` undergoes breaking changes, that means a data snapshot would be invalid. I think this is a fair concern but fairly low-likelihood (non-breaking changes are plausible but I have a hard time imagining a plausible breaking change). I think what is more likely is that we want to add more Extension-type data in the future, and that would require a migration in the current paradigm but not under this proposal.

## Consequences

Any production DBs would need to be updated to support the new schema.

Any services using `GET /search` (VarCat does, if I recall correctly) will need to be updated to handle the changed return object structure.
