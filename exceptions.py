
class ApiServiceError(Exception):
    """Bot cannot get current weather"""


class WrongInput(Exception):
    """Bot could not find the city. Check the spelling"""
