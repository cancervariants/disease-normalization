"""Apply manual data restrictions and annotations to extracted records."""

import csv
from pathlib import Path

from ga4gh.core.models import MappableConcept

from disease.schemas import SourceName


class Rules:
    """Store manually-generated data rules for modifying extracted source data.

    Use to provide consistency in edge cases for computational normalization, and
    correct possible curation errors.

    Initialize within each source's ETL class. This entails a small amount of repeated
    work, and could be revisited if the rules CSV becomes truly large, but makes for
    cleaner code in the meantime.

    Currently used to delete specific parameters from listlike fields, but could be
    expanded to use wildcards (e.g. to prohibit a value from being used in any field)
    or to manually add custom values to a field.
    """

    def __init__(self, source_name: SourceName) -> None:
        """Initialize rules class.
        :param source_name: name of source to use, for filtering unneeded rules
        """
        rules_path = Path(__file__).parent / "rules.csv"
        self.rules: dict[str, list[tuple[str, str]]] = {}
        with rules_path.open() as rules_file:
            reader = csv.DictReader(rules_file, delimiter=",")
            for row in reader:
                if row["source"] == source_name:
                    concept_id = row["concept_id"]
                    if not self.rules.get(concept_id):
                        self.rules[concept_id] = [(row["field"], row["value"])]
                    else:
                        self.rules[concept_id].append((row["field"], row["value"]))

    def apply_rules_to_disease(self, disease: MappableConcept) -> MappableConcept:
        """Apply all rules to a disease. First find relevant rules, then call the
        apply method.

        :param disease: disease object from ETL base
        :return: processed disease object
        """
        relevant_rules = self.rules.get(disease.primaryCoding.code.root, [])
        for rule in relevant_rules:
            self._apply_rule_to_field(disease, rule[0], rule[1])
        return disease

    def _apply_rule_to_field(
        self,
        disease: MappableConcept,
        field: str,
        value: str | list | dict | int | float,
    ) -> None:
        """Given a (field, value) rule, apply it to the given disease object.

        :param disease: disease object ready to load to DB (transformed in place)
        :param field: name of object property field to check
        :param value: value to remove from field, if possible
        """
        if field == "aliases" and disease.aliases and value in disease.aliases:
            disease.aliases.remove(value)
        elif field == "xrefs" and disease.mappings:
            disease.mappings = [
                m
                for m in disease.mappings
                if m.coding.code.root.lower() != value.lower()
            ]
        else:
            msg = "Non-scalar fields currently not implemented"
            raise ValueError(msg)
