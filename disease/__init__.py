"""The VICC library for normalizing diseases."""
from pathlib import Path
import logging


PROJECT_ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(
    filename='disease.log',
    format='[%(asctime)s] %(levelname)s : %(message)s')
logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)
