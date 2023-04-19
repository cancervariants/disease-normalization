"""Construct test data for NCIt source."""
from pathlib import Path
from typing import Generator
import xml.etree.ElementTree as XET

import owlready2 as owl
import lxml.etree as ET
import xmlformatter

from disease.etl import DO
from disease.database import Database

# define captured ids in `test_classes` variable

DO_PREFIX = "http://purl.obolibrary.org/obo/doid/doid-merged.owl"
OWL_PREFIX = "{http://www.w3.org/2002/07/owl#}"
RDFS_PREFIX = "{http://www.w3.org/2000/01/rdf-schema#}"
RDF_PREFIX = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"

ANNOTATION_PROPERTY_TAG = f"{OWL_PREFIX}AnnotationProperty"
DESCRIPTION_TAG = f"{RDF_PREFIX}Description"
ABOUT_ATTRIB = f"{RDF_PREFIX}about"
AXIOM_TAG = f"{OWL_PREFIX}Axiom"
DATATYPE_TAG = f"{RDFS_PREFIX}Datatype"
OBJECT_PROPERTY_TAG = f"{OWL_PREFIX}ObjectProperty"
CLASS_TAG = f"{OWL_PREFIX}Class"
ONTOLOGY_TAG = f"{OWL_PREFIX}Ontology"
ANNOTATED_SOURCE_TAG = f"{OWL_PREFIX}annotatedSource"
RESOURCE_KEY = f"{RDF_PREFIX}resource"


do = DO(Database())
do._extract_data()

onto = owl.get_ontology(do._data_file.absolute().as_uri())
onto.load()
test_uris = [
    "http://purl.obolibrary.org/obo/DOID_769",
    "http://purl.obolibrary.org/obo/DOID_5695",
    "http://purl.obolibrary.org/obo/DOID_1703",
    "http://purl.obolibrary.org/obo/DOID_7079",
    "http://purl.obolibrary.org/obo/DOID_3908",
]

parent_concepts = set()
for uri in test_uris:
    result = onto.search(iri=uri)[0]
    parent_concepts |= result.ancestors()  # type: ignore
parent_concepts.remove(owl.Thing)
parent_concept_iris = {p.iri for p in parent_concepts}


def do_parser() -> Generator:
    """Get unique XML elements."""
    context = iter(
        ET.iterparse(
            do._data_file,
            events=("start", "end"),
            huge_tree=True
        )
    )
    for event, elem in context:
        if event == "start":
            yield elem


parser = do_parser()

# make root element
root = next(parser)
nsmap = root.nsmap
new_root = ET.Element(f"{RDF_PREFIX}RDF", nsmap=nsmap)
new_root.set(
    "{http://www.w3.org/XML/1998/namespace}base",
    "http://purl.obolibrary.org/obo/doid/doid-merged.owl",
)


# get annotations/object properties/etc if they're immediate children of root
def element_is_related_axiom(element):
    """TODO"""
    return (
        element.tag == AXIOM_TAG and
        element.find(
            ANNOTATED_SOURCE_TAG
        ).attrib.get(RESOURCE_KEY) in parent_concept_iris
    )


POSSIBLE_ROOT_TAGS = {
    ONTOLOGY_TAG,
    ANNOTATION_PROPERTY_TAG,
    AXIOM_TAG,
    DESCRIPTION_TAG,
    OBJECT_PROPERTY_TAG,
    CLASS_TAG
}
root_attrib = root.attrib
element = next(parser)
while True:
    if element.getparent().attrib == root_attrib or element_is_related_axiom(element):
        if element.sourceline > 791:
            breakpoint()
        new_root.append(element)
    try:
        element = next(parser)
    except StopIteration:
        break


# # add ontology element
# element = next(parser)
# new_root.append(element)
#
# # grab annotations, descriptions, etc.
# # technically don't need all of them but easier to just keep everything
# keeper_tags = {ANNOTATION_PROPERTY_TAG, DESCRIPTION_TAG, OBJECT_PROPERTY_TAG}
#
# while element.tag != CLASS_TAG:
#     if element.tag in keeper_tags:
#         new_root.append(element)
#     element = next(parser)
#
#
# # get classes
# # first, get all associated concepts for the terms we're interested in
# onto = owl.get_ontology(do._data_file.absolute().as_uri())
# onto.load()
# test_uris = [
#     "http://purl.obolibrary.org/obo/DOID_769",
#     "http://purl.obolibrary.org/obo/DOID_5695",
#     "http://purl.obolibrary.org/obo/DOID_1703",
#     "http://purl.obolibrary.org/obo/DOID_7079",
#     "http://purl.obolibrary.org/obo/DOID_3908",
# ]
#
# parent_concepts = set()
# for uri in test_uris:
#     result = onto.search(iri=uri)[0]
#     parent_concepts |= result.ancestors()  # type: ignore
# parent_concepts.remove(owl.Thing)
# parent_concept_iris = {p.iri for p in parent_concepts}
#
# # double check that we don't need non-DO classes
# assert all(["DOID" in i for i in parent_concept_iris])
#
# while element.tag != DESCRIPTION_TAG:
#     elements = [element]
#     element = next(parser)
#     while element.tag != CLASS_TAG or ABOUT_ATTRIB not in element.attrib:
#     # while (
#     #     element.tag != CLASS_TAG or ABOUT_ATTRIB not in element.attrib
#     # ) and element.attrib.get(ABOUT_ATTRIB) != DESCRIPTION_TAG:
#         if element.tag == AXIOM_TAG:
#             elements.append(element)
#         elif element.tag == DESCRIPTION_TAG and \
#                 element.attrib.get(ABOUT_ATTRIB) == "http://purl.obolibrary.org/obo/GENO_0000150":  # noqa: E501
#             break
#         element = next(parser)
#     if elements[0].attrib.get(ABOUT_ATTRIB) in parent_concept_iris:
#         for e in elements:
#             new_root.append(e)
#     else:
#         for e in elements:
#             e.clear()


