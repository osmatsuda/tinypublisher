import logging

__version__ = "0.3.2"
__appname__ = 'tinypublisher'

# Logger
logger = logging.getLogger(__appname__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(name)s.%(levelname)s: %(message)s')
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


class AppBaseError(Exception):
    pass

