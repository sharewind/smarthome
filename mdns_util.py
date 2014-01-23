"""
mdns_util

Provides a class to wrap pybonjour functionality and references to work
with Tornado's IOLoop for event handling.

    Sample usage:
    >>> from mdns_util import MDNS
    >>> from tornado.ioloop import IOLoop
...
    >>> ioloop = IOLoop.instance()
    >>> mdns = MDNS(ioloop)
    >>> mdns.register('My HTTP Service', '_http._tcp', 8080)
...
    >>> ioloop.start()

"""

from pybonjour import (
    kDNSServiceFlagsAdd,
    DNSServiceProcessResult as process_result,
    DNSServiceBrowse as browse_dns_services,
    DNSServiceResolve as resolve_dns_service,
    DNSServiceRegister as register_dns_service
)

class MDNS(object):
    """
    A utility class for working with pybonjour and tornado.

    MDNS accepts an IOLoop instance, and uses it to handle events for
    `pybonjour.DNSServiceRef` objects

    """

    def __init__(self, ioloop):
        self._ioloop = ioloop
        self._broadcast_refs = {}
        self._discovery_refs = {}
        self._resolution_refs = {}

    def _handle_ref(self, ref):
        """Create a handler for a `pybonjour.DNSServiceRef` instance."""
        self._ioloop.add_handler(
            ref.fileno(),
            lambda fd, events: process_result(ref),
            self._ioloop.READ
        )

    def _close_ref(self, ref):
        """
        Close a DNSServiceRef file descriptor; remove ioloop event handler.
        """

        self._ioloop.remove_handler(ref.fileno())
        ref.close()

    def register(self, name, regtype, domain, port, **kwargs):
        """
        Broadcast a service to the network.
        """

        ref_key = name + regtype + domain + str(port)
        ref = register_dns_service(
            name=name,
            regtype=regtype,
            domain=domain,
            port=port,
            **kwargs)

        self._handle_ref(ref)
        self._broadcast_refs[ref_key] = ref

    def unregister(self, name, regtype, domain, port):
        """
        Stop broadcasting the existence of a service.
        """

        ref_key = name + regtype + domain + str(port)
        ref = self._broadcast_refs.get(ref_key, None)
        if not ref:
            return

        del self._broadcast_refs[ref_key]
        self._close_ref(ref)

    def discover(self, regtype, on_discovered, on_lost):
        """
        Notify listener when a service is found/lost.
        """
        
        if regtype in self._discovery_refs:
            return
        resolution_refs = self._resolution_refs[regtype] = []
        
        def browse_callback(ref, flags, index, error, name, regtype, domain):

            def resolve_callback(ref, flags, index, error, fullname, host,
                                 port, txtRecord):
                """
                Handle pybonjour results for resolution of `regtype` services.
                """
                on_discovered(index, name, fullname, host, port, txtRecord)
                resolution_refs.remove(ref)
                self._close_ref(ref)
            #end resove_callback


            """
            Handle pybonjour results for `regtype` services.
            """
            if flags & kDNSServiceFlagsAdd:
                resolution_ref = resolve_dns_service(0, index, name, regtype, domain, resolve_callback)
                resolution_refs.append(resolution_ref)
                self._handle_ref(resolution_ref)
            else:
                on_lost(index, name, regtype, domain)
                if ref in resolution_refs:
                    resolution_refs.remove(ref)
                    self._close_ref(ref)

        browse_ref = browse_dns_services(
            regtype=regtype,
            callBack=browse_callback
        )

        self._handle_ref(browse_ref)
        self._discovery_refs[regtype] = browse_ref

    def end_discovery(self, regtype):
        """
        Stop looking for services of the given regtype and close handlers.
        """

        if regtype not in self._discovery_refs:
            return

        self._close_ref(self._discovery_refs[regtype])
        [self._close_ref(r) for r in self._resolution_refs[regtype]]
        del self._discovery_refs[regtype]
        del self._resolution_refs[regtype]
