"""
tests/test_sms_parser.py — Unit tests for the SMS parsing engine.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sms_parser import parse_sms


# ---------------------------------------------------------------------------
# REGISTER intent
# ---------------------------------------------------------------------------

class TestRegisterIntent:
    def test_basic_register_english(self):
        p = parse_sms("REGISTER Ram Lal Tractor Mechanic Ramnagar")
        assert p.intent == "REGISTER"
        assert p.name == "Ram Lal"
        assert p.skill == "tractor mechanic"
        assert p.location == "Ramnagar"
        assert p.is_valid

    def test_register_hindi_keyword(self):
        p = parse_sms("PANJIYAN Suresh Kumar Plumber Ballia")
        assert p.intent == "REGISTER"
        assert p.name == "Suresh Kumar"
        assert p.skill == "plumber"
        assert p.location == "Ballia"
        assert p.is_valid

    def test_register_hindi_skill_mistri(self):
        p = parse_sms("REGISTER Mohan Mistri Patna")
        assert p.intent == "REGISTER"
        assert p.skill == "mason"
        assert p.is_valid

    def test_register_hindi_mazdoor(self):
        p = parse_sms("REGISTER Santosh Mazdoor Gopalganj")
        assert p.intent == "REGISTER"
        assert p.skill == "labourer"
        assert p.is_valid

    def test_register_missing_location(self):
        p = parse_sms("REGISTER Ram Lal Tractor Mechanic")
        assert p.intent == "REGISTER"
        assert not p.is_valid
        assert any("Location" in e for e in p.errors)

    def test_register_missing_name(self):
        p = parse_sms("REGISTER Tractor Mechanic Ramnagar")
        # Only one name token — ambiguous; parser may produce errors or wrong name
        # Just confirm no crash and intent is REGISTER
        assert p.intent == "REGISTER"

    def test_register_unknown_skill(self):
        p = parse_sms("REGISTER Ram Lal XyzUnknown Ramnagar")
        assert p.intent == "REGISTER"
        assert not p.is_valid

    def test_register_case_insensitive(self):
        p = parse_sms("register ram lal tractor mechanic ramnagar")
        assert p.intent == "REGISTER"
        assert p.is_valid


# ---------------------------------------------------------------------------
# SEARCH intent
# ---------------------------------------------------------------------------

class TestSearchIntent:
    def test_basic_search_english(self):
        p = parse_sms("NEED Tractor Mechanic Ramnagar")
        assert p.intent == "SEARCH"
        assert p.skill == "tractor mechanic"
        assert p.location == "Ramnagar"
        assert p.is_valid

    def test_search_hindi_keyword(self):
        p = parse_sms("CHAHIYE Plumber Patna")
        assert p.intent == "SEARCH"
        assert p.skill == "plumber"
        assert p.location == "Patna"
        assert p.is_valid

    def test_search_no_location(self):
        p = parse_sms("NEED Electrician")
        assert p.intent == "SEARCH"
        assert p.skill == "electrician"
        assert p.location is None
        assert p.is_valid

    def test_search_hindi_skill(self):
        p = parse_sms("NEED Mistri Vaishali")
        assert p.intent == "SEARCH"
        assert p.skill == "mason"
        assert p.is_valid

    def test_search_mazdoor(self):
        p = parse_sms("CHAHIYE Mazdoor")
        assert p.intent == "SEARCH"
        assert p.skill == "labourer"

    def test_search_case_insensitive(self):
        p = parse_sms("need tractor mechanic ballia")
        assert p.intent == "SEARCH"
        assert p.skill == "tractor mechanic"
        assert p.location == "ballia"

    def test_search_keywordless_detection(self):
        """A message with just a skill keyword should be detected as SEARCH."""
        p = parse_sms("Tractor Mechanic")
        assert p.intent == "SEARCH"
        assert p.skill == "tractor mechanic"


# ---------------------------------------------------------------------------
# UNKNOWN intent
# ---------------------------------------------------------------------------

class TestUnknownIntent:
    def test_empty_message(self):
        p = parse_sms("")
        assert p.intent == "UNKNOWN"

    def test_gibberish(self):
        p = parse_sms("hello world xyz")
        assert p.intent == "UNKNOWN"

    def test_whitespace_only(self):
        p = parse_sms("   ")
        assert p.intent == "UNKNOWN"
