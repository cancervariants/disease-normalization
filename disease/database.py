"""This module creates the database."""
import boto3
from disease.schemas import NamespacePrefix, SourceName
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from os import environ
from typing import Optional, Dict, List
import logging

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


# should this be located in a shared module
PREFIX_LOOKUP = {v.value: SourceName[k].value
                 for k, v in NamespacePrefix.__members__.items()
                 if k in SourceName.__members__.keys()}


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
                         case_sensitive: bool = True) -> Optional[Dict]:
        """Fetch record corresponding to provided concept ID

        :param str concept_id: concept ID for disease record
        :param bool case_sensitive: if true, performs exact lookup, which is
            more efficient. Otherwise, performs filter operation, which
            doesn't require correct casing.
        :return: complete disease record, if match is found; None otherwise
        """
        try:
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
            logger.error(e.response['Error']['Message'])
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
            logger.error(e.response['Error']['Message'])
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
            logger.error(e.response['Error']['Message'])
            return None
        except KeyError:
            return None

    def add_record(self, record: Dict, record_type: str):
        """Add new record to database.

        :param Dict record: record (of any type) to upload. Must include
            `concept_id` key. If record is of the `identity` type, the
            concept_id must be correctly-cased.
        :param str record_type: one of 'identity', 'label', or 'alias'.
        """
        prefix = record['concept_id'].split(':')[0]
        record['src_name'] = PREFIX_LOOKUP[prefix]
        record['label_and_type'] = f'{record["concept_id"].lower()}##{record_type}'  # noqa: E501
        self.batch.put_item(Item=record)
