# coding=utf-8
import re
import string

from language_utilities.constant import ENGLISH_LANG, HINDI_LANG
from lib.nlp.const import nltk_tokenizer
from lib.nlp.pos import POS
from ner_v1.constant import EMOJI_RANGES, FIRST_NAME, MIDDLE_NAME, LAST_NAME
from ner_v1.detectors.textual.name.hindi_const import (HINDI_BADWORDS, HINDI_QUESTIONWORDS,
                                                       HINDI_STOPWORDS, NAME_VARIATIONS,
                                                       COMMON_HINDI_WORDS_OCCURING_WITH_NAME)
from ner_v1.detectors.textual.text.text_detection import TextDetector


# TODO: Refactor this module for readability and useability. Remove any hacks
# TODO: Make this module python 3 compatible

class NameDetector(object):
    """
    NameDetector class detects names from text. This class uses TextDetector
    to detect the entity values. This class also contains templates and pos_tagger to capture
    names which are missed by TextDetector.

    Attributes:
        text: string to extract entities from
        entity_name: string by which the detected person_name entities would be replaced with
                     on calling detect_entity()
        tagged_text: string with city entities replaced with tag defined by entity_name
        processed_text: string with detected time entities removed
        text_detection_object: the object which is used to call the TextDetector
    """

    def __init__(self, entity_name, language=ENGLISH_LANG):
        """
        Initializes a NameDetector object with given entity_name

        Args:
            entity_name: A string by which the detected substrings that correspond to text entities would be replaced
                         with on calling detect_entity()
        """
        self.entity_name = entity_name
        self.language = language
        self.text = ''
        self.names = []
        self.tagged_text = ''
        self.processed_text = ''
        self.original_name_text = []
        self.tag = '_' + entity_name + '_'
        self.text_detection_object = TextDetector(entity_name=entity_name)

    @staticmethod
    def get_format_name(name_list):
        """
        Takes input as name_list which contains the names detected.
        It separates the first, middle and last names.
        It returns two lists:
        1.Containing the names separated into first, middle and last name.
        2.The original text.

        Args:
            name_list (list): List of names detected
            Example:
                 ['yash', 'doshi']

        Returns:
            (
                [{first_name: "yash", middle_name: None, last_name: "doshi"}],
                ["yash modi"]
            )
        """
        original_text = " ".join(name_list)

        first_name = name_list[0]
        middle_name = None
        last_name = None

        if len(name_list) > 1:
            last_name = name_list[-1]
            middle_name = " ".join(name_list[1:-1]) or None

        entity_value = {FIRST_NAME: first_name, MIDDLE_NAME: middle_name, LAST_NAME: last_name}

        return [entity_value], [original_text]

    def text_detection_name(self, text=None):
        """
        Makes a call to TextDetection and return the person_name detected from the elastic search.
        Returns:
           Tuple with list of names detected in TextDetection in the form of variants detected and original_text

         Example : my name is yash doshi

         ([u'dosh', u'yash'], ['doshi', 'yash'])
        """
        if text is None:
            text = self.text
        return self.text_detection_object.detect_entity(text=text)

    def get_name_using_pos_tagger(self, text):
        """
        First checks if the text contains cardinals or interrogation.
        Then passes the text through templates.
        Then returns words which are nouns or adjectives
        Args:
            text (string): The text obtained from the user.

            Example text= My name is yash modi
        Returns:
            [{first_name: "yash", middle_name: None, last_name: "modi"}], ["yash modi"]
        """

        entity_value, original_text = [], []
        pos_tagger_object = POS()
        pattern1 = re.compile(r"name\s*(is|)\s*([\w\s]+)")
        pattern2 = re.compile(r"myself\s+([\w\s]+)")
        pattern3 = re.compile(r"call\s+me\s+([\w\s]+)")
        name_tokens = text.split()
        # Passing empty tokens to tag will cause IndexError
        tagged_names = pos_tagger_object.tag(name_tokens)
        pattern1_match = pattern1.findall(text)
        pattern2_match = pattern2.findall(text)
        pattern3_match = pattern3.findall(text)

        is_question = [word[0] for word in tagged_names if word[1].startswith('WR') or
                       word[1].startswith('WP') or word[1].startswith('CD')]
        if is_question:
            return entity_value, original_text

        if pattern1_match:
            entity_value, original_text = self.get_format_name(pattern1_match[0][1].split())

        elif pattern2_match:
            entity_value, original_text = self.get_format_name(pattern2_match[0].split())

        elif pattern3_match:
            entity_value, original_text = self.get_format_name(pattern3_match[0].split())

        elif len(name_tokens) < 4:
            pos_words = [word[0] for word in tagged_names if word[1].startswith('NN') or
                         word[1].startswith('JJ')]
            if pos_words:
                entity_value, original_text = self.get_format_name(pos_words)

        return entity_value, original_text

    def detect_entity(self, text, bot_message=None):
        """
        Takes text as input and  returns two lists
        1.entity_value in the form of first, middle and last names
        2.original text.
        Args:
           text(string): the original text
           bot_message(string): previous bot message

           Example:
                    text=my name is yash doshi
       Returns:
                [{first_name: "yash", middle_name: None, last_name: "modi"}], [ yash modi"]
        """
        if bot_message:
            if not self.context_check_botmessage(bot_message):
                return [], []

        self.text = text
        self.tagged_text = self.text

        entity_value, original_text = ([], [])

        if self.language == ENGLISH_LANG:
            entity_value, original_text = self.detect_english_name()
        elif self.language == HINDI_LANG:
            entity_value, original_text = self.detect_hindi_name()

        self._update_processed_text(person_name_list=original_text)

        return entity_value, original_text

    def detect_english_name(self, text=None):
        """
        This method is used to detect English names from the provided text
        Returns:
            detect_text_lists (tuple): two dimensional tuple
            1. entity_value (list): representing the entity values of names
            2. original_text (list): representing the original text detected

        Example:

            text=my name is yash doshi
            detect_entity_english()
            >>[{first_name: "yash", middle_name: None, last_name: "modi"}], [ yash modi"]
        """
        if text is None:
            text = self.text
        entity_value, original_text = self.get_name_using_pos_tagger(text)
        if not entity_value:
            text_detection_result = self.text_detection_name(text)
            replaced_text = self.replace_detected_text(text_detection_result, text=text)
            entity_value, original_text = self.detect_person_name_entity(replaced_text)

        return entity_value, original_text

    def detect_hindi_name(self):
        """
        This method is used to detect Hindi names from the provided text

        Returns:
            detect_text_lists (tuple): two dimensional tuple
            1. entity_value (list): representing the entity values of names
            2. original_text (list): representing the original text detected

        Examples:
            text = u'प्रतिक श्रीदत्त जयराओ'
            detect_entity_hindi(text=text)
            >> [{first_name: u"प्रतिक", middle_name: u"श्रीदत्त", last_name: u"जयराओ"}], [ u'प्रतिक श्रीदत्त जयराओ']

        """
        if self.detect_abusive_phrases_hindi(text=self.text) or self.detect_question_hindi(text=self.text):
            return [], []

        text = self.remove_emojis(text=self.text)
        text_before_hindi_regex_operations = text
        regex = re.compile(ur'[^\u0900-\u097F\s]+', re.U)
        text = regex.sub(string=text, repl='')

        regex_detection_result = self.get_hindi_names_from_regex(text=text)
        replaced_text = self.replace_detected_text(regex_detection_result, text=text)
        entity_value, original_text = self.detect_person_name_entity(replaced_text)

        if not entity_value:
            entity_value, original_text = self.get_hindi_names_without_regex(text=text)
        # Further check for name, if it might have been written in latin script.
        if not entity_value:
            english_present_regex = re.compile(ur'[a-zA-Z\s]+', re.U)
            if english_present_regex.search(text_before_hindi_regex_operations):
                remove_everything_except_english = re.compile(ur'[^a-zA-Z\s]+', re.U)
                text_only_english = remove_everything_except_english.sub(
                    string=text_before_hindi_regex_operations, repl='')
                entity_value, original_text = self.detect_english_name(text=text_only_english.strip())

        return entity_value, original_text

    def replace_detected_text(self, text_detection_result, text):
        """
        Replaces the detected name from text_detection_result by _<name>_
        Args:
            text_detection_result: tuple of detected names from TextDetection
            consisting of two lists
            1.The variants detected
            2.The original text
            ([u'dosh', u'yash'], ['doshi', 'yash'])

            Example:
                    text_detection_result= ([u'dosh', u'yash'], ['doshi', 'yash'])
            Returns:
                    ['my', 'name', 'is', 'yash', 'doshi']

        """
        replaced_text = []
        if self.language == ENGLISH_LANG:
            replaced_text = nltk_tokenizer.tokenize(text.lower())
        elif self.language == HINDI_LANG:
            replaced_text = text.lower().strip().split()

        for detected_original_text in (text_detection_result[1]):
            for j in range(len(replaced_text)):
                replaced_text[j] = replaced_text[j].replace(detected_original_text, "_" + detected_original_text + "_")

        return replaced_text

    def detect_person_name_entity(self, replaced_text):
        """
        Separates the detected names into first, middle and last names.
        Returns in form of two lists entity_value and original_text
        Args:
            replaced_text: text in which names detected from TextDetector are replaced by
        _<name>_
        Example:
                replaced_text = My name is _yash_ _modi_
        Returns:
                [{first_name: "yash", middle_name: None, last_name: "modi"}], [ "yash modi"]
        """

        original_text, entity_value = [], []
        name_list = []
        name_holder = []

        for each in replaced_text:
            if each.startswith('_') and each.endswith('_'):
                name_holder.append(each.replace('_', ''))

            else:
                if name_holder:
                    name_list.append(name_holder)
                    name_holder = []

        if name_holder:
            name_list.append(name_holder)

        for name in name_list:
            name_entity_value, original_text_value = self.get_format_name(name)
            original_text.extend(original_text_value)
            entity_value.extend(name_entity_value)

        return entity_value, original_text

    def context_check_botmessage(self, botmessage):
        """
        Checks if previous botmessage conatins name as a keyword or not
        Args:
            botmessage: it consists of the previous botmessage

        Example: what is your name ?

        Returns:
            True
        """

        regex_pattern = re.compile(r'[{}]+'.format(re.escape(string.punctuation)))
        botmessage = regex_pattern.sub(r'', botmessage)

        botmessage = " " + botmessage.lower().strip() + " "
        for variant in NAME_VARIATIONS:
            if " " + variant + " " in botmessage:
                return True
        return False

    def get_hindi_names_from_regex(self, text):
        """
        This method is used to detect hindi names which obey the regexes
        Args:
            text (str): text from which hindi names obeying the regex have to be extracted

        Returns:
            detect_text_lists (tuple): two dimensional tuple
            1. text_list (list): representing the detected text
            2. text_list (list): representing the original text

        Examples:
            text = u'मेरा नाम प्रतिक श्रीदत्त जयराओ है'
            get_hindi_text_from_regex(text=text)
            >>([u'प्रतिक', u'श्रीदत्त', u'जयराओ'], [u'प्रतिक', u'श्रीदत्त', u'जयराओ'])

        """
        text_list = self.get_hindi_text_from_regex(text=text)

        detected_names = []
        if text_list:
            for each in text_list:
                if each:
                    detected_names.extend(each.split())

        text_list = detected_names
        return text_list, text_list

    def get_hindi_names_without_regex(self, text):
        """
        This method is used to get detect hindi names without any regex pattern (This method is called only if
        detection from regex patterns fails)
        This method removes common hindi words ocurring in context of name and hindi stop words
        COMMON_HINDI_WORDS_OCCURING_WITH_NAME set of hindi words ocurring in context of name
        Args:
            text (str): the text from which hindi text has to be detected
        Returns:
            person_name (tuple): two dimensional tuple
            1. entity_value (list): representing the entity values of names
            2. original_text (list): representing the original text detected
        Example:
            text = u'प्रतिक श्रीदत्त जयराओ'
            get_hindi_names_without_regex(text=text)
            >> [{first_name: u"प्रतिक", middle_name: u"श्रीदत्त", last_name: u"जयराओ"}], [ u'प्रतिक श्रीदत्त जयराओ']
        """
        text = self.replace_stopwords_hindi(text)
        text = " ".join([word for word in text.split(" ") if word not in COMMON_HINDI_WORDS_OCCURING_WITH_NAME])
        if not text.strip():
            return [], []
        original_text_list = text.strip().split()
        if len(original_text_list) > 4:
            original_text_list = []
        replaced_text = self.replace_detected_text((original_text_list, original_text_list), text=text)
        return self.detect_person_name_entity(replaced_text=replaced_text)

    def get_hindi_text_from_regex(self, text):
        """
        This method is used to detect hindi names using regexes from the given text
        Args:
            text (str): text from which hindi names which follow the regex pattern have to be extracted

        Returns:
            pattern_match (list): list consisting of detected words

        Examples:
            text = u'मेरा नाम प्रतिक श्रीदत्त जयराओ है'
            get_hindi_text_from_regex(text=text)
            >>[u'प्रतिक श्रीदत्त जयराओ']

        """
        regex_list = [ur"(?:मुझे|हमें|मुझको|हमको|हमे)\s+(?:लोग)\s+([\u0900-\u097F\s]+)"
                      ur"\s+(?:नाम\sसे)\s+(?:कहते|बुलाते|बुलाओ)",
                      ur"(?:नाम|मैं|हम|मै)\s+([\u0900-\u097F\s]+)",
                      ur"(?:मुझे|हमें|मुझको|हमको|हमे)\s+([\u0900-\u097F\s]+)(?:कहते|बुलाते|बुलाओ)",
                      ur"\s*([\u0900-\u097F\s]+)(?:मुझे|मैं|मै)(?:कहते|बुलाते|बुलाओ)?"
                      ]

        for regex in regex_list:
            regex_ = re.compile(regex, re.U)
            pattern_match = regex_.findall(text)
            pattern_match = [self.replace_stopwords_hindi(x) for x in pattern_match if x]
            if pattern_match:
                if pattern_match[0]:
                    return pattern_match

        return None

    def replace_stopwords_hindi(self, text):
        """
        This method is used to replace hindi stop words from the text
        Args:
            text (str): The text from which hindi stop words have to be removed

        Returns:
            clean_text (str): text from which hindi stop words have been removed
        """
        split_list = text.split(" ")
        split_list = [word for word in split_list if word not in HINDI_STOPWORDS]
        if split_list:
            return " ".join(split_list)

        return ""

    def detect_abusive_phrases_hindi(self, text):
        """
        This method is used to check for hindi abuses in the sentence
        Args:
            text (str): text in which abuses have to be checked

        Returns:
            status (bool): returns if the text consists of abuses
        """
        text = ' ' + text + ' '
        for abuse in HINDI_BADWORDS:
            if ' ' + abuse + ' ' in text:
                return True
        return False

    def remove_emojis(self, text):
        """
        This method is used to remove emojis from the given text
        Args:
            text (str): the text from which the emojis have to be removed
        Returns:
            text (str): text with emojis replaced with ''
        """
        emoji_pattern = re.compile(ur'[{0}]+'.format(''.join(EMOJI_RANGES.values())), re.UNICODE)
        text = emoji_pattern.sub(repl='', string=text)
        return text

    def detect_question_hindi(self, text):
        """
        This method is used to detect if the given text has a hindi question present in it
        Args:
            text (str): the text for which the question check has to be run

        Returns:
            status (bool): returns if the text has a question in it
        """
        for word in text.split():
            if word in HINDI_QUESTIONWORDS:
                return True
        return False

    def _update_processed_text(self, person_name_list):
        """
        Replaces detected date with tag generated from entity_name used to initialize the object with

        A final string with all dates replaced will be stored in object's tagged_text attribute
        A string with all dates removed will be stored in object's processed_text attribute

        Args:
            person_name_list (list): list of substrings of original text to be replaced with tag
                                       created from entity_name
        """
        for detected_text in person_name_list:
            self.tagged_text = self.tagged_text.replace(detected_text, self.tag)
            self.processed_text = self.processed_text.replace(detected_text, '')
