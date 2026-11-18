"""Placeholders keep names and phone numbers out of AI tracing (ADR-0002)."""

import json

from shared.observability.ai_tracing.placeholders import Placeholders


def test_names_and_phone_numbers_are_replaced():
    placeholders = Placeholders(["Anna"])

    assert placeholders.apply("Call Anna on +46 70 123 45 67") == (
        "Call <NAME_1> on <PHONE_1>"
    )


def test_the_same_name_keeps_its_placeholder_across_input_and_output():
    placeholders = Placeholders(["Anna", "Erik"])

    placeholders.apply("Erik met Anna")

    assert placeholders.apply("anna left") == "<NAME_2> left"


def test_the_longest_name_wins():
    placeholders = Placeholders(["Anna", "Anna-Lisa"])

    assert placeholders.apply("Anna-Lisa and Anna") == "<NAME_1> and <NAME_2>"


def test_names_inside_a_json_document_are_replaced_after_unescaping():
    placeholders = Placeholders(["Jöns"])

    document = placeholders.apply_json(json.dumps({"people": ["Jöns"]}))

    assert json.loads(document) == {"people": ["<NAME_1>"]}


def test_a_document_that_isnt_json_is_treated_as_text():
    placeholders = Placeholders(["Anna"])

    assert placeholders.apply_json("Anna said hi") == "<NAME_1> said hi"
