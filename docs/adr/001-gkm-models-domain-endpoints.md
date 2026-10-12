# 001 - Use GKM models for domain modeling and HTTP endpoints

**Status**: proposed

**Context**: currently, we employ GKM models only for the eventual result of the `/normalize` endpoint; otherwise, we have bespoke data structures describing disease concepts, sources, etc for internal data exchange, storage in the DB, and as the output of our `/search` endpoints. However, we increasingly 

**Decision**: tear out all non-GKM models doing the work of either endpoint schema or domain model definitions (eg during ETL -> database loading, and when passing data from the DB out to a query response). Diseases should be a `MappableConcept`. Source metadata should be a `DataSet`. Schema versions underlying the data should also be available as part of the `GET /service-info` response, as we've already done in AnyVar.

**Consequences**: 

* This will be a breaking change with existing database snapshots; new deployments will require teardown/recreation of the existing DB.

* Systems that consume the `/search` endpoint will need to be updated slightly; the data is the same, but the structure changes. For the disease normalizer, VarCat could potentially be affected upon final rollout to the prod environment.
