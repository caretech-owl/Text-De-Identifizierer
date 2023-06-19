# For Presidio
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider
from flair_recognizer import FlairRecognizer

# For extracting text
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextLine

# For command line arguments
import argparse

import os

# For stanza
# import stanza
# stanza.download("de")

# Get commandline arguments
parser = argparse.ArgumentParser(
    prog='PDF-Anonymisierer',
    description='Anonymisiert deutschsprachige PDFs',
    epilog='')

parser.add_argument('filename', type=str,
                    help="Datei (Endung .pdf) oder Ordner mit Dateien")
args = parser.parse_args()

if args.filename.endswith('pdf'):
    filenames = [args.filename, ]
else:
    # Get files in path
    filenames = [os.path.join(args.filename, f) for f in os.listdir(args.filename) if
                 os.path.isfile(os.path.join(args.filename, f))
                 and f.endswith('.pdf')
                 ]

# German Spacy model
provider = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "de",
                "model_name": "de_core_news_lg"
                }  # , {
               #   "lang_code": "en",
               #   "model_name": "en_core_web_lg"
               # }
               ]
})
analyzer = AnalyzerEngine(
    nlp_engine=provider.create_engine(), supported_languages=["de", "en"])

# Flair https://github.com/flairNLP/flair is better in recognizing german names and locations
flair_recognizer = (
    FlairRecognizer(supported_language="de")
)  # This downloads a large (+2GB) model on the first run
registry = RecognizerRegistry()
registry.add_recognizer(flair_recognizer)
fl_analyzer = AnalyzerEngine(
    registry=registry, nlp_engine=provider.create_engine(), supported_languages="de")


# Breaks for german https://github.com/explosion/spacy-stanza/issues/70
# provider2 = NlpEngineProvider(nlp_configuration={
#     "nlp_engine_name": "stanza",
#     "models": [{"lang_code": "de",
#                 "model_name": "de"
#                 }]
# })
# analyzer2 = AnalyzerEngine(
#     nlp_engine=provider2.create_engine(), supported_languages=["de"])

# Everything above 5 digits
code_recognizer = PatternRecognizer(supported_entity="CODE",
                                    supported_language="de",
                                    patterns=[Pattern(name="code",
                                                      # for numbers being more than 5 digits long
                                                      regex=r"\d{5}\d+",
                                                      score=0.5)])

postcode_recognizer = PatternRecognizer(supported_entity="POSTCODE",
                                        supported_language="de",
                                        patterns=[Pattern(name="postcode",
                                                          # for numbers being  5 digits long
                                                          regex=r"\d{5}",
                                                          score=0.5)])

street_recognizer = PatternRecognizer(supported_entity="STREET",
                                      supported_language="de",
                                      patterns=[Pattern(name="street",
                                                             # Merge Location and housnumber, Used after first anonymization run
                                                             regex=r"<LOCATION>.?\s*(\d{1,4})",
                                                             score=0.5)])
date_recognizer = PatternRecognizer(supported_entity="DATE",
                                    supported_language="de",
                                    patterns=[Pattern(name="date",
                                                      # Sorts out abbreviated dates
                                                      regex=r"\d{2}/\d{4}",
                                                      score=0.5), Pattern(name="date_dot",
                                                                          regex=r"\d{2}.\d{4}",
                                                                          score=0.5)])

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

for filename in filenames:
    text_to_anonymize = extract_text(filename)

    # Analyze the text using the analyzer engine
    res_fl = fl_analyzer.analyze(
        text=text_to_anonymize, language='de', entities=[
            'PERSON', 'LOCATION', 'ORGANIZATION'
        ], score_threshold=0.3)

    # NRP: Nationality, religious or political
    res_all = analyzer.analyze(
        text=text_to_anonymize, language='de', entities=[
            'DATE_TIME', 'NRP', 'PHONE_NUMBER', 'EMAIL_ADDRESS', 'URL', 'IBAN_CODE', 'CODE', 'POSTCODE', 'DATE'
        ], score_threshold=0.3)

    res = res_all + res_fl
    anonymized_results = anonymizer.anonymize(text=text_to_anonymize,
                                              analyzer_results=res,
                                              operators=operators)

    # Rerun for addresses
    res_all = analyzer.analyze(
        text=anonymized_results.text, language='de', entities=[
            'STREET'
        ], score_threshold=0.3)

    anonymized_results = anonymizer.anonymize(text=anonymized_results.text,
                                              analyzer_results=res_all,
                                              operators=operators)
    with open(filename.removesuffix(".pdf") + ".txt", 'w') as f:
        f.write(anonymized_results.text)

exit(0)
