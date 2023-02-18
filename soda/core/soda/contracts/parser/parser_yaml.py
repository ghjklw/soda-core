from __future__ import annotations

import re
from numbers import Number
from typing import Dict, List

from ruamel.yaml import CommentedMap, CommentedSeq

from soda.contracts.parser.parser_log import ParserLogs, ParserLocation


class YamlValue:
    """
    Base class for yaml data structure objects
    """

    def __init__(self, logs: ParserLogs, location: ParserLocation):
        self.logs: ParserLogs = logs
        self.location = location

    def _convert_value(self, ruamel_value: object, logs: ParserLogs, line: int, column: int) -> YamlValue:
        location = ParserLocation(file_path=self.location.file_path, line=line, column=column)
        if isinstance(ruamel_value, str):
            return YamlString(value=ruamel_value, logs=logs, location=location)
        if isinstance(ruamel_value, bool):
            return YamlBoolean(value=ruamel_value, logs=logs, location=location)
        if isinstance(ruamel_value, Number):
            return YamlNumber(value=ruamel_value, logs=logs, location=location)
        if ruamel_value is None:
            return YamlNull(logs=logs, location=location)
        if isinstance(ruamel_value, CommentedMap):
            return YamlObject(ruamel_object=ruamel_value, logs=logs, location=location)
        if isinstance(ruamel_value, CommentedSeq):
            return YamlList(ruamel_list=ruamel_value, logs=logs, location=location)
        logs.error(f"Unsupported Ruamel YAML object type: {type(ruamel_value).__name__}\n{str(ruamel_value)}")


class YamlString(YamlValue):
    def __init__(self, value: str, logs: ParserLogs, location: ParserLocation):
        super().__init__(logs, location)
        self.value: str = value

    @classmethod
    def validate_name(cls, yaml_string: YamlString | None) -> None:
        if yaml_string is not None:
            if '\n' in yaml_string.value or len(yaml_string.value) > 120:
                yaml_string.logs.error(
                    message="Invalid name",
                    location=yaml_string.location,
                    docs_ref="02-data-producer-contract.md#string-types"
                )

    email_regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

    @classmethod
    def validate_email(cls, yaml_string: YamlString | None) -> None:
        if yaml_string is not None:
            if not re.fullmatch(cls.email_regex, yaml_string.value):
                yaml_string.logs.error(
                    message="Invalid email",
                    location=yaml_string.location,
                    docs_ref="02-data-producer-contract.md#string-types"
                )

    id_regex = re.compile(r'[A-Za-z0-9_]+')

    @classmethod
    def validate_id(cls, yaml_string: YamlString | None) -> None:
        if yaml_string is not None:
            if not re.fullmatch(cls.id_regex, yaml_string.value):
                yaml_string.logs.error(
                    message="Invalid id",
                    location=yaml_string.location,
                    docs_ref="02-data-producer-contract.md#string-types"
                )


class YamlNumber(YamlValue):
    def __init__(self, value: Number, logs: ParserLogs, location: ParserLocation):
        super().__init__(logs, location)
        self.value: Number = value


class YamlBoolean(YamlValue):
    def __init__(self, value: bool, logs: ParserLogs, location: ParserLocation):
        super().__init__(logs, location)
        self.value: bool = value


class YamlNull(YamlValue):
    def __init__(self, logs: ParserLogs, location: ParserLocation):
        super().__init__(logs, location)
        self.value: None = None


class YamlObject(YamlValue):
    def __init__(self, ruamel_object: CommentedMap, logs: ParserLogs, location: ParserLocation):
        super().__init__(logs, location)
        self.yaml_dict: Dict[str, YamlValue] = {
            key: self.__convert_map_value(ruamel_object=ruamel_object, key=key, value=value)
            for key, value in ruamel_object.items()
        }

    def __convert_map_value(self, ruamel_object: CommentedMap, key, value) -> YamlValue:
        ruamel_location = ruamel_object.lc.value(key)
        line: int = ruamel_location[0]
        column: int = ruamel_location[1]
        return self._convert_value(ruamel_value=value, logs=self.logs, line=line, column=column)

    def __iter__(self):
        return iter(self.yaml_dict)

    def read_object(self, key: str) -> YamlObject | None:
        """
        An appropriate error log is generated if the value is not a YamlObject or if the key is missing
        :return: a YamlObject if the value for the key is a YamlObject, otherwise None.
        """
        return self.read_value(key=key, expected_type=YamlObject, required=True, default_value=None)

    def read_object_opt(self, key: str) -> YamlObject | None:
        """
        An appropriate error log is generated if the value is not a YamlObject
        :return: a YamlObject if the value for the key is a YamlObject, otherwise None.
        """
        return self.read_value(key=key, expected_type=YamlObject, required=False, default_value=None)

    def read_string_opt(self, key: str, default_value: str | None = None) -> YamlString | None:
        """
        An appropriate error log is generated if the value is not a string
        :return: a YamlString if the value for the key is a YAML string, otherwise None.
        """
        return self.read_value(key=key, expected_type=YamlString, required=False, default_value=default_value)

    def read_string(self, key: str) -> YamlString | None:
        """
        An appropriate error log is generated if the value is not a string or if the key is missing.
        :return: a YamlString if the value for the key is a YAML string, otherwise None.
        """
        return self.read_value(key=key, expected_type=YamlString, required=True)

    def read_value(self,
                   key: str,
                   expected_type: type = None,
                   required: bool = False,
                   default_value=None
                   ) -> YamlValue:
        if key not in self.yaml_dict:
            if required:
                self.logs.error(f"'{key}' is required")
            return default_value
        yaml_value: YamlValue = self.yaml_dict.get(key)
        if not isinstance(yaml_value, expected_type):
            self.logs.error(
                message=f"'{key}' expected a {expected_type.__name__}, but was {type(yaml_value).__name__}",
                location=yaml_value.location
            )
        return yaml_value

    def actual_type_name(self) -> str:
        return "object"


class YamlList(YamlValue):
    def __init__(self, ruamel_list: CommentedSeq, logs: ParserLogs, location: ParserLocation):
        super().__init__(logs, location)
        self.value: List[YamlValue] = [
            self.__convert_array_value(ruamel_value=ruamel_value, commented_seq=ruamel_list, index=index)
            for index, ruamel_value in enumerate(ruamel_list)
        ]

    def __convert_array_value(self, ruamel_value, commented_seq: CommentedSeq, index: int) -> YamlValue:
        ruamel_location = commented_seq.lc.key(index)
        line: int = ruamel_location[0]
        column: int = ruamel_location[1]
        return self._convert_value(ruamel_value, self.logs, line, column)
