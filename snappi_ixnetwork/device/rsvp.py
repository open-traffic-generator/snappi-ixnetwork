from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Rsvp(Base):
    def __init__(self, ngpf):
        super(Rsvp, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)

    def config(self, device):
        self.logger.debug("Configuring RSVP")
        rsvp = device.get("rsvp")
        if rsvp is None:
            return