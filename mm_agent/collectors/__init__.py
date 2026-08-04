from .ad import ADCollector
from .gpo import GPOCollector
from .firewall_palo_alto import PaloAltoCollector
from .firewall_fortinet import FortinetCollector
from .endpoint_intune import IntuneCollector

registry = {
    "ad": ADCollector,
    "gpo": GPOCollector,
    "firewall_palo_alto": PaloAltoCollector,
    "firewall_fortinet": FortinetCollector,
    "endpoint_intune": IntuneCollector,
}
