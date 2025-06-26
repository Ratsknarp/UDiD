from enum import Enum


class ImportAccountStates(Enum):
    KEY_ID = 1
    ISSUE_ID = 2
    P8_FILE = 3

class RegisterUDIDStates(Enum):
    REGISTER = 1

class CheckUDIDStates(Enum):
    UDID = 1

class GenerateKeyStates(Enum):
    NO_OF_KEYS = 1

class EnableDisableUDID(Enum):
    UDID_PROMPT = 1