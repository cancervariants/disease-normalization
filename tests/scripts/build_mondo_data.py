"""Construct test data for Mondo source.

This saves a tar file named `fixture_mondo_XXXX-XX-XX.ow.tar.gz` in the test data
directory, because the OWL output is still too large to commit to the repo. Methods
using it should a) make sure to check for files with the `fixture_` prefix, and b)
remember to decompress it.
"""
import os
import subprocess
import tarfile
from http import HTTPStatus
from pathlib import Path

import requests

from disease.database import create_db
from disease.etl import Mondo

mondo = Mondo(create_db())
mondo._extract_data()

infile = mondo._data_file.absolute()

scripts_dir = Path(__file__).resolve().parent
test_data_dir = scripts_dir.parent / "data" / "mondo"

robot_file = scripts_dir / "robot"
if not robot_file.exists():
    response = requests.get(
        "https://raw.githubusercontent.com/ontodev/robot/master/bin/robot"
    )
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError("Couldn't acquire robot script")
    with open(robot_file, "wb") as f:
        f.write(response.content)
    try:
        os.chmod(robot_file, 0o755)
    except PermissionError:
        pass  # handle below
if not os.access(robot_file, os.X_OK):
    raise PermissionError(
        "robot file isn't executable by the user -- see 'getting started': http://robot.obolibrary.org/"  # noqa: E501
    )

robot_jar = scripts_dir / "robot.jar"
if not robot_jar.exists():
    response = requests.get(
        "https://api.github.com/repos/ontodev/robot/releases/latest"
    )
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError("Couldn't get ROBOT release info from GitHub")
    json = response.json()
    assert json["assets"][0]["name"] == "robot.jar"
    jar_url = json["assets"][0]["url"]
    jar_response = requests.get(jar_url)
    if jar_response.status_code != HTTPStatus.OK:
        raise requests.HTTPError("Couldn't download ROBOT JAR from GitHub")
    with open(robot_jar, "wb") as f:
        f.write(jar_response.content)

terms_file = scripts_dir / "mondo_terms.txt"
if not terms_file.exists():
    raise FileNotFoundError("Could not find mondo_terms.txt")

outfile = test_data_dir / mondo._data_file.name
outfile.parent.mkdir(exist_ok=True)
cmd_str = f"{robot_file} extract --method star --input {infile} --term-file {terms_file} --output {outfile}"  # noqa: E501

subprocess.run(cmd_str, shell=True)

# save compressed file as `fixture_mondo_XXXX-XX-XX.owl.tar.gz`
tarball = outfile.parent / f"fixture_{outfile.name}.tar.gz"

with tarfile.open(tarball, "w:gz") as tar:
    tar.add(outfile, arcname=outfile.name)
