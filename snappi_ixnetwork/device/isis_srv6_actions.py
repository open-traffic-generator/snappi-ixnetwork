import ipaddress
import time

from snappi_ixnetwork.logger import get_ixnet_logger


class IsisSRv6Actions(object):
    """Handles ISIS SRv6 My Local SID lifecycle actions (add/modify/delete).

    Maps snappi ActionProtocolIsisSrv6MyLocalSid operations to IxNetwork
    isisSRv6EndSIDList manipulations under isisSRv6LocatorEntryList.

    IxNetwork does not allow modifying isisSRv6EndSIDList properties while
    the protocol is running ("Changing the property in a started element is
    not permitted"). The workaround is to stop the ISIS protocol on the
    affected device group, make the changes, then restart it.
    """

    # Map behavior strings to IANA SRv6 Endpoint Behavior code points
    _BEHAVIOR_MAP = {
        "u_n":       1,    # uN (End, micro-SID node)
        "u_dt4":     18,   # uDT4 (End.DT4)
        "u_dt6":     17,   # uDT6 (End.DT6)
        "u_dt46":    19,   # uDT46 (End.DT46)
        "u_dx4":     16,   # uDX4 (End.DX4)
        "u_dx6":     15,   # uDX6 (End.DX6)
        "end":       1,    # End
        "end_dt4":   18,   # End.DT4
        "end_dt6":   17,   # End.DT6
        "end_dt46":  19,   # End.DT46
    }

    def __init__(self, api):
        self._api = api
        self.logger = get_ixnet_logger(__name__)

    def handle_my_local_sid(self, my_local_sid):
        """Entry point for My Local SID action.

        Args:
            my_local_sid: ActionProtocolIsisSrv6MyLocalSid object with
                          router_names and choice (add/modify/delete).
        """
        self._api._connect()
        router_names = my_local_sid.get("router_names") or []
        choice = my_local_sid.get("choice")
        if choice == "add":
            entries = my_local_sid.add.get("entries")
            self._add_my_local_sids(router_names, entries)
        elif choice == "modify":
            entries = my_local_sid.modify.get("entries")
            self._modify_my_local_sids(router_names, entries)
        elif choice == "delete":
            sid_refs = my_local_sid.delete.get("sid_refs")
            self._delete_my_local_sids(router_names, sid_refs)

    def _get_isis_interfaces(self, router_names):
        """Find isisL3 interface objects for the given router names.

        Returns list of (device_group, isis_l3_interface, isis_router) tuples.
        """
        results = []
        topos = self._api._ixnetwork.Topology.find()
        for topo in topos:
            for dg in topo.DeviceGroup.find():
                eth_list = dg.Ethernet.find()
                for eth in eth_list:
                    isis_list = eth.IsisL3.find()
                    for isis_intf in isis_list:
                        # Check if this device group has a matching router
                        isis_routers = dg.IsisL3Router.find()
                        for router in isis_routers:
                            if not router_names or router.Name in router_names:
                                results.append((dg, isis_intf, router))
        return results

    def _stop_isis_protocol(self, isis_intf):
        """Stop ISIS protocol on the given interface."""
        self.logger.debug("Stopping ISIS protocol for modification")
        isis_intf.Stop()
        # Wait for protocol to stop
        for _ in range(30):
            isis_intf.refresh()
            status = isis_intf.SessionStatus
            if all(s == "down" or s == "notStarted" for s in status):
                break
            time.sleep(1)

    def _start_isis_protocol(self, isis_intf):
        """Start ISIS protocol on the given interface."""
        self.logger.debug("Starting ISIS protocol after modification")
        isis_intf.Start()
        # Wait for protocol session to come up
        for _ in range(60):
            isis_intf.refresh()
            status = isis_intf.SessionStatus
            if status and all(s == "up" for s in status):
                break
            time.sleep(1)

    def _add_my_local_sids(self, router_names, entries):
        """Add new End SID entries to the locator's End SID list."""
        if not entries or len(entries) == 0:
            return
        self.logger.debug("Adding %d My Local SID entries" % len(entries))
        targets = self._get_isis_interfaces(router_names)
        for dg, isis_intf, router in targets:
            locator_list = router.IsisSRv6LocatorEntryList
            if locator_list is None:
                continue
            # Read current locator info before stopping
            locator_prefix = self._get_multivalue_single(
                locator_list, "Locator"
            )
            if locator_prefix is None:
                continue
            # Stop protocol to allow modifications
            self._stop_isis_protocol(isis_intf)
            try:
                # Get existing End SID list
                end_sid_list = locator_list.IsisSRv6EndSIDList
                current_count = locator_list.SidCount
                new_count = current_count + len(entries)
                # Update SidCount to accommodate new entries
                locator_list.update(SidCount=new_count)
                # Refresh end_sid_list after count change
                end_sid_list = locator_list.IsisSRv6EndSIDList
                # Read current SID values
                current_sids = list(end_sid_list.Sid.Values)
                current_eps = list(end_sid_list.EndPointFunction.Values)
                current_cflags = list(end_sid_list.CFlag.Values)
                # Build new values
                new_sids = list(current_sids)
                new_eps = list(current_eps)
                new_cflags = list(current_cflags)
                for entry in entries:
                    sid_prefix = entry.get("sid_prefix")
                    behavior = entry.get("behavior") or "u_n"
                    ep_code = self._BEHAVIOR_MAP.get(behavior, 1)
                    new_sids.append(sid_prefix)
                    new_eps.append(str(ep_code))
                    new_cflags.append("false")
                # Apply updated values
                end_sid_list.Sid.ValueList(new_sids)
                end_sid_list.EndPointFunction.ValueList(new_eps)
                end_sid_list.CFlag.ValueList(new_cflags)
            finally:
                # Restart protocol
                self._start_isis_protocol(isis_intf)

    def _modify_my_local_sids(self, router_names, entries):
        """Modify existing End SID entries matched by sid_prefix."""
        if not entries or len(entries) == 0:
            return
        self.logger.debug("Modifying %d My Local SID entries" % len(entries))
        targets = self._get_isis_interfaces(router_names)
        for dg, isis_intf, router in targets:
            locator_list = router.IsisSRv6LocatorEntryList
            if locator_list is None:
                continue
            end_sid_list = locator_list.IsisSRv6EndSIDList
            current_sids = list(end_sid_list.Sid.Values)
            current_eps = list(end_sid_list.EndPointFunction.Values)
            modified = False
            for entry in entries:
                sid_prefix = entry.get("sid_prefix")
                behavior = entry.get("behavior")
                # Match by SID prefix (normalized IPv6 comparison)
                for idx, existing_sid in enumerate(current_sids):
                    if self._ipv6_equal(existing_sid, sid_prefix):
                        if behavior is not None:
                            ep_code = self._BEHAVIOR_MAP.get(behavior, 1)
                            current_eps[idx] = str(ep_code)
                            modified = True
                        break
            if not modified:
                continue
            # Stop protocol to allow modifications
            self._stop_isis_protocol(isis_intf)
            try:
                end_sid_list.EndPointFunction.ValueList(current_eps)
            finally:
                # Restart protocol
                self._start_isis_protocol(isis_intf)

    def _delete_my_local_sids(self, router_names, sid_refs):
        """Delete End SID entries matched by sid_prefix + prefix_length."""
        if not sid_refs or len(sid_refs) == 0:
            return
        self.logger.debug("Deleting %d My Local SID entries" % len(sid_refs))
        # Build lookup set of SIDs to delete
        delete_set = set()
        for ref in sid_refs:
            sid_prefix = ref.get("sid_prefix")
            if sid_prefix:
                try:
                    normalized = str(
                        ipaddress.IPv6Address(sid_prefix)
                    )
                    delete_set.add(normalized)
                except ValueError:
                    delete_set.add(sid_prefix)
        targets = self._get_isis_interfaces(router_names)
        for dg, isis_intf, router in targets:
            locator_list = router.IsisSRv6LocatorEntryList
            if locator_list is None:
                continue
            end_sid_list = locator_list.IsisSRv6EndSIDList
            current_sids = list(end_sid_list.Sid.Values)
            current_eps = list(end_sid_list.EndPointFunction.Values)
            current_cflags = list(end_sid_list.CFlag.Values)
            # Filter out entries to delete
            new_sids = []
            new_eps = []
            new_cflags = []
            for idx, sid in enumerate(current_sids):
                try:
                    normalized = str(ipaddress.IPv6Address(sid))
                except ValueError:
                    normalized = sid
                if normalized not in delete_set:
                    new_sids.append(sid)
                    new_eps.append(current_eps[idx])
                    new_cflags.append(current_cflags[idx])
            new_count = len(new_sids)
            if new_count == len(current_sids):
                continue  # Nothing to delete for this router
            # Stop protocol to allow modifications
            self._stop_isis_protocol(isis_intf)
            try:
                # Update count and values
                locator_list.update(SidCount=max(new_count, 1))
                end_sid_list = locator_list.IsisSRv6EndSIDList
                if new_count > 0:
                    end_sid_list.Sid.ValueList(new_sids)
                    end_sid_list.EndPointFunction.ValueList(new_eps)
                    end_sid_list.CFlag.ValueList(new_cflags)
                else:
                    # Deactivate if we can't go to 0
                    end_sid_list.Active.Single("false")
            finally:
                # Restart protocol
                self._start_isis_protocol(isis_intf)

    def _get_multivalue_single(self, obj, attr_name):
        """Get the first value of a multivalue attribute."""
        try:
            mv = getattr(obj, attr_name)
            values = mv.Values
            if values and len(values) > 0:
                return values[0]
        except Exception:
            pass
        return None

    def _ipv6_equal(self, addr1, addr2):
        """Compare two IPv6 addresses after normalization."""
        try:
            return (
                ipaddress.IPv6Address(addr1)
                == ipaddress.IPv6Address(addr2)
            )
        except (ValueError, TypeError):
            return addr1 == addr2
