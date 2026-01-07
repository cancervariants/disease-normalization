Contributing
============

Bug reports and feature requests
--------------------------------

Bugs and new feature requests can be submitted to the `issue tracker on GitHub <https://github.com/cancervariants/disease-normalization/issues>`_. See `this StackOverflow post <https://stackoverflow.com/help/minimal-reproducible-example>`_ for tips on how to craft a helpful bug report.

Development setup
-----------------

Clone the repository: ::

    git clone https://github.com/cancervariants/disease-normalization
    cd disease-normalization

Then initialize a virtual environment: ::

    python3 -m virtualenv venv
    source venv/bin/activate
    python3 -m pip install -e '.[dev,tests,docs]'

We use `pre-commit <https://pre-commit.com/#usage>`_ to run conformance tests before commits. This provides checks for:

* Code format and style
* Added large files
* AWS credentials
* Private keys

Before your first commit, run: ::

    pre-commit install

Style
-----

Code style is managed by `Ruff <https://github.com/astral-sh/ruff>`_, and should be checked via pre-commit hook before commits. Final QC is applied with GitHub Actions to every pull request.

Tests
-----

Tests are executed with `pytest <https://docs.pytest.org/en/7.1.x/getting-started.html>`_: ::

    pytest

To employ testing data (e.g. in CI), first define the :ref:`app configuration<configuration>` to utilize the test environment: ::

    export DISEASE_NORM_ENV=test
    pytest


Documentation
-------------

The documentation is built with Sphinx, which is included as part of the ``docs`` dependency group. Navigate to the `docs/` subdirectory and use `make` to build the HTML version: ::

    cd docs
    make html

See the `Sphinx documentation <https://www.sphinx-doc.org/en/master/>`_ for more information.

Creating and Publishing Docker images
-------------------------------------

.. note::

    This section assumes you have push permissions for the DockerHub organization.

    It also assumes you have OMIM data located at ``$WAGS_TAILS_DIR/omim``, see
    :ref:`Wags-TAILS <wags-tails-dir>` for more details.

.. important::

    All commands in this section must be run from the **root of the repository**.

    These instructions assume a **fresh local DynamoDB setup**. The local DynamoDB
    data is stored in a bind-mounted Docker volume and **must be reset** before
    loading new data. Reusing an existing local DynamoDB volume is not supported.

Configure environment
^^^^^^^^^^^^^^^^^^^^^

Set your DockerHub organization. ::

    export DOCKERHUB_ORG=your-org

Set the ``WAGS_TAILS_DIR`` environment variable to your location. ::

    export WAGS_TAILS_DIR="$HOME/.local/share/wags_tails"

Set the image version from the most recent Git tag (used for API image). ::

    export VERSION=$(git describe --tags --abbrev=0)

Set the image date tag (used for DynamoDB image). ::

    export DATE=$(date +%F)

Reset local DynamoDB data
^^^^^^^^^^^^^^^^^^^^^^^^^

The local DynamoDB volume (``disease_norm_ddb_vol``) is configured as a *bind-mounted*
Docker volume that maps to the local ``dynamodb_local_latest`` directory. Because of
this, both the Docker volume **and** the local directory must be removed to ensure a
completely clean database state.

Remove the existing Docker volume. ::

    docker volume rm disease_norm_ddb_vol

Remove the local DynamoDB data directory. ::

    rm -rf dynamodb_local_latest

Recreate the local DynamoDB data directory. ::

    mkdir dynamodb_local_latest

Recreate the Docker volume (bind-mounted to a local directory). ::

    docker volume create --driver local --opt type=none --opt device="$(pwd)/dynamodb_local_latest" --opt o=bind disease_norm_ddb_vol

Build and run services locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start the services and load DynamoDB: ::

    docker compose -f compose-dev.yaml up --build

Build and publish API images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To tag and push the API images: ::

    docker build --build-arg VERSION=$VERSION -t $DOCKERHUB_ORG/disease-normalizer-api:$VERSION -t $DOCKERHUB_ORG/disease-normalizer-api:latest .
    docker push $DOCKERHUB_ORG/disease-normalizer-api:$VERSION
    docker push $DOCKERHUB_ORG/disease-normalizer-api:latest

Archive local DynamoDB data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To archive ``disease_norm_ddb_vol`` into ``./disease_norm_ddb.tar.gz``: ::

    docker run --rm \
        -v disease_norm_ddb_vol:/volume \
        -v "$(pwd)":/backup \
        alpine:3.23 \
        sh -c "cd /volume && tar czf /backup/disease_norm_ddb.tar.gz ."

Build and publish DynamoDB images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To tag and push the DynamoDB images: ::

    docker build -f Dockerfile.ddb -t $DOCKERHUB_ORG/disease-normalizer-ddb:$DATE -t $DOCKERHUB_ORG/disease-normalizer-ddb:latest .
    docker push $DOCKERHUB_ORG/disease-normalizer-ddb:$DATE
    docker push $DOCKERHUB_ORG/disease-normalizer-ddb:latest
