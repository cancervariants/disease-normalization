CREATE MATERIALIZED VIEW record_lookup_view AS
SELECT dc.concept_id,
       dl.label,
       da.aliases,
       das.associated_with,
       dx.xrefs,
       dc.source,
       dc.merge_ref,
       dc.pediatric_disease,
       dc.oncologic_disease,
       lower(dc.concept_id) AS concept_id_lowercase
FROM disease_concepts dc
FULL JOIN (
    SELECT da_1.concept_id, array_agg(da_1.alias) AS aliases
    FROM disease_aliases da_1
    GROUP BY da_1.concept_id
) da ON dc.concept_id::text = da.concept_id::text
FULL JOIN (
    SELECT das_1.concept_id, array_agg(das_1.associated_with) AS associated_with
    FROM disease_associations das_1
    GROUP BY das_1.concept_id
) das ON dc.concept_id::text = das.concept_id::text
FULL JOIN disease_labels dl ON dc.concept_id::text = dl.concept_id::text
FULL JOIN (
    SELECT dx_1.concept_id, array_agg(dx_1.xref) AS xrefs
    FROM disease_xrefs dx_1
    GROUP BY dx_1.concept_id
) dx ON dc.concept_id::text = dx.concept_id::text;
