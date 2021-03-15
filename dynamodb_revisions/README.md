# DynamoDB Revisions
Files in this directory are used to make updates to the `disease_concepts` and/or `disease_metadata` tables in DynamoDB.

## add_omim_other_ids.py

Covers some miscellaneous DB schematic updates:

* Altering merged record concept ID and reference patterns
* Adding OMIM as an `other_identifier` rather than an `xref`
