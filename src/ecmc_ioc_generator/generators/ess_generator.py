"""ESS-specific ECMC IOC generator."""

from . import BaseGenerator


class ESSGenerator(BaseGenerator):
    """Generate an ECMC IOC configuration for ESS."""

    facility = "ESS"
    prefix = 'iocshLoad "${ecmccfg_DIR}/'

    def _add_slave_fn(self, hw_desc: str) -> str:
        """Return the addSlave iocshLoad command string for the given slave."""
        # TODO(kivel): This looks wrong to me, needs to be verified
        return self.prefix + 'addSlave.cmd" HW_DESC=' + hw_desc

    def _print_header(self, stream):
        """Print the facility-specific header."""
        print("require essioc", file=stream)
        print("require ecmccfg\n", file=stream)
        print(
            self.prefix + 'startup.cmd" "ECMC_VER=' + self.ecmc_ver + ', NAMING=ESSnaming"\n',
            file=stream,
        )

    def _print_axis_config(self, stream):
        """Print axis configuration templates for motion terminals."""
        # ESS pattern: explicit SDOs via ecmcConfigOrDie
        print(
            '# ecmcConfigOrDie "Cfg.EcAddSdo(${ECMC_EC_SLAVE_NUM},0x8010,0x1,<TODO>,2)"',
            file=stream,
        )
        print(
            '# ecmcConfigOrDie "Cfg.EcAddSdo(${ECMC_EC_SLAVE_NUM},0x8010,0x2,<TODO>,4)"',
            file=stream,
        )
        print(
            '# ecmcConfigOrDie "Cfg.EcAddSdo(${ECMC_EC_SLAVE_NUM},0x8012,0x3A,<TODO>,1)"',
            file=stream,
        )


    def _print_footer(self, stream):
        print("\n" + self.prefix + 'applyConfig.cmd"', file=stream)
        print(self.prefix + 'setAppMode.cmd"', file=stream)
        print("iocInit", file=stream)
