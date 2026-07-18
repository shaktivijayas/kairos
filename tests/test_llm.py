from kairos import llm


def test_parse_json_object_passes_through_plain_object():
    assert llm._parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_unwraps_single_element_list():
    assert llm._parse_json_object('[{"a": 1}]') == {"a": 1}


def test_parse_json_object_unwraps_empty_list_to_empty_dict():
    assert llm._parse_json_object("[]") == {}


def test_parse_json_object_uses_first_element_of_multi_element_list():
    assert llm._parse_json_object('[{"a": 1}, {"a": 2}]') == {"a": 1}
