"""Apply manual data restrictions and annotations to extracted records."""

import csv
from pathlib import Path

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

    def apply_rules_to_disease(self, disease: dict) -> dict:
        """Apply all rules to a disease. First find relevant rules, then call the
        apply method.

        :param disease: disease object from ETL base
        :return: processed disease object
        """
        relevant_rules = self.rules.get(disease["concept_id"], [])
        for rule in relevant_rules:
            disease = self._apply_rule_to_field(disease, rule[0], rule[1])
        return disease

    def _apply_rule_to_field(
        self, disease: dict, field: str, value: str | list | dict | int | float
    ) -> dict:
        """Given a (field, value) rule, apply it to the given disease object.

        :param disease: disease object ready to load to DB
        :param field: name of object property field to check
        :param value: value to remove from field, if possible
        :return: disease object with rule applied
        """
        if field not in {"aliases", "xrefs", "associated_with"}:
            msg = "Non-scalar fields currently not implemented"
            raise ValueError(msg)
        field_data = set(disease.get(field, []))
        if value in field_data:
            field_data.remove(value)
            disease[field] = list(field_data)
        return disease
