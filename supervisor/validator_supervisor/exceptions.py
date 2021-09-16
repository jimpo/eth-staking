class MissingValidatorData(Exception):
    pass


class UnlockRequired(Exception):
    pass


class InvalidSSHPubkey(Exception):
    pass


class ValidatorRunning(Exception):
    pass


class DockerBuildException(Exception):
    pass


class BadValidatorRelease(Exception):
    pass
