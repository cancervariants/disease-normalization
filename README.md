# Disease Normalization
Services and guidelines for normalizing disease terms

## Developer instructions
Following are sections include instructions specifically for developers.

### Installation
For a development install, we recommend using Pipenv. See the
[pipenv docs](https://pipenv-fork.readthedocs.io/en/latest/#install-pipenv-today)
for direction on installing pipenv in your compute environment.

Once installed, from the project root dir, just run:

```commandline
pipenv sync
```

### Deploying DynamoDB Locally

We use Amazon DynamoDB for our database. To deploy locally, follow [these instructions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html).

### Init coding style tests

Code style is managed by [flake8](https://github.com/PyCQA/flake8) and checked prior to commit.

We use [pre-commit](https://pre-commit.com/#usage) to run conformance tests.

This ensures:

* Check code style
* Check for added large files
* Detect AWS Credentials
* Detect Private Key

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

### Updating the disease normalization database

Before you use the CLI to update the database, run the following in a separate terminal to start DynamoDB on `port 8000`:

```
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb
```

To change the port, simply add `-port value`.

#### Update source(s)

The sources we currently use are: OncoTree, OMIM, Disease Ontology, and Mondo.

The application will automatically retrieve input data for all sources but OMIM, for which a source file must be manually acquired and placed in the `disease/data/omim` folder within the library root. In order to access OMIM data, users must submit a request [here](https://www.omim.org/downloads). Once approved, the relevant OMIM file (`mimTitles.txt`) should be renamed according to the convention `omim_YYYYMMDD.tsv`, where `YYYYMMDD` indicates the date that the file was generated, and placed in the appropriate location.

To update one source, simply set `--normalizer` to the source you wish to update. Accepted source names are `DO` (for Disease Ontology), `Mondo`, `OncoTree`, and `OMIM`.

From the project root, run the following to update the Mondo source:

```commandline
python3 -m disease.cli --normalizer="Mondo"
```

To update multiple sources, you can use the `normalizer` flag with the source names separated by spaces.

```commandline
python3 -m disease.cli --normalizer="Mondo OMIM DO"
```

#### Update all sources

To update all sources, use the `--update_all` flag.

From the project root, run the following to update all sources:

```commandline
python3 -m disease.cli --update_all
```

### Create Merged Concept Groups
The `normalize` endpoint relies on merged concept groups.

To create merged concept groups, use the `--update_merged` flag with the `--update_all` flag.

```commandline
python3 -m disease.cli --update_all --update_merged
```

#### Specifying the database URL endpoint

The default URL endpoint is `http://localhost:8000`.

There are two different ways to specify the database URL endpoint.

The first way is to set the `--db_url` flag to the URL endpoint.

```commandline
python3 -m disease.cli --update_all --db_url="http://localhost:8001"
```

The second way is to set the `DISEASE_NORM_DB_URL` to the URL endpoint.
```commandline
export DISEASE_NORM_DB_URL="http://localhost:8001"
python3 -m disease.cli --update_all
```

### Starting the disease normalization service

From the project root, run the following:

```commandline
uvicorn disease.main:app --reload
```

Next, view the OpenAPI docs on your local machine:

http://127.0.0.1:8000/disease
