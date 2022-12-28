"""This module provides a CLI util to make updates to normalizer database."""
from os import environ
from timeit import default_timer as timer
from typing import List, Optional

import click
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from disease import logger
from disease.database import (
    AWS_ENV_VAR_NAME,
    SKIP_AWS_DB_ENV_NAME,
    VALID_AWS_ENV_NAMES,
    Database,
    confirm_aws_db_use,
)
from disease.etl import DO, OMIM, Mondo, NCIt, OncoTree  # noqa: F401
from disease.etl.merge import Merge
from disease.schemas import SourceName

# Use to lookup class object from source name. Should be one key-value pair
# for every functioning ETL class.
SOURCES_CLASS_LOOKUP = {
    s.value.lower(): eval(s.value) for s in SourceName.__members__.values()
}


class CLI:
    """Class for updating the normalizer database via Click"""

    @staticmethod
    @click.command()
    @click.option(
        "--normalizer", help="The source(s) you wish to update separated by spaces."
    )
    @click.option(
        "--aws_instance",
        help=" Must be `Dev`, `Staging`, or `Prod`. This determines the AWS instance to"
        " use. `Dev` uses nonprod. `Staging` and `Prod` uses prod.",
    )
    @click.option("--db_url", help="URL endpoint for the application database.")
    @click.option("--update_all", is_flag=True, help="Update all normalizer sources.")
    @click.option(
        "--update_merged", is_flag=True, help="Update concepts for /normalize endpoint."
    )
    @click.option(
        "--from_local",
        is_flag=True,
        default=False,
        help="Use most recent local source data instead of fetching latest versions.",
    )
    def update_normalizer_db(
        normalizer, aws_instance, db_url, update_all, update_merged, from_local
    ):
        """Update selected source(s) in the Disease Normalizer database."""
        # If SKIP_AWS_CONFIRMATION is accidentally set, we should verify that the
        # aws instance should actually be used
        invalid_aws_msg = f"{AWS_ENV_VAR_NAME} must be set to one of {VALID_AWS_ENV_NAMES}"  # noqa: E501
        aws_env_name = environ.get(AWS_ENV_VAR_NAME) or aws_instance
        if aws_env_name:
            assert aws_env_name in VALID_AWS_ENV_NAMES, invalid_aws_msg
            environ[AWS_ENV_VAR_NAME] = aws_env_name
            confirm_aws_db_use(aws_env_name.upper())
            environ[SKIP_AWS_DB_ENV_NAME] = "true"  # this is already checked above
            db: Database = Database()
        else:
            if db_url:
                endpoint_url = db_url
            elif "DISEASE_NORM_DB_URL" in environ:
                endpoint_url = environ["DISEASE_NORM_DB_URL"]
            else:
                endpoint_url = "http://localhost:8000"
            db = Database(db_url=endpoint_url)

        if update_all:
            sources_to_update = list(src for src in SOURCES_CLASS_LOOKUP)
            CLI()._update_sources(sources_to_update, db, update_merged, from_local)
        elif not normalizer:
            if update_merged:
                CLI()._update_merged(db, [])
            else:
                CLI()._help_msg()
        else:
            sources_to_update = str(normalizer).lower().split()
            if len(sources_to_update) == 0:
                CLI()._help_msg()

            invalid_sources = set(sources_to_update) - {
                src for src in SOURCES_CLASS_LOOKUP
            }
            if len(invalid_sources) != 0:
                raise Exception(f"Not valid sources: {invalid_sources}")

            CLI()._update_sources(sources_to_update, db, update_merged, from_local)

    @staticmethod
    def _help_msg(message: Optional[str] = None):
        """Display help message."""
        ctx = click.get_current_context()
        if message:
            click.echo(message)
        click.echo(ctx.get_help())
        ctx.exit()

    @staticmethod
    def _update_sources(
        sources: List[str], db: Database, update_merged: bool, from_local: bool = False
    ):
        """Update selected normalizer sources."""
        added_ids = []
        for source_name in sources:
            msg = f"Deleting {source_name}..."
            click.echo(f"\n{msg}")
            logger.info(msg)
            start_delete = timer()
            CLI()._delete_data(source_name, db)
            end_delete = timer()
            delete_time = end_delete - start_delete
            msg = f"Deleted {source_name} in {delete_time:.5f} seconds."
            click.echo(f"{msg}\n")
            logger.info(msg)

            msg = f"Loading {source_name}..."
            click.echo(msg)
            logger.info(msg)
            start_load = timer()
            source = SOURCES_CLASS_LOOKUP[source_name](database=db)
            if isinstance(source, Mondo):
                added_ids = source.perform_etl(from_local)
            else:
                source.perform_etl()
            end_load = timer()
            load_time = end_load - start_load
            msg = f"Loaded {source_name} in {load_time:.5f} seconds."
            click.echo(msg)
            logger.info(msg)
            msg = f"Total time for {source_name}: {(delete_time + load_time):.5f} seconds."  # noqa: E501
            click.echo(msg)
            logger.info(msg)
        if update_merged:
            CLI()._update_merged(db, added_ids)

    def _update_merged(self, db: Database, added_ids: List[str]) -> None:
        """Update merged concepts and references.
        :param db: Database client
        :param added_ids: list of concept IDs to use for normalized groups.
            Should consist solely of MONDO IDs. If empty, will be fetched.
        """
        start_merge = timer()
        if not added_ids:
            CLI()._delete_merged_data(db)
            added_ids = db.get_ids_for_merge()
        merge = Merge(database=db)
        click.echo("Constructing normalized records...")
        merge.create_merged_concepts(added_ids)
        end_merge = timer()
        click.echo(
            f"Merged concept generation completed in"
            f" {(end_merge - start_merge):.5f} seconds."
        )

    @staticmethod
    def _delete_merged_data(database: Database):
        """Delete data pertaining to merged records.
        :param database: DynamoDB client
        """
        click.echo("\nDeleting normalized records...")
        start_delete = timer()
        try:
            while True:
                with database.diseases.batch_writer(
                    overwrite_by_pkeys=["label_and_type", "concept_id"]
                ) as batch:
                    response = database.diseases.query(
                        IndexName="type_index",
                        KeyConditionExpression=Key("item_type").eq("merger"),
                    )
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
        except ClientError as e:
            click.echo(e.response["Error"]["Message"])
        end_delete = timer()
        delete_time = end_delete - start_delete
        click.echo(f"Deleted normalized records in {delete_time:.5f} seconds.")

    @staticmethod
    def _delete_data(source: str, database: Database):
        # Delete source's metadata
        try:
            metadata = database.metadata.query(
                KeyConditionExpression=Key("src_name").eq(
                    SourceName[f"{source.upper()}"].value
                )
            )
            if metadata["Items"]:
                database.metadata.delete_item(
                    Key={"src_name": metadata["Items"][0]["src_name"]},
                    ConditionExpression="src_name = :src",
                    ExpressionAttributeValues={
                        ":src": SourceName[f"{source.upper()}"].value
                    },
                )
        except ClientError as e:
            click.echo(e.response["Error"]["Message"])

        # Delete source's data from diseases table
        try:
            while True:
                response = database.diseases.query(
                    IndexName="src_index",
                    KeyConditionExpression=Key("src_name").eq(
                        SourceName[f"{source.upper()}"].value
                    ),
                )

                records = response["Items"]
                if not records:
                    break

                with database.diseases.batch_writer(
                    overwrite_by_pkeys=["label_and_type", "concept_id"]
                ) as batch:

                    for record in records:
                        batch.delete_item(
                            Key={
                                "label_and_type": record["label_and_type"],
                                "concept_id": record["concept_id"],
                            }
                        )
        except ClientError as e:
            click.echo(e.response["Error"]["Message"])


if __name__ == "__main__":
    CLI().update_normalizer_db()
