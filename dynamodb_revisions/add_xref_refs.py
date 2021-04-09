"""Add xref reference to current concepts and update ICD-O namespace."""
import sys
from pathlib import Path
from timeit import default_timer as timer
import click
from boto3.dynamodb.conditions import Attr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(f"{PROJECT_ROOT}")

from disease.database import Database  # noqa: E402


def update_identity_records():
    """Add reference for xref attribute and update ICD-O namespace."""
    db = Database()
    batch = db.diseases.batch_writer()

    last_evaluated_key = None
    while True:
        if last_evaluated_key:
            response = db.diseases.scan(
                FilterExpression=Attr('item_type').eq('identity'),
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = db.diseases.scan(
                FilterExpression=Attr('item_type').eq('identity')
            )
        last_evaluated_key = response.get('LastEvaluatedKey')

        records = response['Items']
        for record in records:
            xrefs = {xref for xref in record.get('xrefs', [])}

            # update icdo prefix
            xrefs_updated = {xref.replace('icd.o', 'icdo')
                             for xref in xrefs}
            if xrefs != xrefs_updated:
                db.update_record(record['concept_id'], 'xrefs',
                                 list(xrefs_updated))

            # add xref lookup
            xrefs_l = {xref.lower() for xref in xrefs_updated}
            for xref in xrefs_l:
                batch.put_item(Item={
                    'label_and_type': f"{xref.lower()}##xref",
                    'concept_id': record['concept_id'].lower(),
                    'src_name': record['src_name']
                })

        if not last_evaluated_key:
            break
    db.flush_batch()


def update_merged_records():
    """Update ICD-O namespace in merged records."""
    db = Database()

    last_evaluated_key = None
    while True:
        if last_evaluated_key:
            response = db.diseases.scan(
                FilterExpression=Attr('item_type').eq('merger'),
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = db.diseases.scan(
                FilterExpression=Attr('item_type').eq('merger')
            )
        last_evaluated_key = response.get('LastEvaluatedKey')

        records = response['Items']
        for record in records:
            xrefs = {xref for xref in record.get('xrefs', [])}

            # update icdo prefix
            xrefs_updated = {xref.replace('icd.o', 'icdo')
                             for xref in xrefs}
            if xrefs != xrefs_updated:
                db.update_record(record['concept_id'], 'xrefs',
                                 list(xrefs_updated), 'merger')

        if not last_evaluated_key:
            break


if __name__ == '__main__':
    click.echo("Adding xref references and updating ICD-O namespace...")
    start = timer()
    update_identity_records()
    update_merged_records()
    end = timer()
    click.echo(f"Finished adding xref references in {end - start:.5f}s.")
