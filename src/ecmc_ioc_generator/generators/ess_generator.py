"""ESS-specific ECMC IOC generator."""

from . import BaseGenerator


class ESSGenerator(BaseGenerator):
    """Generate an ECMC IOC configuration for ESS."""

    facility = "ESS"
    prefix = 'iocshLoad "${ecmccfg_DIR}/'

    def _print_header(self, stream):
        """Print the facility-specific header."""
        print("require essioc", file=stream)
        print("require ecmccfg\n", file=stream)
        print(
            self.prefix + 'startup.cmd" "ECMC_VER=' + self.ecmc_ver + ', NAMING=ESSnaming"\n',
            file=stream,
        )

    def _print_axis_config(self, stream):
        pass

    def _print_footer(self, stream):
        pass

    def _process_slaves(self, stream):
        pass
