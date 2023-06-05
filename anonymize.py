# For Presidio
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider

# For extracting text
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextLine

# For command line arguments
import argparse

import os

# For stanza
# import stanza
# stanza.download("de")


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

# Analyzer
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


# provider2 = NlpEngineProvider(nlp_configuration={
#     "nlp_engine_name": "stanza",
#     "models": [{"lang_code": "de",
#                 "model_name": "de"
#                 }]
# })
# analyzer2 = AnalyzerEngine(
#     nlp_engine=provider2.create_engine(), supported_languages=["de"])

code_recognizer = PatternRecognizer(supported_entity="CODE",
                                    supported_language="de",
                                    patterns=[Pattern(name="code",
                                                      # for numbers between 5 digits long
                                                      regex=r"\d{5}\d+",
                                                      score=0.5)])

postcode_recognizer = PatternRecognizer(supported_entity="POSTCODE",
                                        supported_language="de",
                                        patterns=[Pattern(name="postcode",
                                                          # for numbers between 5 digits long
                                                          regex=r"\d{5}",
                                                          score=0.5)])

analyzer.registry.add_recognizer(postcode_recognizer)
analyzer.registry.add_recognizer(code_recognizer)

operators = {"PERSON": OperatorConfig("replace"),
             "DATE_TIME": OperatorConfig("replace"),
             "NRP": OperatorConfig("replace"),
             "LOCATION": OperatorConfig("replace"),
             "PHONE_NUMBER": OperatorConfig("replace"),
             "EMAIL_ADDRESS": OperatorConfig("replace"),
             "CODE": OperatorConfig("replace"),
             "POSTCODE": OperatorConfig("replace"),
             "URL": OperatorConfig("replace")
             }

anonymizer = AnonymizerEngine()

for filename in filenames:
    text_to_anonymize = extract_text(filename)

    # NRP: Nationality, religious or political

    # Analyze the text using the analyzer engine
    res_all = analyzer.analyze(
        text=text_to_anonymize, language='de', entities=[
            'DATE_TIME', 'NRP', 'PHONE_NUMBER', 'EMAIL_ADDRESS', 'URL', 'IBAN_CODE', 'CODE', 'POSTCODE'
        ], score_threshold=0.3)
    # NER Score is always 0.85
    res_person = analyzer.analyze(
        text=text_to_anonymize, language='de', entities=['PERSON'
                                                         ], score_threshold=0.6)

    res_loc = analyzer.analyze(
        text=text_to_anonymize, language='de', entities=['LOCATION'
                                                         ], score_threshold=0.6)

    res = res_all + res_person + res_loc
    anonymized_results = anonymizer.anonymize(text=text_to_anonymize,
                                              analyzer_results=res,
                                              operators=operators)

    with open(filename.removesuffix(".pdf") + ".txt", 'w') as f:
        f.write(anonymized_results.text)

exit(0)
