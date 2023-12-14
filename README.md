# Text De-Identifizierer

This project provides a skript for automatic removal of direct personal identifiers in pdf, docx, txt and log files. Note that, according to GDPR, this is not a full anonymization scheme. However, the procedure of masking direct identifiers can be part of technical measures for data privacy.

## Installation

We assume that python and git are installed and there is basic knowledge about both tools. Here, we provide commands to install requirements in a python virtualenv, which have been tested on Linux.

```sh
git clone https://github.com/caretech-owl/text-anonymisierer
cd text-anonymisierer
python -m venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

For de-identifying a single file:
```sh
source venv/bin/activate
python anonymize.py path/to/file
```

For- de-iidentifying files in a directory:
```sh
source venv/bin/activate
python anonymize.py path/

```
Results are saved as txt in a directory called output. 


