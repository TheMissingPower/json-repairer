from contract import RULES

from .checks import bundled, result


def verify_input(value):
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.case_id != input_value.case_id:
        return result(False, f"the output is case {output_value.case_id.value}, not {input_value.case_id.value}")
    broken, _ = bundled(input_value.case_id)
    if output_value.broken_json != broken:
        return result(False, f"the broken text is not case {input_value.case_id.value}'s")
    if output_value.rules != RULES:
        return result(False, "the rules are not the task's rules")
    return result(True, "the case is the bundled one")
