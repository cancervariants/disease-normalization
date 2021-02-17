# Disease Normalization
Services and guidelines for normalizing disease terms

## Developer instructions
Following are sections include instructions specifically for developers.

### Installation
For a development install, we recommend using Pipenv. See the
[pipenv docs](https://pipenv-fork.readthedocs.io/en/latest/#install-pipenv-today)
for direction on installing pipenv in your compute environment.

Once installed, from the project root dir, just run:

```shell script
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

### Starting the disease normalization service

From the project root, run the following:

```shell script
 uvicorn main:app --reload
```

Next, view the OpenAPI docs on your local machine:

http://127.0.0.1:8000/disease
