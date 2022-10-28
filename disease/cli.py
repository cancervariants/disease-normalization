"""This module provides a CLI util to make updates to normalizer database."""
from timeit import default_timer as timer
from os import environ

import click
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from disease import SOURCES_LOWER_LOOKUP, logger
from disease.schemas import SourceName
from disease.database import Database, confirm_aws_db_use, SKIP_AWS_DB_ENV_NAME, \
    VALID_AWS_ENV_NAMES, AWS_ENV_VAR_NAME
from disease.etl.merge import Merge
from disease.etl.mondo import Mondo
from disease.etl import NCIt  # noqa: F401
from disease.etl import DO  # noqa: F401
from disease.etl import OncoTree  # noqa: F401
from disease.etl import OMIM  # noqa: F401


# Use to lookup class object from source name. Should be one key-value pair
# for every functioning ETL class.
SOURCES_CLASS_LOOKUP = {s.value.lower(): eval(s.value)
                        for s in SourceName.__members__.values()}


class CLI:
    """Class for updating the normalizer database via Click"""

    @staticmethod
    @click.command()
    @click.option(
        '--normalizer',
        help="The source(s) you wish to update separated by spaces."
    )
    @click.option(
        '--aws_instance',
        help=" Must be `Dev`, `Staging`, or `Prod`. This determines the AWS instance to"
             " use. `Dev` uses nonprod. `Staging` and `Prod` uses prod."
    )
    @click.option(
        '--db_url',
        help="URL endpoint for the application database."
    )
    @click.option(
        '--update_all',
        is_flag=True,
        help='Update all normalizer sources.'
    )
    @click.option(
        '--update_merged',
        is_flag=True,
        help='Update concepts for normalize endpoint. Must select either '
             '--update_all or include Mondo as a normalizer source argument.'
    )
    def update_normalizer_db(normalizer, aws_instance, db_url, update_all,
                             update_merged):
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
            elif 'DISEASE_NORM_DB_URL' in environ.keys():
                endpoint_url = environ['DISEASE_NORM_DB_URL']
            else:
                endpoint_url = 'http://localhost:8000'
            db: Database = Database(db_url=endpoint_url)

        if update_all:
            normalizers = list(src for src in SOURCES_CLASS_LOOKUP)
            CLI()._update_normalizers(normalizers, db, update_merged)
        elif not normalizer:
            CLI()._help_msg("Must provide 1 or more source names, or use `--update_all` parameter")  # noqa: E501
        else:
            normalizers = normalizer.lower().split()

            if len(normalizers) == 0:
                CLI()._help_msg("Must provide 1 or more source names, or use `--update_all` parameter")  # noqa: E501

            non_sources = set(normalizers) - {src for src
                                              in SOURCES_LOWER_LOOKUP}

            if len(non_sources) != 0:
                raise Exception(f"Not valid source(s): {non_sources}. \n"
                                f"Legal sources are "
                                f"{list(SOURCES_LOWER_LOOKUP.values())}.")

            if update_merged and 'mondo' not in normalizers:
                CLI()._help_msg("Must include Mondo in sources to update for `--update_merged`")  # noqa: E501

            CLI()._update_normalizers(normalizers, db, update_merged)

    @staticmethod
    def _help_msg(message):
        """Display help message."""
        ctx = click.get_current_context()
        click.echo(message)
        click.echo(ctx.get_help())
        ctx.exit()

    @staticmethod
    def _update_normalizers(normalizers, db, update_merged):
        """Update selected normalizer sources."""
        processed_ids = []
        for n in normalizers:
            msg = f"Deleting {n}..."
            click.echo(f"\n{msg}")
            logger.info(msg)
            start_delete = timer()
            CLI()._delete_data(n, db)
            end_delete = timer()
            delete_time = end_delete - start_delete
            msg = f"Deleted {n} in {delete_time:.5f} seconds."
            click.echo(f"{msg}\n")
            logger.info(msg)

            msg = f"Loading {n}..."
            click.echo(msg)
            logger.info(msg)
            start_load = timer()
            source = SOURCES_CLASS_LOOKUP[n](database=db)
            if isinstance(source, Mondo):
                processed_ids = source.perform_etl()
            else:
                source.perform_etl()
            end_load = timer()
            load_time = end_load - start_load
            msg = f"Loaded {n} in {load_time:.5f} seconds."
            click.echo(msg)
            logger.info(msg)
            msg = f"Total time for {n}: " \
                  f"{(delete_time + load_time):.5f} seconds."
            click.echo(msg)
            logger.info(msg)
        if update_merged and processed_ids:
            click.echo("Generating merged concepts...")
            merge = Merge(database=db)
            merge.create_merged_concepts(processed_ids)
            click.echo("Merged concept generation complete.")

    @staticmethod
    def _delete_data(source, database):
        # Delete source's metadata
        try:
            metadata = database.metadata.query(
                KeyConditionExpression=Key(
                    'src_name').eq(SourceName[f"{source.upper()}"].value)
            )
            if metadata['Items']:
                database.metadata.delete_item(
                    Key={'src_name': metadata['Items'][0]['src_name']},
                    ConditionExpression="src_name = :src",
                    ExpressionAttributeValues={
                        ':src': SourceName[f"{source.upper()}"].value}
                )
        except ClientError as e:
            click.echo(e.response['Error']['Message'])

        # Delete source's data from diseases table
        try:
            while True:
                response = database.diseases.query(
                    IndexName='src_index',
                    KeyConditionExpression=Key('src_name').eq(
                        SourceName[f"{source.upper()}"].value)
                )

                records = response['Items']
                if not records:
                    break

                with database.diseases.batch_writer(
                        overwrite_by_pkeys=['label_and_type', 'concept_id']) \
                        as batch:

                    for record in records:
                        batch.delete_item(
                            Key={
                                'label_and_type': record['label_and_type'],
                                'concept_id': record['concept_id']
                            }
                        )
        except ClientError as e:
            click.echo(e.response['Error']['Message'])


if __name__ == '__main__':
    CLI().update_normalizer_db()
