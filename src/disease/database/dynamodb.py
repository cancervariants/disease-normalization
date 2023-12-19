"""Provide DynamoDB client."""
import atexit
import logging
import sys
from os import environ
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Union

import boto3
import click
from boto3.dynamodb.conditions import Attr, Equals, Key
from botocore.exceptions import ClientError

from disease import ITEM_TYPES, PREFIX_LOOKUP
from disease.database.database import (
    AWS_ENV_VAR_NAME,
    SKIP_AWS_DB_ENV_NAME,
    VALID_AWS_ENV_NAMES,
    AbstractDatabase,
    AwsEnvName,
    DatabaseException,
    DatabaseReadException,
    DatabaseWriteException,
    confirm_aws_db_use,
)
from disease.schemas import (
    DataLicenseAttributes,
    RecordType,
    RefType,
    SourceMeta,
    SourceName,
)

_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)


class DynamoDbDatabase(AbstractDatabase):
    """Database class employing DynamoDB."""

    def __init__(self, db_url: Optional[str] = None, **db_args) -> None:
        """Initialize Database class.

        :param str db_url: URL endpoint for DynamoDB source
        :Keyword Arguments:
            * region_name: AWS region (defaults to "us-east-2")
        """
        self.disease_table = environ.get("DISEASE_DYNAMO_TABLE", "disease_normalizer")

        region_name = db_args.get("region_name", "us-east-2")

        if AWS_ENV_VAR_NAME in environ:
            if "DISEASE_TEST" in environ:
                raise DatabaseException(
                    f"Cannot have both DISEASE_TEST and {AWS_ENV_VAR_NAME} set."
                )

            aws_env = environ[AWS_ENV_VAR_NAME]
            if aws_env not in VALID_AWS_ENV_NAMES:
                raise DatabaseException(
                    f"{AWS_ENV_VAR_NAME} must be one of {VALID_AWS_ENV_NAMES}"
                )

            skip_confirmation = environ.get(SKIP_AWS_DB_ENV_NAME)
            if (not skip_confirmation) or (
                skip_confirmation and skip_confirmation != "true"
            ):
                confirm_aws_db_use(environ[AWS_ENV_VAR_NAME])

            boto_params = {"region_name": region_name}

            if aws_env == AwsEnvName.DEVELOPMENT:
                self.disease_table = environ.get(
                    "DISEASE_DYNAMO_TABLE", "disease_normalizer_nonprod"
                )
        else:
            if db_url:
                endpoint_url = db_url
            elif "DISEASE_NORM_DB_URL" in environ:
                endpoint_url = environ["DISEASE_NORM_DB_URL"]
            else:
                endpoint_url = "http://localhost:8000"
            click.echo(f"***Using Disease Database Endpoint: {endpoint_url}***")
            boto_params = {"region_name": region_name, "endpoint_url": endpoint_url}

        self.dynamodb = boto3.resource("dynamodb", **boto_params)
        self.dynamodb_client = boto3.client("dynamodb", **boto_params)

        # Only create tables for local instance
        envs_do_not_create_tables = {AWS_ENV_VAR_NAME, "DISEASE_TEST"}
        if not set(envs_do_not_create_tables) & set(environ):
            self.initialize_db()

        self.diseases = self.dynamodb.Table(self.disease_table)
        self.batch = self.diseases.batch_writer()
        self._cached_sources: Dict[str, SourceMeta] = {}
        atexit.register(self.close_connection)

    def list_tables(self) -> List[str]:
        """Return names of tables in database.

        :return: Table names in DynamoDB
        """
        return self.dynamodb_client.list_tables()["TableNames"]

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
        if self.disease_table in self.list_tables():
            self.dynamodb.Table(self.disease_table).delete()

    def _create_diseases_table(self) -> None:
        """Create Diseases table."""
        self.dynamodb.create_table(
            TableName=self.disease_table,
            KeySchema=[
                {"AttributeName": "label_and_type", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "concept_id", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "label_and_type", "AttributeType": "S"},
                {"AttributeName": "concept_id", "AttributeType": "S"},
                {"AttributeName": "src_name", "AttributeType": "S"},
                {"AttributeName": "item_type", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "src_index",
                    "KeySchema": [{"AttributeName": "src_name", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 10,
                        "WriteCapacityUnits": 10,
                    },
                },
                {
                    "IndexName": "item_type_index",
                    "KeySchema": [{"AttributeName": "item_type", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 10,
                        "WriteCapacityUnits": 10,
                    },
                },
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        )

    def check_schema_initialized(self) -> bool:
        """Check if database schema is properly initialized.

        :return: True if DB appears to be fully initialized, False otherwise
        """
        existing_tables = self.list_tables()
        exists = self.disease_table in existing_tables
        if not exists:
            _logger.info(f"{self.disease_table} is missing or unavailable.")
        return exists

    def check_tables_populated(self) -> bool:
        """Perform rudimentary checks to see if tables are populated.
        Emphasis is on rudimentary -- if some fiendish element has deleted half of the
        disease aliases, this method won't pick it up. It just wants to see if a few
        critical tables have at least a small number of records.

        :return: True if queries successful, false if DB appears empty
        """
        sources = self.diseases.query(
            IndexName="item_type_index",
            KeyConditionExpression=Key("item_type").eq("source"),
        ).get("Items", [])
        if len(sources) < len(SourceName):
            _logger.info("Disease sources table is missing expected sources.")
            return False

        records = self.diseases.query(
            IndexName="item_type_index",
            KeyConditionExpression=Key("item_type").eq(RecordType.IDENTITY.value),
            Limit=1,
        )
        if len(records.get("Items", [])) < 1:
            _logger.info("Disease records index is empty.")
            return False

        normalized_records = self.diseases.query(
            IndexName="item_type_index",
            KeyConditionExpression=Key("item_type").eq(RecordType.MERGER.value),
            Limit=1,
        )
        if len(normalized_records.get("Items", [])) < 1:
            _logger.info("Normalized disease records index is empty.")
            return False

        return True

    def initialize_db(self) -> None:
        """Create disease_normalizer table if needed."""
        if not self.check_schema_initialized():
            self._create_diseases_table()

    def get_source_metadata(
        self, src_name: Union[str, SourceName]
    ) -> Optional[SourceMeta]:
        """Get license, versioning, data lookup, etc information for a source.

        :param src_name: name of the source to get data for
        :return: source metadata, if lookup is successful
        """
        if isinstance(src_name, SourceName):
            src_name = src_name.value
        if src_name in self._cached_sources:
            return self._cached_sources[src_name]
        else:
            pk = f"{src_name.lower()}##source"
            concept_id = f"source:{src_name.lower()}"
            retrieved_metadata = self.diseases.get_item(
                Key={"label_and_type": pk, "concept_id": concept_id}
            ).get("Item")
            if not retrieved_metadata:
                return None
            formatted_metadata = SourceMeta(
                data_license=retrieved_metadata["data_license"],
                data_license_url=retrieved_metadata["data_license_url"],
                version=retrieved_metadata["version"],
                data_url=retrieved_metadata["data_url"],
                rdp_url=retrieved_metadata["rdp_url"],
                data_license_attributes=DataLicenseAttributes(
                    **retrieved_metadata["data_license_attributes"]
                ),
            )
            self._cached_sources[src_name] = formatted_metadata
            return formatted_metadata

    def get_record_by_id(
        self, concept_id: str, case_sensitive: bool = True, merge: bool = False
    ) -> Optional[Dict]:
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
                pk = f"{concept_id.lower()}##{RecordType.MERGER.value}"
            else:
                pk = f"{concept_id.lower()}##{RecordType.IDENTITY.value}"
            if case_sensitive:
                response = self.diseases.get_item(
                    Key={"label_and_type": pk, "concept_id": concept_id}
                )
                record = response.get("Item")
                if not record:
                    return None
            else:
                exp = Key("label_and_type").eq(pk)
                response = self.diseases.query(KeyConditionExpression=exp)
                record = response["Items"][0]
            del record["label_and_type"]
            return record
        except ClientError as e:
            _logger.error(
                f"boto3 client error on get_records_by_id for "
                f"search term {concept_id}: "
                f"{e.response['Error']['Message']}"
            )
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
            _logger.error(
                f"boto3 client error on get_refs_by_type for "
                f"search term {search_term}: "
                f"{e.response['Error']['Message']}"
            )
            return []

    def get_all_concept_ids(self, source: Optional[SourceName] = None) -> Set[str]:
        """Retrieve concept IDs for use in generating normalized records.

        :param source: optionally, just get all IDs for a specific source
        :return: Set of concept IDs as strings.
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
            records = response["Items"]
            for record in records:
                concept_ids.append(record["concept_id"])
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
        return set(concept_ids)

    def get_all_records(self, record_type: RecordType) -> Generator[Dict, None, None]:
        """Retrieve all source or normalized records. Either return all source records,
        or all records that qualify as "normalized" (i.e., merged groups + source
        records that are otherwise ungrouped).
        For example,

        .. code-block::pycon

           >>> from disease.database import create_db
           >>> from disease.schemas import RecordType
           >>> db = create_db()
           >>> for record in db.get_all_records(RecordType.MERGER):
           >>>     pass  # do something

        :param record_type: type of result to return
        :return: Generator that lazily provides records as they are retrieved
        """
        last_evaluated_key = None
        while True:
            if last_evaluated_key:
                response = self.diseases.scan(
                    ExclusiveStartKey=last_evaluated_key,
                )
            else:
                response = self.diseases.scan()
            records = response.get("Items", [])
            for record in records:
                incoming_record_type = record.get("item_type")
                if record_type == RecordType.IDENTITY:
                    if incoming_record_type == record_type:
                        yield record
                else:
                    if (
                        incoming_record_type == RecordType.IDENTITY
                        and not record.get("merge_ref")
                    ) or incoming_record_type == RecordType.MERGER:
                        yield record
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

    def add_source_metadata(self, src_name: SourceName, meta: SourceMeta) -> None:
        """Add new source metadata entry.

        :param src_name: name of source
        :param meta: known source attributes
        :raise DatabaseWriteException: if write fails
        """
        src_name_value = src_name.value
        metadata_item = meta.model_dump()
        metadata_item["src_name"] = src_name_value
        metadata_item["label_and_type"] = f"{str(src_name_value).lower()}##source"
        metadata_item["concept_id"] = f"source:{str(src_name_value).lower()}"
        metadata_item["item_type"] = "source"
        try:
            self.diseases.put_item(Item=metadata_item)
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
            _logger.error(
                "boto3 client error on add_record for "
                f"{concept_id}: {e.response['Error']['Message']}"
            )
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
        label_and_type = f"{concept_id.lower()}##{RecordType.MERGER.value}"
        record["label_and_type"] = label_and_type
        record["item_type"] = RecordType.MERGER.value
        try:
            self.batch.put_item(Item=record)
        except ClientError as e:
            _logger.error(
                "boto3 client error on add_record for "
                f"{concept_id}: {e.response['Error']['Message']}"
            )

    def _add_ref_record(
        self, term: str, concept_id: str, ref_type: str, src_name: SourceName
    ) -> None:
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
            _logger.error(
                f"boto3 client error adding reference {term} for "
                f"{concept_id} with match type {ref_type}: "
                f"{e.response['Error']['Message']}"
            )

    def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
        """Update the merged record reference of an individual record to a new value.

        :param concept_id: record to update
        :param merge_ref: new ref value
        :raise DatabaseWriteException: if attempting to update non-existent record
        """
        label_and_type = f"{concept_id.lower()}##identity"
        key = {"label_and_type": label_and_type, "concept_id": concept_id}
        update_expression = "set merge_ref=:r"
        update_values = {":r": merge_ref.lower()}
        condition_expression = "attribute_exists(label_and_type)"
        try:
            self.diseases.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=update_values,
                ConditionExpression=condition_expression,
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                raise DatabaseWriteException(
                    f"No such record exists for keys {label_and_type}, {concept_id}"
                )
            else:
                _logger.error(
                    f"boto3 client error in `database.update_record()`: "
                    f"{e.response['Error']['Message']}"
                )

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
                        KeyConditionExpression=Key("item_type").eq(
                            RecordType.MERGER.value
                        ),
                    )
                except ClientError as e:
                    raise DatabaseReadException(e)
                records = response["Items"]
                if not records:
                    break
                for record in records:
                    batch.delete_item(
                        Key={
                            "label_and_type": record["label_and_type"],
                            "concept_id": record["concept_id"],
                        }
                    )

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
                    KeyConditionExpression=Key("src_name").eq(src_name.value),
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
                        batch.delete_item(
                            Key={
                                "label_and_type": record["label_and_type"],
                                "concept_id": record["concept_id"],
                            }
                        )
                    except ClientError as e:
                        raise DatabaseWriteException(e)

    def complete_write_transaction(self) -> None:
        """Conclude transaction or batch writing if relevant."""
        self.batch.__exit__(*sys.exc_info())
        self.batch = self.diseases.batch_writer()

    def close_connection(self) -> None:
        """Perform any manual connection closure procedures if necessary."""
        self.batch.__exit__(*sys.exc_info())

    def load_from_remote(self, url: Optional[str] = None) -> None:  # noqa: ANN401
        """Load DB from remote dump. Not available for DynamoDB database backend.

        :param url: remote location to retrieve gzipped dump file from
        """
        raise NotImplementedError

    def export_db(self, export_location: Path) -> None:
        """Dump DB to specified location. Not available for DynamoDB database backend.

        :param export_location: path to save DB dump at
        """
        raise NotImplementedError
