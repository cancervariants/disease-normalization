"""Construct test data for DO source."""
import os
import subprocess
from http import HTTPStatus
from pathlib import Path

import requests

from disease.database import create_db
from disease.etl import DO

do = DO(create_db())
do._extract_data()

infile = do._data_file.absolute()

scripts_dir = Path(__file__).resolve().parent
test_data_dir = scripts_dir.parent / "data" / "do"

robot_file = scripts_dir / "robot"
if not robot_file.exists():
    response = requests.get(
        "https://raw.githubusercontent.com/ontodev/robot/master/bin/robot"
    )  # noqa: E501
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
    )  # noqa: E501

robot_jar = scripts_dir / "robot.jar"
if not robot_jar.exists():
    response = requests.get(
        "https://api.github.com/repos/ontodev/robot/releases/latest"
    )  # noqa: E501
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

terms_file = scripts_dir / "do_terms.txt"
if not terms_file.exists():
    raise FileNotFoundError("Could not find do_terms.txt")

outfile = test_data_dir / do._data_file.name
outfile.parent.mkdir(exist_ok=True)
cmd_str = f"{robot_file} extract --method star --input {infile} --term-file {terms_file} --output {outfile}"  # noqa: E501

subprocess.run(cmd_str, shell=True)
