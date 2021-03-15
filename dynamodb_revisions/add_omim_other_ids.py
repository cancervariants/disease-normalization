"""Add v0.2.0 updates to production DynamoDB instance."""
from disease.database import Database
from timeit import default_timer as timer
from disease.etl import Merge


db = Database()
merge = Merge(db)


def update_identities():
    """
    For all records where item_type='identity':
     * Move OMIM refs from xrefs to other_ids
     * Add other_id lookup references
     * update merge_ref field
    """
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = db.dynamodb_client.scan(
                TableName=db.diseases.name,
                ExclusiveStartKey=last_evaluated_key,
                FilterExpression='item_type <> :item_type',
                ExpressionAttributeValues={
                    ':item_type': {'S': 'identity'}
                }
            )
        else:
            response = db.dynamodb_client.scan(
                TableName=db.diseases.name,
                FilterExpression='item_type <> :item_type',
                ExpressionAttributeValues={
                    ':item_type': {'S': 'identity'}
                }
            )
        last_evaluated_key = response.get('LastEvaluatedKey')
        records = response['Items']

        for record in records:
            if record['src_name'] == 'OMIM':
                continue
            concept_id = record['concept_id']

            # move OMIM refs from xrefs to other_ids
            update_ids = False
            other_ids = record.get('other_identifiers', [])
            xrefs = record.get('xrefs', [])
            new_xrefs = xrefs[:]
            for xref in xrefs:
                if xref.startswith('omim'):
                    other_ids.append(xref)
                    new_xrefs.remove(xref)
                    update_ids = True
            if update_ids:
                if new_xrefs:
                    db.update_record(concept_id, 'xrefs', new_xrefs)
                else:
                    key = {
                        'label_and_type': record['label_and_type'],
                        'concept_id': record['concept_id']
                    }
                    db.diseases.update_item(Key=key,
                                            UpdateExpression="REMOVE xrefs")
                db.update_record(concept_id, 'other_identifiers',
                                 other_ids)

            # add other_id lookup
            for other_id in other_ids:
                db.add_ref_record(other_id, concept_id, 'other_id')

            # fix merge ref ID
            merge_ref = record.get('merge_ref')
            if merge_ref and '|' in merge_ref:
                new_merge_ref = merge_ref.split('|')[0]
                db.update_record(new_merge_ref, concept_id, 'merge_ref')


def replace_merged():
    """Delete + replace existing merged records"""
    last_evaluated_key = None
    while True:
        if last_evaluated_key:
            response = db.dynamodb_client.scan(
                TableName=db.diseases.name,
                ExclusiveStartKey=last_evaluated_key,
                FilterExpression='item_type <> :item_type',
                ExpressionAttributeValues={
                    ':item_type': {'S': 'merger'}
                }
            )
        else:
            response = db.dynamodb_client.scan(
                TableName=db.diseases.name,
                FilterExpression='item_type <> :item_type',
                ExpressionAttributeValues={
                    ':item_type': {'S': 'merger'}
                }
            )

        last_evaluated_key = response.get('LastEvaluatedKey')
        records = response['Items']

        for record in records:
            concept_id_old = record['concept_id']
            # delete old record
            db.batch.delete_item(Key={
                'label_and_type': record['label_and_type'],
                'concept_id': concept_id_old
            })

            # update attributes
            regenerate = False
            associated_ids = concept_id_old.split('|')
            main_id = associated_ids[0]
            xrefs = record.get('xrefs', [])
            if xrefs:
                xrefs_new = xrefs[:]
            for xref in xrefs:
                if xref.startswith('omim'):
                    regenerate = True
                    associated_ids.append(xref)
                    xrefs_new.remove(xref)
                    db.update_record(xref, 'merge_ref', main_id)
            if regenerate:
                record, _ = merge._generate_merged_record(associated_ids)
            else:
                record['concept_id'] = main_id
                record['label_and_type'] = f'{main_id.lower()}##merger'
                if len(associated_ids) > 1:
                    record['other_ids'] = associated_ids[1:]

            # upload
            db.batch.put_item(Item=record)

    db.flush_batch()


if __name__ == '__main__':
    # run identity record iteration
    start = timer()
    update_identities()
    end = timer()
    print(f"Completed non-Mondo updates in {end - start:.5f} seconds")

    # generate merged items + add merge refs to omim
    start = timer()
    replace_merged()
    end = timer()
    print(f"Completed non-Mondo updates in {end - start:.5f} seconds")
