import logging

from .constant import Constant

logger = logging.getLogger(__name__)


class Log():

    @staticmethod
    def debug(log_msg):
        logger.debug(log_msg)

    @staticmethod
    def error(log_msg):
        logger.error(log_msg)
        print("ERROR: {}".format(log_msg))

    @staticmethod
    def info(log_msg):
        logger.info(log_msg)
        if Constant.VERBOSE:
            print("INFO: {}".format(log_msg))

    @staticmethod
    def warning(log_msg):
        logger.warning(log_msg)
        print("WARNING: {}".format(log_msg))
