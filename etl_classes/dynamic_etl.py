from docx import Document
import jsonpickle
from data_classes.flag import FlagContainer, TextFlags, ParagraphFlags
from modifiers.paragraph_modifier import ParagraphModifier
from modifiers.text_modifier import TextModifier
from .base_etl_class import BaseETL
from json import loads

class DynamicETL(BaseETL):
    """
    A class that performs dynamic Extraction, Transformation, and Loading (ETL) of data from DOCX files.

    Args:
        data_dir (str): The directory containing the input DOCX files.
        dest_dir (str): The directory to save the transformed data.
        flags (FlagContainer): The flags specifying the transformation operations.

    """

    def __init__(self, data_dir: str, dest_dir: str, flags: FlagContainer):
        self._execute_etl(data_dir, dest_dir, flags)

    def _execute_etl(self, data_dir: str, dest_dir: str, flags: FlagContainer) -> None:
        """
        Executes the ETL process.

        Args:
            data_dir (str): The directory containing the input DOCX files.
            dest_dir (str): The directory to save the transformed data.
            flags (FlagContainer): The flags specifying the transformation operations.

        Returns:
            None

        """
        extracted_data = self._extract(data_dir)
        transformed_data = self._transform(extracted_data, flags)
        self._load(dest_dir, transformed_data)

    def _transform(self, data: list[Document], flags: FlagContainer):
        """
        Transforms the extracted data according to the specified flags.

        Args:
            data (list[Document]): The extracted data as a list of Document objects.
            flags (FlagContainer): The flags specifying the transformation operations.

        Returns:
            dict: The transformed data as a dictionary.

        """
        corpora_total = {}
        corpora_total["config"] = flags.__dict__
        corpora_total["documents"] = []
        text_flags = flags.text_flags
        paragraph_flags = flags.paragraph_flags

        removed_paragraphs = []  # TODO: Implement paragraphs
        for current_doc, filename in data:
            current_doc_obj = {"filename": filename}
            current_doc_corpora: list[dict] = []
            kept_paragraphs, _ = self.__remove_paragraphs_from_doc(current_doc.paragraphs, paragraph_flags)
            current_doc_corpora.extend(self.__transform_paragraphs_from_doc(kept_paragraphs, text_flags))
            current_doc_obj["corpora"] = current_doc_corpora
            corpora_total["documents"].append(current_doc_obj)

        return corpora_total

    def __remove_paragraphs_from_doc(self, doc_paragraphs, paragraph_flags: ParagraphFlags) -> tuple:
        """
        Removes paragraphs from a document based on the specified paragraph flags.

        Args:
            doc_paragraphs: The paragraphs in the document.
            paragraph_flags (ParagraphFlags): The flags specifying the paragraph removal operations.

        Returns:
            tuple: A tuple containing the modified document paragraphs and the removed paragraphs.

        """
        removed_paragraphs = []
        if paragraph_flags.remove_title_page:
            print("removing titlepage")
            corpora_with_headings_removed, removed_headings = ParagraphModifier.remove_title(doc_paragraphs)
            doc_paragraphs = corpora_with_headings_removed
            removed_paragraphs.extend(removed_headings)

        if paragraph_flags.remove_bibliography:
            print("removing bib")
            corpora_with_headings_removed, removed_headings = ParagraphModifier.remove_bibliography(doc_paragraphs)
            doc_paragraphs = corpora_with_headings_removed
            removed_paragraphs.extend(removed_headings)

        if paragraph_flags.remove_headings:
            corpora_with_headings_removed, removed_headings = ParagraphModifier.remove_headings(doc_paragraphs)
            doc_paragraphs = corpora_with_headings_removed
            removed_paragraphs.extend(removed_headings)

        if paragraph_flags.remove_tables_and_figures:
            corpora_with_headings_removed, removed_headings = ParagraphModifier.remove_tables_figures(doc_paragraphs)
            doc_paragraphs = corpora_with_headings_removed
            removed_paragraphs.extend(removed_headings)

        return doc_paragraphs, removed_paragraphs

    def __transform_paragraphs_from_doc(self, doc_paragraphs, text_flags: TextFlags) -> list[dict]:
        """
        Transforms the paragraphs from a document based on the specified text flags.

        Args:
            doc_paragraphs: The paragraphs in the document.
            text_flags (TextFlags): The flags specifying the text transformation operations.

        Returns:
            list[dict]: The transformed paragraphs as a list of dictionaries.

        """
        total_doc_corpora = []
        # prepare stop_words if necessary
        if text_flags.remove_stop_words:
            with open('stopwords.json', 'r') as file:
                stopwords = loads(file.read())  # list of Dutch stopwords

        for paragraph in doc_paragraphs:
            # Remove empty paragraphs
            if paragraph.text == "" or paragraph.text == " " or paragraph.text == "\n":
                continue

            # Remove paragraphs containing only 1 or 2 words
            if len(paragraph.text.split()) < 3:
                continue

            current_paragraph_obj = {"text": paragraph.text.strip(), "style": paragraph.style.name}  # TODO: use Paragraph class from data_classes -> paragraph.py
            # For each paragraph, check the flag dictionary
            if text_flags.remove_stop_words:
                print("removing stop words")
                current_paragraph_obj["text"] = TextModifier.remove_stop_words(current_paragraph_obj["text"], stopwords)

            if text_flags.apply_lemmatization:
                print("applying lemmatization")
                current_paragraph_obj["text"] = TextModifier.apply_lemmatization(current_paragraph_obj["text"])

            if text_flags.apply_stemming:
                print("applying stemming")
                current_paragraph_obj["text"] = TextModifier.apply_stemming(current_paragraph_obj["text"])

            if text_flags.remove_punctuation:
                print("removing punctuation")
                current_paragraph_obj["text"] = TextModifier.remove_punctuation(current_paragraph_obj["text"])

            total_doc_corpora.append(current_paragraph_obj)

        return total_doc_corpora

    def _load(self, dest_str: str, data):
        """
        Loads the transformed data to the specified destination.

        Args:
            dest_str (str): The destination file path.
            data: The transformed data.

        Returns:
            None

        """
        json_str = jsonpickle.encode(data, unpicklable=False)
        with open(dest_str, "w") as f:
            f.write(json_str)
