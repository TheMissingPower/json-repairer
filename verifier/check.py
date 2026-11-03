from .checks import result
from .strict_json import check


def verify_input(value):
    if not isinstance(value.text, str):
        return result(False, "check_json takes a text")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    expected = check(input_value.text)
    actual = (output_value.valid, output_value.error, output_value.line, output_value.column)
    if actual != expected:
        return result(False, f"check_json says {list(actual)}, but the text checks as {list(expected)}")
    return result(True, "the text is strict JSON" if expected[0] else f"the text is not strict JSON: {expected[1]}")