# # get annotation property elements
# element = next(parser)
# while element.tag != ANNOTATION_PROPERTY_TAG:
#     element = next(parser)
#
# while element.tag != DESCRIPTION_TAG:
#     new_root.append(element)
#     element = next(parser)
#     while element.tag != ANNOTATION_PROPERTY_TAG and element.tag != DESCRIPTION_TAG:
#         if element.tag == AXIOM_TAG:
#             new_root.append(element)
#         element = next(parser)
#
# # get description element
# while element.tag != ANNOTATION_PROPERTY_TAG:
#     new_root.append(element)
#     element = next(parser)
#     while element.tag != ANNOTATION_PROPERTY_TAG:
#         if element.tag == AXIOM_TAG:
#             new_root.append(element)
#         element = next(parser)
#
# # back to annotation property elements
# while element.tag != OBJECT_PROPERTY_TAG:
#     new_root.append(element)
#     element = next(parser)
#     while element.tag != ANNOTATION_PROPERTY_TAG:
#         if element.tag == AXIOM_TAG:
#             new_root.append(element)
#         element = next(parser)
#
# breakpoint()
#
# # get object property elements
# while element.tag != CLASS_TAG:
#     new_root.append(element)
#     element = next(parser)
#     while element.tag != OBJECT_PROPERTY_TAG:
#         if element.tag == AXIOM_TAG:
#             new_root.append(element)
#         element = next(parser)
#
# # get classes
# onto = owl.get_ontology(do._data_file.absolute().as_uri())
# onto.load()
# test_uris = [
#     "http://purl.obolibrary.org/obo/DOID_769",
#     "http://purl.obolibrary.org/obo/DOID_5695",
#     "http://purl.obolibrary.org/obo/DOID_1703",
#     "http://purl.obolibrary.org/obo/DOID_7079",
#     "http://purl.obolibrary.org/obo/DOID_3908",
# ]
#
# parent_concepts = set()
# for uri in test_uris:
#     result = onto.search(iri=uri)[0]
#     parent_concepts |= result.ancestors()  # type: ignore
# parent_concepts.remove(owl.Thing)
# parent_concept_iris = {p.iri for p in parent_concepts}
#
# while element.attrib.get(ABOUT_ATTRIB) != f"{DO_PREFIX}#term-group":
#     elements = [element]
#     element = next(parser)
#     while (
#         element.tag != CLASS_TAG or ABOUT_ATTRIB not in element.attrib
#     ) and element.attrib.get(ABOUT_ATTRIB) != f"{DO_PREFIX}#term-group":
#         if element.tag == AXIOM_TAG:
#             elements.append(element)
#         element = next(parser)
#     if elements[0].attrib.get(ABOUT_ATTRIB) in parent_concept_iris:
#         for e in elements:
#             new_root.append(e)
#     else:
#         for e in elements:
#             e.clear()
#
# # get description elements
# EOF = False
# while not EOF:
#     new_root.append(element)
#     element = next(parser)
#     while True:
#         if element.tag == AXIOM_TAG:
#             new_root.append(element)
#         try:
#             element = next(parser)
#         except StopIteration:
#             EOF = True
#             break
#         if element.tag == DESCRIPTION_TAG:
#             break
#


TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "do"
outfile_path = TEST_DATA_DIR / do._data_file.name
outfile_path.parent.mkdir(exist_ok=True)

ET.ElementTree(new_root).write(outfile_path, pretty_print=True)

pi = XET.ProcessingInstruction(  # TODO get encoding attrib out
    target='xml version="1.0"'
)
pi_string = XET.tostring(pi).decode("ASCII")
with open(outfile_path, "r+") as f:
    content = f.read()
    f.seek(0, 0)
    f.write(pi_string.rstrip("\r\n") + "\n" + content)

formatter = xmlformatter.Formatter(indent=2)
formatter.format_file(outfile_path)
