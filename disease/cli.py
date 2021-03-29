"""This module provides a CLI util to make updates to normalizer database."""
import click
from disease import SOURCES_CLASS_LOOKUP, SOURCES_LOWER_LOOKUP
from disease.schemas import SourceName
from disease.database import Database
from disease.etl.mondo import Mondo
from disease.etl.merge import Merge
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from timeit import default_timer as timer
from os import environ


class CLI:
    """Class for updating the normalizer database via Click"""

    @click.command()
    @click.option(
        '--normalizer',
        help="The source(s) you wish to update separated by spaces."
    )
    @click.option(
        '--prod',
        is_flag=True,
        help="Working in production environment."
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
    def update_normalizer_db(normalizer, prod, db_url, update_all,
                             update_merged):
        """Update selected source(s) in the Disease Normalizer database."""
        if prod:
            environ['DISEASE_NORM_PROD'] = "TRUE"
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

    def _help_msg(self, message):
        """Display help message."""
        ctx = click.get_current_context()
        click.echo(message)
        click.echo(ctx.get_help())
        ctx.exit()

    def _update_normalizers(self, normalizers, db, update_merged):
        """Update selected normalizer sources."""
        processed_ids = []
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
            if isinstance(source, Mondo):
                processed_ids = source.perform_etl()
            else:
                source.perform_etl()
            end_load = timer()
            load_time = end_load - start_load
            click.echo(f"Loaded {n} in {load_time:.5f} seconds.")
            click.echo(f"Total time for {n}: "
                       f"{(delete_time + load_time):.5f} seconds.")
        if update_merged and processed_ids:
            click.echo("Generating merged concepts...")
            merge = Merge(database=db)
            merge.create_merged_concepts(processed_ids)
            click.echo("Merged concept generation complete.")

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
