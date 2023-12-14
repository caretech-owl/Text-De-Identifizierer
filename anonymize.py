# For Presidio
from presidio_analyzer import (
    AnalyzerEngine, PatternRecognizer, Pattern, RecognizerRegistry)
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider
from flair_recognizer import FlairRecognizer

# For extracting text
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextLine
import docx

# For command line arguments
import argparse

import os

# Get commandline arguments
parser = argparse.ArgumentParser(
    prog='Text-Anonymisierer',
    description='Anonymisiert deutschsprachige Texte',
    epilog='')
parser.add_argument('filename', type=str,
                    help="Datei oder Ordner mit Dateien")
args = parser.parse_args()

# Gather filenames
filenames = []
if (args.filename.endswith('pdf') or
    args.filename.endswith('docx') or
    args.filename.endswith('log') or
        args.filename.endswith('txt')):
    filenames = [args.filename, ]
    if not os.path.isfile(args.filename):
        print("File not found!")
        exit(1)
elif os.path.isdir(args.filename):
    # Get files in path
    filenames = [
        os.path.join(args.filename, f) for f in os.listdir(args.filename)
        if os.path.isfile(os.path.join(args.filename, f)) and
        (f.endswith('.pdf') or f.endswith('.docx') or f.endswith('.log')
         or f.endswith('.txt'))]

if len(filenames) == 0:
    print("No files found! Supported file types: pdf, docx, log, txt")
    exit(1)

# German Spacy model
provider = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "de",
                "model_name": "de_core_news_lg"
                }]
})
analyzer = AnalyzerEngine(
    nlp_engine=provider.create_engine(), supported_languages=["de", "en"])

# Flair https://github.com/flairNLP/flair
# is better in recognizing german names and locations
flair_recognizer = (
    FlairRecognizer(supported_language="de")
)  # This downloads a large (+2GB) model on the first run
registry = RecognizerRegistry()
registry.add_recognizer(flair_recognizer)
fl_analyzer = AnalyzerEngine(
    registry=registry, nlp_engine=provider.create_engine(),
    supported_languages="de")


# Breaks for german https://github.com/explosion/spacy-stanza/issues/70
# import stanza
# stanza.download("de")
# provider2 = NlpEngineProvider(nlp_configuration={
#     "nlp_engine_name": "stanza",
#     "models": [{"lang_code": "de",
#                 "model_name": "de"
#                 }]
# })
# analyzer2 = AnalyzerEngine(
#     nlp_engine=provider2.create_engine(), supported_languages=["de"])

###
# Custom recognizers
###

# Everything above 5 digits
code_recognizer = PatternRecognizer(supported_entity="CODE",
                                    supported_language="de",
                                    patterns=[Pattern(name="code",
                                                      regex=r"\d{5}\d+",
                                                      score=0.5)])

postcode_recognizer = PatternRecognizer(supported_entity="POSTCODE",
                                        supported_language="de",
                                        patterns=[Pattern(name="postcode",
                                                          regex=r"\d{5}",
                                                          score=0.5)])
# Merge Location and housnumber, Used after first anonymization run
street_recognizer = PatternRecognizer(
    supported_entity="STREET", supported_language="de",
    patterns=[
        Pattern(
            name="street", regex=r"<LOCATION>.?\s*(\d{1,4})",
            score=0.5)])

# Sorts out abbreviated dates
date_recognizer = PatternRecognizer(
    supported_entity="DATE", supported_language="de",
    patterns=[Pattern(name="date", regex=r"\d{2}/\d{4}", score=0.5),
              Pattern(
                  name="date_dot", regex=r"\d{2}.\d{4}", score=0.5)])

analyzer.registry.add_recognizer(postcode_recognizer)
analyzer.registry.add_recognizer(code_recognizer)
analyzer.registry.add_recognizer(street_recognizer)
analyzer.registry.add_recognizer(date_recognizer)

# Replace everything by <NAME>
operators = {"PERSON": OperatorConfig("replace"),
             "DATE_TIME": OperatorConfig("replace"),
             "NRP": OperatorConfig("replace"),
             "LOCATION": OperatorConfig("replace"),
             "PHONE_NUMBER": OperatorConfig("replace"),
             "EMAIL_ADDRESS": OperatorConfig("replace"),
             "CODE": OperatorConfig("replace"),
             "POSTCODE": OperatorConfig("replace"),
             "URL": OperatorConfig("replace"),
             "ORGANIZATION": OperatorConfig("replace"),
             "STREET": OperatorConfig("replace"),
             "DATE": OperatorConfig("replace")
             }

anonymizer = AnonymizerEngine()


def getTextDocx(filename: str) -> str:
    """Opens a "Word" document in docx/doc file format. Uses docx library

    Args:
        filename (str): name of the file

    Returns:
        str: text of the document
    """
    doc = docx.Document(filename)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    res = ""
    for line in fullText:
        res = res + line + "\n"

    return res


if not os.path.exists("output"):
    os.mkdir("output")
for filename in filenames:
    if filename.endswith("pdf"):
        text_to_anonymize = extract_text(filename)
    elif filename.endswith("docx"):
        text_to_anonymize = getTextDocx(filename)
    elif filename.endswith("log") or filename.endswith("txt"):
        with open(filename, 'r') as f:
            text_to_anonymize = f.read()
    else:
        print("Cannot open file: ", filename)
        continue

    # Analyze the text using the analyzer engine
    res_fl = fl_analyzer.analyze(
        text=text_to_anonymize, language='de', entities=[
            'PERSON', 'LOCATION', 'ORGANIZATION'
        ], score_threshold=0.3)
    text_to_anonymize = anonymizer.anonymize(text=text_to_anonymize,
                                             analyzer_results=res_fl,
                                             operators=operators).text
    # Rerun for addresses
    res_all = analyzer.analyze(
        text=text_to_anonymize, language='de', entities=[
            'STREET'
        ], score_threshold=0.3)

    text_to_anonymize = anonymizer.anonymize(text=text_to_anonymize,
                                             analyzer_results=res_all,
                                             operators=operators).text

    # Rerun for all other entities
    # NRP: Nationality, religious or political
    res_all = analyzer.analyze(
        text=text_to_anonymize, language='de',
        entities=['DATE_TIME', 'NRP', 'PHONE_NUMBER', 'EMAIL_ADDRESS', 'URL',
                  'IBAN_CODE', 'CODE', 'POSTCODE', 'DATE'],
        score_threshold=0.3)

    anonymized_results = anonymizer.anonymize(text=text_to_anonymize,
                                              analyzer_results=res_all,
                                              operators=operators)

    # Save file
    new_file = "output/" + os.path.basename(filename)
    for i in [".pdf", ".docx", ".log", ".txt"]:
        new_file = new_file.removesuffix(i)
    with open(new_file + ".txt", 'w') as f:
        f.write(anonymized_results.text)

exit(0)
