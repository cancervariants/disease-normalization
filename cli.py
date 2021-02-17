"""This module provides a CLI util to make updates to normalizer database."""
import click
from disease import SOURCES_CLASS_LOOKUP, SOURCES
from disease.schemas import SourceName
from disease.database import Database
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from timeit import default_timer as timer


class CLI:
    """Class for updating the normalizer database via Click"""

    @click.command()
    @click.option(
        '--normalizer',
        help="The source(s) you wish to update separated by spaces."
    )
    @click.option(
        '--dev',
        is_flag=True,
        help="Working in development environment on localhost port 8000."
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
    def update_normalizer_db(normalizer, dev, db_url, update_all):
        """Update select normalizer source(s) in the disease database."""
        if dev:
            db: Database = Database(db_url='http://localhost:8000')
        elif db_url:
            db: Database = Database(db_url=db_url)
        else:
            db: Database = Database()

        if update_all:
            normalizers = list(src for src in SOURCES_CLASS_LOOKUP)
            CLI()._update_normalizers(normalizers, db)
        elif not normalizer:
            CLI()._help_msg()
        else:
            normalizers = normalizer.lower().split()

            if len(normalizers) == 0:
                CLI()._help_msg()

            non_sources = set(normalizers) - {src for src in SOURCES}

            if len(non_sources) != 0:
                raise Exception(f"Not valid source(s): {non_sources}")

            CLI()._update_normalizers(normalizers, db)

    def _help_msg(self):
        """Display help message."""
        ctx = click.get_current_context()
        click.echo(
            "Must either enter 1 or more sources, or use `--update_all` parameter")  # noqa: E501
        click.echo(ctx.get_help())
        ctx.exit()

    def _update_normalizers(self, normalizers, db):
        """Update selected normalizer sources."""
        for n in normalizers:
            click.echo(f"\nDeleting {n}...")
            start_delete = timer()
            CLI()._delete_data(n, db)
            end_delete = timer()
            delete_time = end_delete - start_delete
            click.echo(f"Deleted {n} in "
                       f"{delete_time:.5f} seconds.\n")
            click.echo(f"Loading {n}...")
            start_load = timer()
            source = SOURCES_CLASS_LOOKUP[n](database=db)
            source.perform_etl()
            end_load = timer()
            load_time = end_load - start_load
            click.echo(f"Loaded {n} in {load_time:.5f} seconds.")
            click.echo(f"Total time for {n}: "
                       f"{(delete_time + load_time):.5f} seconds.")

    def _delete_data(self, source, database):
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
