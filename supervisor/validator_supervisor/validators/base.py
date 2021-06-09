from abc import ABC

from ..subprocess import SimpleSubprocess


class ValidatorRunner(SimpleSubprocess, ABC):
    def __init__(
            self,
            eth2_network: str,
            datadir: str,
            out_log_filepath: str,
            err_log_filepath: str,
    ):
        super().__init__(out_log_filepath, err_log_filepath)
        self.eth2_network = eth2_network
        self.datadir = datadir
