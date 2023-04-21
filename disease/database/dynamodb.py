"""Provide DynamoDB client."""
import atexit
import logging
from os import environ
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Union
import boto3
from boto3.dynamodb.conditions import Equals, Key, Attr
from botocore.exceptions import ClientError

import click
from disease import ITEM_TYPES, PREFIX_LOOKUP
from disease.database.database import AWS_ENV_VAR_NAME, SKIP_AWS_DB_ENV_NAME, \
    VALID_AWS_ENV_NAMES, AbstractDatabase, AwsEnvName, DatabaseException, \
    DatabaseReadException, DatabaseWriteException, confirm_aws_db_use
from disease.schemas import RefType, SourceMeta, SourceName

_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)


class DynamoDbDatabase(AbstractDatabase):
    """Database class employing DynamoDB."""

    def __init__(self, db_url: Optional[str] = None, **db_args):
        """Initialize Database class.

        :param str db_url: URL endpoint for DynamoDB source
        :Keyword Arguments:
            * region_name: AWS region (defaults to "us-east-2")
        """
        disease_concepts_table = "disease_concepts"  # default
        disease_metadata_table = "disease_metadata"  # default

        region_name = db_args.get("region_name", "us-east-2")

        if AWS_ENV_VAR_NAME in environ:
            if "DISEASE_TEST" in environ:
                raise DatabaseException(f"Cannot have both DISEASE_TEST and {AWS_ENV_VAR_NAME} set.")  # noqa: E501

            aws_env = environ[AWS_ENV_VAR_NAME]
            if aws_env not in VALID_AWS_ENV_NAMES:
                raise DatabaseException(f"{AWS_ENV_VAR_NAME} must be one of {VALID_AWS_ENV_NAMES}")  # noqa: E501

            skip_confirmation = environ.get(SKIP_AWS_DB_ENV_NAME)
            if (not skip_confirmation) or (skip_confirmation and skip_confirmation != "true"):  # noqa: E501
                confirm_aws_db_use(environ[AWS_ENV_VAR_NAME])

            boto_params = {
                "region_name": region_name
            }

            if aws_env == AwsEnvName.DEVELOPMENT:
                disease_concepts_table = "disease_concepts_nonprod"
                disease_metadata_table = "disease_metadata_nonprod"
        else:
            if db_url:
                endpoint_url = db_url
            elif 'DISEASE_NORM_DB_URL' in environ:
                endpoint_url = environ['DISEASE_NORM_DB_URL']
            else:
                endpoint_url = 'http://localhost:8000'
            click.echo(f"***Using Disease Database Endpoint: {endpoint_url}***")
            boto_params = {
                'region_name': region_name,
                'endpoint_url': endpoint_url
            }

        self.dynamodb = boto3.resource('dynamodb', **boto_params)
        self.dynamodb_client = boto3.client('dynamodb', **boto_params)

        # Only create tables for local instance
        envs_do_not_create_tables = {AWS_ENV_VAR_NAME, "DISEASE_TEST"}
        if not set(envs_do_not_create_tables) & set(environ):
            self.initialize_db()

        self.diseases = self.dynamodb.Table(disease_concepts_table)
        self.metadata = self.dynamodb.Table(disease_metadata_table)
        self.batch = self.diseases.batch_writer()
        self._cached_sources = {}
        atexit.register(self.close_connection)

    def list_tables(self) -> List[str]:
        """Return names of tables in database.

        :return: Table names in DynamoDB
        """
        return self.dynamodb_client.list_tables()['TableNames']

    def drop_db(self) -> None:
        """Delete all tables from database. Requires manual confirmation.

        :raise DatabaseWriteException: if called in a protected setting with
            confirmation silenced.
        """
        try:
            if not self._check_delete_okay():
                return
        except DatabaseWriteException as e:
            raise e

        existing_tables = self.list_tables()
        for table_name in existing_tables:
            self.dynamodb.Table(table_name).delete()

    def _create_diseases_table(self, existing_tables: List[str]):
        """Create Diseases table if non-existent.

        :param List[str] existing_tables: table names already in DB
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
                        'IndexName': 'item_type_index',
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

    def _create_meta_data_table(self, existing_tables: List[str]) -> None:
        """Create MetaData table if non-existent.

        :param List[str] existing_tables: table names already in DB
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

    def initialize_db(self) -> None:
        """Create disease_concepts and disease_metadata tables."""
        existing_tables = self.list_tables()
        self._create_diseases_table(existing_tables)
        self._create_meta_data_table(existing_tables)

    def get_source_metadata(self, src_name: Union[str, SourceName]) -> Optional[Dict]:
        """Get license, versioning, data lookup, etc information for a source.

        :param src_name: name of the source to get data for
        :return: Dict containing metadata if lookup is successful
        """
        if isinstance(src_name, SourceName):
            src_name = src_name.value
        if src_name in self._cached_sources:
            return self._cached_sources[src_name]
        else:
            metadata = self.metadata.get_item(Key={"src_name": src_name}).get("Item")
            self._cached_sources[src_name] = metadata
            return metadata

    def get_record_by_id(self, concept_id: str,
                         case_sensitive: bool = True,
                         merge: bool = False) -> Optional[Dict]:
        """Fetch record corresponding to provided concept ID
        :param str concept_id: concept ID for disease record
        :param bool case_sensitive: if true, performs exact lookup, which is more
        efficient. Otherwise, performs filter operation, which doesn't require correct
        casing.
        :param bool merge: if true, look for merged record; look for identity record
        otherwise.
        :return: complete record, if match is found; None otherwise
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
                record = response['Items'][0]
                del record["label_and_type"]
                return record
        except ClientError as e:
            _logger.error(f"boto3 client error on get_records_by_id for "
                          f"search term {concept_id}: "
                          f"{e.response['Error']['Message']}")
            return None
        except (KeyError, IndexError):  # record doesn't exist
            return None

    def get_refs_by_type(self, search_term: str, ref_type: RefType) -> List[str]:
        """Retrieve concept IDs for records matching the user's query. Other methods
        are responsible for actually retrieving full records.

        :param search_term: string to match against
        :param ref_type: type of match to look for.
        :return: list of associated concept IDs. Empty if lookup fails.
        """
        pk = f"{search_term}##{ref_type.value.lower()}"
        filter_exp = Key("label_and_type").eq(pk)
        try:
            matches = self.diseases.query(KeyConditionExpression=filter_exp)
            return [m["concept_id"] for m in matches.get("Items", None)]
        except ClientError as e:
            _logger.error(f"boto3 client error on get_refs_by_type for "
                          f"search term {search_term}: "
                          f"{e.response['Error']['Message']}")
            return []

    def get_all_concept_ids(self, source: Optional[SourceName] = None) -> Set[str]:
        """Retrieve concept IDs for use in generating normalized records.

        :param source: optionally, just get all IDs for a specific source
        :return: List of concept IDs as strings.
        """
        last_evaluated_key = None
        concept_ids = []
        params: Dict[str, Union[str, Equals]] = {
            "ProjectionExpression": "concept_id",
        }
        if source is not None:
            params["FilterExpression"] = Attr("src_name").eq(source.value)
        while True:
            if last_evaluated_key:
                response = self.diseases.scan(
                    ExclusiveStartKey=last_evaluated_key, **params
                )
            else:
                response = self.diseases.scan(**params)
            records = response['Items']
            for record in records:
                concept_ids.append(record['concept_id'])
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        return set(concept_ids)

    def add_source_metadata(self, src_name: SourceName, metadata: SourceMeta) -> None:
        """Add new source metadata entry.

        :param src_name: name of source
        :param data: known source attributes
        :raise DatabaseWriteException: if write fails
        """
        metadata_item = metadata.dict()
        metadata_item["src_name"] = src_name.value
        try:
            self.metadata.put_item(Item=metadata_item)
        except ClientError as e:
            raise DatabaseWriteException(e)

    def add_record(self, record: Dict, src_name: SourceName) -> None:
        """Add new record to database.

        :param Dict record: record to upload
        :param SourceName src_name: name of source for record
        """
        concept_id = record["concept_id"]
        record["src_name"] = src_name.value
        label_and_type = f"{concept_id.lower()}##identity"
        record["label_and_type"] = label_and_type
        record["item_type"] = "identity"
        try:
            self.batch.put_item(Item=record)
        except ClientError as e:
            _logger.error("boto3 client error on add_record for "
                          f"{concept_id}: {e.response['Error']['Message']}")
        for attr_type, item_type in ITEM_TYPES.items():
            if attr_type in record:
                value = record.get(attr_type)
                if not value:
                    continue
                if isinstance(value, str):
                    items = [value.lower()]
                else:
                    items = {item.lower() for item in value}
                for item in items:
                    self._add_ref_record(
                        item, record["concept_id"], item_type, src_name
                    )

    def add_merged_record(self, record: Dict) -> None:
        """Add merged record to database.

        :param record: merged record to add
        """
        concept_id = record["concept_id"]
        id_prefix = concept_id.split(":")[0].lower()
        record["src_name"] = PREFIX_LOOKUP[id_prefix]
        label_and_type = f"{concept_id.lower()}##merger"
        record["label_and_type"] = label_and_type
        record["item_type"] = "merger"
        try:
            self.batch.put_item(Item=record)
        except ClientError as e:
            _logger.error("boto3 client error on add_record for "
                          f"{concept_id}: {e.response['Error']['Message']}")

    def _add_ref_record(self, term: str, concept_id: str, ref_type: str,
                        src_name: SourceName) -> None:
        """Add auxiliary/reference record to database.

        :param str term: referent term
        :param str concept_id: concept ID to refer to
        :param str ref_type: one of {'alias', 'label', 'xref',
            'associated_with'}
        :param src_name: name of source for record
        """
        label_and_type = f"{term.lower()}##{ref_type}"
        record = {
            "label_and_type": label_and_type,
            "concept_id": concept_id.lower(),
            "src_name": src_name.value,
            "item_type": ref_type,
        }
        try:
            self.batch.put_item(Item=record)
        except ClientError as e:
            _logger.error(f"boto3 client error adding reference {term} for "
                          f"{concept_id} with match type {ref_type}: "
                          f"{e.response['Error']['Message']}")

    def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:
        """Update the merged record reference of an individual record to a new value.

        :param concept_id: record to update
        :param merge_ref: new ref value
        :raise DatabaseWriteException: if attempting to update non-existent record
        """
        label_and_type = f"{concept_id.lower()}##identity"
        key = {
            "label_and_type": label_and_type,
            "concept_id": concept_id
        }
        update_expression = "set merge_ref=:r"
        update_values = {':r': merge_ref.lower()}
        condition_expression = "attribute_exists(label_and_type)"
        try:
            self.diseases.update_item(Key=key,
                                      UpdateExpression=update_expression,
                                      ExpressionAttributeValues=update_values,
                                      ConditionExpression=condition_expression)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                raise DatabaseWriteException(
                    f"No such record exists for keys {label_and_type}, {concept_id}"
                )
            else:
                _logger.error(f"boto3 client error in `database.update_record()`: "
                              f"{e.response['Error']['Message']}")

    def delete_normalized_concepts(self) -> None:
        """Remove merged records from the database. Use when performing a new update
        of normalized data.

        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """
        while True:
            with self.diseases.batch_writer(
                overwrite_by_pkeys=["label_and_type", "concept_id"]
            ) as batch:
                try:
                    response = self.diseases.query(
                        IndexName="item_type_index",
                        KeyConditionExpression=Key("item_type").eq("merger"),
                    )
                except ClientError as e:
                    raise DatabaseReadException(e)
                records = response["Items"]
                if not records:
                    break
                for record in records:
                    batch.delete_item(Key={
                        "label_and_type": record["label_and_type"],
                        "concept_id": record["concept_id"]
                    })

    def delete_source(self, src_name: SourceName) -> None:
        """Delete all data for a source. Use when updating source data.

        :param src_name: name of source to delete
        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """
        while True:
            try:
                response = self.diseases.query(
                    IndexName="src_index",
                    KeyConditionExpression=Key("src_name").eq(
                        src_name.value
                    )
                )
            except ClientError as e:
                raise DatabaseReadException(e)
            records = response["Items"]
            if not records:
                break
            with self.diseases.batch_writer(
                overwrite_by_pkeys=["label_and_type", "concept_id"]
            ) as batch:
                for record in records:
                    try:
                        batch.delete_item(Key={
                            "label_and_type": record["label_and_type"],
                            "concept_id": record["concept_id"]
                        })
                    except ClientError as e:
                        raise DatabaseWriteException(e)

        try:
            self.metadata.delete_item(Key={
                "src_name": src_name.value
            })
        except ClientError as e:
            raise DatabaseWriteException(e)

    def complete_write_transaction(self) -> None:
        """Conclude transaction or batch writing if relevant."""
        _logger.debug("flushing DynamoDB batch writer")
        self.batch.__exit__(*sys.exc_info())
        self.batch = self.diseases.batch_writer()

    def close_connection(self) -> None:
        """Perform any manual connection closure procedures if necessary."""
        self.batch.__exit__(*sys.exc_info())

    def load_from_remote(self, url: Optional[str] = None) -> None:
        """Load DB from remote dump. Not available for DynamoDB database backend.

        :param url: remote location to retrieve gzipped dump file from
        """
        raise NotImplementedError

    def export_db(self, export_location: Path) -> None:
        """Dump DB to specified location. Not available for DynamoDB database backend.

        :param export_location: path to save DB dump at
        """
        raise NotImplementedError