import abc


class DnsProvider(object):
    __metaclass__ = abc.ABCMeta

    """Add type A record to dns provider service.
        Args:
            fqdn (str): Fully qualified domain name.
            ip (str): Pointer ip address.
            ttl (Optional[int]): Record TTL value. Default 360
    """

    @abc.abstractmethod
    def add_record(self, fqdn, ip, ttl=360):
        pass

    """Remove type A record to dns provider service.
        Args:
            fqdn (str): Fully qualified domain name.
    """

    @abc.abstractmethod
    def remove_record(self, fqdn):
        pass
