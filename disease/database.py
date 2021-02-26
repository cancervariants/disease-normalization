"""This module creates the database."""
from disease import PREFIX_LOOKUP
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import click
import sys
from os import environ
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class Database:
    """The database class."""

    def __init__(self, db_url: str = '', region_name: str = 'us-east-2'):
        """Initialize Database class.

        :param str db_url: database endpoint URL to connect to
        :param str region_name: AWS region name to use
        """
        if db_url:
            boto_params = {
                'region_name': region_name,
                'endpoint_url': db_url
            }
        elif 'DISEASE_NORM_DB_URL' in environ.keys():
            boto_params = {
                'region_name': region_name,
                'endpoint_url': environ['DISEASE_NORM_DB_URL']
            }
        else:
            if 'DISEASE_NORM_PROD' not in environ \
                    or environ['DISEASE_NORM_PROD'] == 'false':
                if click.confirm("Are you sure you want to update "
                                 "the production database?", default=False):
                    click.echo("Updating the production database...")
                else:
                    click.echo("Exiting.")
                    sys.exit()

            boto_params = {
                'region_name': region_name
            }
        self.dynamodb = boto3.resource('dynamodb', **boto_params)
        self.dynamodb_client = boto3.client('dynamodb', **boto_params)

        # create tables if nonexistant if not connecting to remote database
        if db_url or 'DISEASE_NORM_DB_URL' in environ.keys():
            existing_tables = self.dynamodb_client.list_tables()['TableNames']
            self.create_diseases_table(existing_tables)
            self.create_meta_data_table(existing_tables)

        self.diseases = self.dynamodb.Table('disease_concepts')
        self.metadata = self.dynamodb.Table('disease_metadata')
        self.batch = self.diseases.batch_writer()
        self.cached_sources = {}

    def create_diseases_table(self, existing_tables: List):
        """Create Diseases table if it doesn't already exist.

        :param List existing_tables: list of existing table names
        """
        table_name = 'disease_concepts'
        if table_name not in existing_tables:
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'label_and_type',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'concept_id',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'label_and_type',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'concept_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'src_name',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'item_type',
                        'AttributeType': 'S'
                    }

                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'src_index',
                        'KeySchema': [
                            {
                                'AttributeName': 'src_name',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'KEYS_ONLY'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 10,
                            'WriteCapacityUnits': 10
                        }
                    },
                    {
                        'IndexName': 'type_index',
                        'KeySchema': [
                            {
                                'AttributeName': 'item_type',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'KEYS_ONLY'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 10,
                            'WriteCapacityUnits': 10
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )

    def create_meta_data_table(self, existing_tables: List):
        """Create MetaData table if not exists.

        :param List existing_tables: list of existing table names
        """
        table_name = 'disease_metadata'
        if table_name not in existing_tables:
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'src_name',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'src_name',
                        'AttributeType': 'S'
                    },
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )

    def get_record_by_id(self, concept_id: str,
                         case_sensitive: bool = True,
                         merge: bool = False) -> Optional[Dict]:
        """Fetch record corresponding to provided concept ID

        :param str concept_id: concept ID for disease record
        :param bool case_sensitive: if true, performs exact lookup, which is
            more efficient. Otherwise, performs filter operation, which
            doesn't require correct casing.
        :return: complete disease record, if match is found; None otherwise
        """
        try:
            if merge:
                pk = f'{concept_id.lower()}##merger'
            else:
                pk = f'{concept_id.lower()}##identity'
            if case_sensitive:
                match = self.diseases.get_item(Key={
                    'label_and_type': pk,
                    'concept_id': concept_id
                })
                return match['Item']
            else:
                exp = Key('label_and_type').eq(pk)
                response = self.diseases.query(KeyConditionExpression=exp)
                return response['Items'][0]
        except ClientError as e:
            logger.error(f"boto3 client error on get_records_by_id for "
                         f"search term {concept_id}: "
                         f"{e.response['Error']['Message']}")
            return None
        except KeyError:  # record doesn't exist
            return None
        except IndexError:  # record doesn't exist
            return None

    def get_records_by_type(self, query: str,
                            match_type: str) -> List[Dict]:
        """Retrieve records for given query and match type.

        :param query: string to match against
        :param str match_type: type of match to look for. Should be one
            of "label" or "alias" (use `get_record_by_id` for concept ID
            lookup)
        :return: list of matching records. Empty if lookup fails.
        """
        pk = f'{query}##{match_type.lower()}'
        filter_exp = Key('label_and_type').eq(pk)
        try:
            matches = self.diseases.query(KeyConditionExpression=filter_exp)
            return matches.get('Items', None)
        except ClientError as e:
            logger.error(f"boto3 client error on get_records_by_type for "
                         f"search term {query}: "
                         f"{e.response['Error']['Message']}")
            return []

    def get_merged_record(self, merge_ref) -> Optional[Dict]:
        """Fetch merged record from given reference.
        :param str merge_ref: key for merged record, formated as a string
            of grouped concept IDs separated by vertical bars, ending with
            `##merger`. Must be correctly-cased.
        :return: complete merged record if lookup successful, None otherwise
        """
        try:
            match = self.diseases.get_item(Key={
                'label_and_type': merge_ref.lower(),
                'concept_id': merge_ref
            })
            return match['Item']
        except ClientError as e:
            logger.error("boto3 client error in "
                         "`database.get_merged_record()`: "
                         f"{e.response['Error']['Message']}")
            return None
        except KeyError:
            return None

    def add_record(self, record: Dict, record_type="identity"):
        """Add new record to database.

        :param Dict record: record to upload
        :param str record_type: type of record (either 'identity' or 'merger')
        """
        id_prefix = record['concept_id'].split(':')[0].lower()
        record['src_name'] = PREFIX_LOOKUP[id_prefix]
        label_and_type = f'{record["concept_id"].lower()}##{record_type}'
        record['label_and_type'] = label_and_type
        record['item_type'] = record_type
        try:
            self.batch.put_item(Item=record)
        except ClientError as e:
            logger.error("boto3 client error on add_record for "
                         f"{record['concept_id']}: "
                         f"{e.response['Error']['Message']}")

    def add_ref_record(self, term: str, concept_id: str, ref_type: str):
        """Add auxilliary/reference record to database.

        :param str term: referent term
        :param str concept_id: concept ID to refer to
        :param str ref_type: one of ('alias', 'label')
        """
        label_and_type = f'{term.lower()}##{ref_type}'
        src_name = PREFIX_LOOKUP[concept_id.split(':')[0].lower()]
        record = {
            'label_and_type': label_and_type,
            'concept_id': concept_id.lower(),
            'src_name': src_name,
            'item_type': ref_type,
        }
        try:
            self.batch.put_item(Item=record)
        except ClientError as e:
            logger.error(f"boto3 client error adding reference {term} for "
                         f"{concept_id} with match type {ref_type}: "
                         f"{e.response['Error']['Message']}")

    def update_record(self, concept_id: str, field: str, new_value: Any):
        """Update the field of an individual record to a new value.

        :param str concept_id: record to update
        :param str field: name of field to update
        :parm str new_value: new value
        """
        key = {
            'label_and_type': f'{concept_id.lower()}##identity',
            'concept_id': concept_id
        }
        update_expression = f"set {field}=:r"
        update_values = {':r': new_value}
        try:
            self.diseases.update_item(Key=key,
                                      UpdateExpression=update_expression,
                                      ExpressionAttributeValues=update_values)
        except ClientError as e:
            logger.error(f"boto3 client error in `database.update_record()`: "
                         f"{e.response['Error']['Message']}")

    def flush_batch(self):
        """Flush internal batch_writer."""
        self.batch.__exit__(*sys.exc_info())
        self.batch = self.diseases.batch_writer()
