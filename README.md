# Disease Normalization
Services and guidelines for normalizing disease terms

## Developer instructions
Following are sections include instructions specifically for developers.

### Installation
For a development install, we recommend using Pipenv. See the
[pipenv docs](https://pipenv-fork.readthedocs.io/en/latest/#install-pipenv-today)
for direction on installing pipenv in your compute environment.

Once installed, from the project root dir, run:

```commandline
pipenv sync
```

### Data files
If source data files aren't found in the expected subdirectories (within `data/` by default), the application will attempt to download them directly.

### Init coding style tests

Code style is managed by [flake8](https://github.com/PyCQA/flake8) and checked prior to commit.

We use [pre-commit](https://pre-commit.com/#usage) to run conformance tests.

This ensures:

* Check code style
* Check for added large files
* Detect AWS Credentials
* Detect Private Key

Before first commit run:

```
pre-commit install
```


### Running unit tests

Running unit tests is as easy as pytest.

```
pipenv run pytest
```

### Updating the disease normalization database

Before you use the CLI to update the database, run the following in a separate terminal to start DynamoDB on `port 8000`:

```
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb
```

To change the port, simply add `-port value`.

#### Update source(s)
The sources we currently use are:  NCIt, Mondo, DO, and OncoTree.

To update one source, simply set `--normalizer` to the source you wish to update. 

From the project root, run the following to update the NCIt source:

```commandline
python3 -m disease.cli --normalizer="ncit"
```

To update multiple sources, you can use the `normalizer` flag with the source names separated by spaces.

#### Update all sources

To update all sources, use the `--update_all` flag. 

From the project root, run the following to update all sources:

```commandline
python3 -m disease.cli --update_all
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

```shell script
 uvicorn main:app --reload
```

Next, view the OpenAPI docs on your local machine:

http://127.0.0.1:8000/disease
