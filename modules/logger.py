import logging, sys

class Log:
    def __init__(self, filename: str, directory: str = '') -> None:
        self.logger = logging.getLogger(filename)
        self.logger.setLevel(logging.DEBUG)

        # Create handlers
        console = logging.StreamHandler(sys.stdout)
        file = logging.FileHandler(f'{directory}/{filename}.txt', 'w')

        # Set logger level
        console.setLevel(logging.DEBUG)
        file.setLevel(logging.DEBUG)

        # Create formatters and add to handler
        console.setFormatter(logging.Formatter('%(message)s'))
        file.setFormatter(logging.Formatter('%(message)s'))

        # Add to handlers
        self.logger.addHandler(console)
        self.logger.addHandler(file)

    def header(self, message):
        self.info(f'\n==================== {message}')

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)
