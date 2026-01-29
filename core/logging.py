# SPDX-FileCopyrightText: 2024 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""console logging. this is old code that has never been tuned well."""

from functools import wraps

from mathutils import Quaternion, Vector

suppress_section_headings = False
suppress_trace_values = False


# --------------------------------------------------------------------------------------------------
# dump the number of psk records to the console for debugging
debug_dump = dict(
    points=0,
    wedges=0,
    faces=0,
    materials=0,
    bones=0,
    weights=0,
    extrauvs=0,
)


# --------------------------------------------------------------------------------------------------
class SectionHeader:
    """prints nested indented function names for trace logging."""

    current_level: int = 0
    indent_step: int = 2
    indent_string: str = " "
    print_header: bool = True
    print_leading_line: bool = False
    current_header: str = ""

    def __init__(self, print_leading_line: bool = False, print_header: bool = True):
        self.print_leading_line = print_leading_line
        self.print_header = print_header

    # ----------------------------------------------------------------------------------------------
    def __call__(self, func, *args, **kwargs):
        @wraps(func)
        def wrapper(*args, **kwargs):
            indent = SectionHeader.indent_string * SectionHeader.current_level

            if self.print_leading_line:
                print(indent)
            if self.print_header:
                print(f"{indent}{func.__name__}")

            SectionHeader.current_level += SectionHeader.indent_step
            ret = func(*args, **kwargs)
            SectionHeader.current_level -= SectionHeader.indent_step

            return ret

        return wrapper

    # ----------------------------------------------------------------------------------------------
    @staticmethod
    def get_indent(indent_step: int):
        """return the current indent level times the indent_step."""

        return SectionHeader.indent_string * (
            SectionHeader.current_level + SectionHeader.indent_step * indent_step
        )


# --------------------------------------------------------------------------------------------------
class Echo:
    """message logger that uses the SectionHeader for indention depth."""

    prefix: str = ""
    indent_step: int = 1
    width: int = 20
    messages: list[str] = []
    capture_messages: bool = False

    # ----------------------------------------------------------------------------------------------
    def message(
        self,
        message: str = "",
        indent_step: int = 0,
        use_indent: bool = True,
        leading_line: bool = False,
    ):
        """output a message."""

        if use_indent:
            indent_string = SectionHeader.get_indent(indent_step=indent_step + self.indent_step)
        else:
            indent_string = ""
        message_out = f"{Echo.prefix}{indent_string}{message}"

        if Echo.capture_messages:
            self.messages.append(message_out)
        else:
            if leading_line:
                print()
            print(message_out)

    # ----------------------------------------------------------------------------------------------
    def value(
        self,
        message: str = "",
        value: str = "",
        padding_character: str = ".",
        width: int = 0,
        indent_step: int = -1,
        use_indent: bool = True,
        trailing_line: bool = False,
        align_padding: bool = False,
    ):
        """output a padded message and value pair."""

        if width is None:
            width = self.width

        if message == "":
            message = repr(value)

        if align_padding:
            width = width - SectionHeader.current_level
            width = 0 if width < 0 else width
            indent_string = SectionHeader.get_indent(indent_step=indent_step + indent_step)
            value = f"{indent_string}{value}"

        self.message(
            f"{message:{padding_character}<{width}}: {value}",
            indent_step=indent_step,
            use_indent=use_indent,
        )

        if trailing_line:
            self.message()

    # ----------------------------------------------------------------------------------------------
    def values(
        self,
        values: list,
        message: str,
        padding_character: str,
        width: int,
        indent_step: int,
        use_indent: bool,
        trailing_line: bool,
        align_padding: bool,
    ):
        """output a list of padded messages and value pairs."""
        for value in values:
            self.value(
                message=message,
                value=value,
                padding_character=padding_character,
                width=width,
                indent_step=indent_step,
                use_indent=use_indent,
                trailing_line=trailing_line,
                align_padding=align_padding,
            )

    # ----------------------------------------------------------------------------------------------
    def items(self, items, width: int = 30, indent_step: int = 1):
        """prototype recursive method to echo a nested data structure."""

        # ------------------------------------------------------------------------------------------
        # check for containers (list, dict, etc.)
        def is_container(item, key=None):
            if hasattr(item, "__dict__"):
                name = f"<{item.__class__.__name__}>"
                key = None
            elif isinstance(item, dict):
                if not key:
                    # keyless dict inside of a list
                    name = "{dict}"
                else:
                    name = f"{{{key}}}"
                    key = None
            elif isinstance(item, list):
                if len(item) == 0:
                    name = "[empty list]"
                else:
                    name = f"[{key}]"
                    key = None
            elif isinstance(item, tuple):
                if len(item) == 0:
                    name = "[empty tuple]"
                else:
                    name = "[tuple]"
            else:
                return False

            if key:
                return f"{name}: {key}"
            else:
                return f"{name}"

        # ------------------------------------------------------------------------------------------
        # non-basic types are set to strings prefixed with the type
        # if there is a key, use the key, value message
        def echo_basic_type(value, key=None):
            if isinstance(value, float):
                value = f"{round(value, 8):22.16f}"
            elif not isinstance(value, (str, int, bool, Vector, Quaternion, type(None))):
                value = f"{type(value)}: {str(value)}"

            if key:
                self.value(message=key, value=value, width=width, indent_step=0)
            else:
                self.message(value)

        # ------------------------------------------------------------------------------------------
        # class: do not include dunder methods, class methods or static methods
        if hasattr(items, "__dict__"):
            # NOTE: dictionary comprehension with keys and values
            class_items = {
                k: v
                for k, v in items.__dict__.items()
                if not k.startswith("__") and not isinstance(v, (classmethod, staticmethod))
            }

            Echo.items(self, class_items, width=width)

        # ------------------------------------------------------------------------------------------
        # dicts
        elif isinstance(items, dict):
            for key, value in items.items():
                if header := is_container(item=value, key=key):
                    self.message(header)

                    self.indent_step += 1
                    Echo.items(self, value, width=width)
                    self.indent_step -= 1

                else:
                    echo_basic_type(value=value, key=key)

        # ------------------------------------------------------------------------------------------
        # lists and tuples
        elif isinstance(items, (list, tuple)):
            if len(items) > 0:
                for item in items:
                    # containers
                    # NOTE: not sure if this is ever true
                    if header := is_container(item=item):
                        self.message(header)

                        self.indent_step += 1
                        Echo.items(self, item, width=width)
                        self.indent_step -= 1

                    else:
                        echo_basic_type(value=item)

        # ------------------------------------------------------------------------------------------
        # echo all other types as basic
        else:
            echo_basic_type(f"items: {items}")

        self.capture_messages = False
