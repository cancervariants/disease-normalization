# Disease Normalizer

Services and guidelines for normalizing disease terms

## Installation

The Disease Normalizer is available via PyPI:

```commandline

pip install disease-normalizer[etl,pg]
```

The [etl,pg] argument tells pip to install packages to fulfill the dependencies of the gene.etl package and the PostgreSQL data storage implementation alongside the default DynamoDB data storage implementation.

### External requirements

The Disease Normalizer can retrieve most required data itself, using the [wags-tails](https://github.com/GenomicMedLab/wags-tails) library. The exception is disease terms from OMIM, for which a source file must be manually acquired and placed in the `omim` folder within the data directory (by default, `~/.local/share/wags_tails/omim/`). In order to access OMIM data, users must submit a request [here](https://www.omim.org/downloads). Once approved, the relevant OMIM file (`mimTitles.txt`) should be renamed according to the convention `omim_YYYYMMDD.tsv`, where `YYYYMMDD` indicates the date that the file was generated, and placed in the appropriate location.

### Database Initialization

The Disease Normalizer supports two data storage options:

* [DynamoDB](https://aws.amazon.com/dynamodb), a NoSQL service provided by AWS. This is our preferred storage solution. In addition to cloud deployment, Amazon also provides a tool for local service, which can be installed [here](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html). Once downloaded, you can start service by running `java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb` in a terminal (add a `-port <VALUE>` option to use a different port). By default, data will be added to a table named `disease_normalizer`, but an alternate table name can by given under the environment variable `DISEASE_DYNAMO_TABLE`.
* [PostgreSQL](https://www.postgresql.org/), a well-known relational database technology. Once starting the Postgres server process, [ensure that a database is created](https://www.postgresql.org/docs/current/sql-createdatabase.html) (we typically name ours `disease_normalizer`).

By default, the Disease Normalizer expects to find a DynamoDB instance listening at `http://localhost:8000`. Alternative locations can be specified in two ways:

The first way is to set the `--db_url` command-line option to the URL endpoint.

```commandline
disease_norm_update --update_all --db_url="http://localhost:8001"
```

The second way is to set the `DISEASE_NORM_DB_URL` environment variable to the URL endpoint.
```commandline
export DISEASE_NORM_DB_URL="http://localhost:8001"
```

To use a PostgreSQL instance instead of DynamoDB, provide a PostgreSQL connection URL instead, e.g.

```commandline
export DISEASE_NORM_DB_URL="postgresql://postgres@localhost:5432/disease_normalizer"
```

### Adding and refreshing data

Use the `disease_norm_update` command in a shell to update the database.

If you encounter an error message like the following, refer to the installation instructions above:

```shell
"Encountered ModuleNotFoundError attempting to import Mondo. Are ETL dependencies installed?"
```

#### Update source(s)

The Disease Normalizer currently uses data from the following sources:

 * The [National Cancer Institute Thesaurus (NCIt)](https://ncithesaurus.nci.nih.gov/ncitbrowser/)
 * The [Mondo Disease Ontology](https://mondo.monarchinitiative.org/)
 * The [Online Mendelian Inheritance in Man (OMIM)](https://www.omim.org/)
 * [OncoTree](http://oncotree.mskcc.org/)
 * The [Disease Ontology](https://disease-ontology.org/)

As described above, all source data other than OMIM can be acquired automatically.

To update one source, simply set `--sources` to the source you wish to update. The normalizer will check to see if local source data is up-to-date, acquire the most recent data if not, and use it to populate the database.

For example, run the following to acquire the latest NCIt data if necessary, and update the NCIt disease records in the normalizer database:

```commandline
disease_norm_update --sources="ncit"
```

To update multiple sources, you can use the `--sources` option with the source names separated by spaces.

#### Update all sources

To update all sources, use the `--update_all` flag:

```commandline
disease_norm_update --update_all
```

### Create Merged Concept Groups
The `normalize` endpoint relies on merged concept groups.

To create merged concept groups, use the `--update_merged` flag with the `--update_all` flag.

```commandline
python3 -m disease.cli --update_all --update_merged
```

### Starting the disease normalization service

Once the Disease Normalizer database has been loaded, from the project root, run the following:

```commandline
uvicorn disease.main:app --reload
```

Next, view the OpenAPI docs on your local machine:

http://127.0.0.1:8000/disease

## Developer instructions
Following are sections include instructions specifically for developers.

### Installation
For a development install, we recommend using Pipenv. See the
[pipenv docs](https://pipenv-fork.readthedocs.io/en/latest/#install-pipenv-today)
for direction on installing pipenv in your compute environment.

To get started, clone the repo and initialize the environment:

```commandline
git clone https://github.com/cancervariants/disease-normalization
cd disease-normalization
pipenv shell
pipenv update
pipenv install --dev
```

Alternatively, install the `pg`, `etl`, `dev`, and test dependency groups in a virtual environment:

```commandline
git clone https://github.com/cancervariants/gene-normalization
cd gene-normalization
python3 -m virtualenv venv
source venv/bin/activate
pip install -e ".[pg,etl,dev,test]"
```

### Init coding style tests

Code style is managed by [Ruff](https://github.com/astral-sh/ruff) and checked prior to commit.

This performs checks for:

* Code style
* File endings
* Added large files
* AWS credentials
* Private keys

Before first commit run:

```commandline
pre-commit install
```

### Running unit tests

Tests are provided via pytest.

```commandline
pytest
```

By default, tests will employ an existing DynamoDB database. For test environments where this is unavailable (e.g. in CI), the `DISEASE_TEST` environment variable can be set to initialize a local DynamoDB instance with miniature versions of input data files before tests are executed.

```comandline
export DISEASE_TEST=true
pytest
```

Sometimes, sources will update their data, and our test fixtures and data will become incorrect. The `tests/scripts/` subdirectory includes scripts to rebuild data files, although most fixtures will need to be updated manually.
