#!/usr/bin/env python
######################################################################
#
# Copyright 2012 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import Globals

from zope.component import getUtility

from Products.ZenEvents.events2.proxy import EventSummaryProxy
from Products.ZenModel.interfaces import IAction
from Products.ZenUtils.CyclingDaemon import CyclingDaemon
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.guid.guid import GUIDManager
from Products.Zuul import getFacade
from zenoss.protocols.jsonformat import from_dict
from zenoss.protocols.protobufs.zep_pb2 import (EventSummary,
                                                STATUS_NEW,
                                                STATUS_ACKNOWLEDGED)

from datetime import *

unused(Globals)


DAEMON = "zeneventenrichment"


class zeneventenrichment(CyclingDaemon):
    name = DAEMON

    def __init__(self, *args, **kwargs):
        super(zeneventenrichment, self).__init__(*args, **kwargs)

        self.zep = getFacade("zep")
        self.guidManager = GUIDManager(self.dmd)

        # Filter for events with sn_sysid
        self.incidentEventsFilter = self.zep.createEventFilter(
            status=[STATUS_NEW, STATUS_ACKNOWLEDGED],
            details={'zenpack.community.eventenrichment.expireSet':1})

    def main_loop(self):
        """
        Loop through all open events with incidents and close them
        if their incidents are closed.
        """

        uuidsToClose = []
        eventSummaries = self.zep.getEventSummariesGenerator(
            self.incidentEventsFilter)

        for zepEventSummary in eventSummaries:
            eventSummary = from_dict(EventSummary, zepEventSummary)
            event = EventSummaryProxy(eventSummary)
            self.log.debug("Checking if event %s is older than %s seconds",
                event.evid, event.details.get("zenpack.community.eventenrichment.expireTime"))

	    delta=datetime.now()-datetime.strptime(event.lastTime,'%Y/%m/%d %H:%M:%S.%f') 
	    self.log.debug("Event delta is %s",delta.total_seconds())
	    if delta.total_seconds() >= int(event.details.get("zenpack.community.eventenrichment.expireTime")):
		self.log.debug("Event %s is older than %s",event.evid, event.details.get("zenpack.community.eventenrichment.expireTime"))
		self.zep.addNote(event.evid, 'Expiring event', userName='admin')
		uuidsToClose.append(event.evid)
        if uuidsToClose:
            uuidsToClose = list(set(uuidsToClose))
            eventsToClose = self.zep.createEventFilter(uuid=uuidsToClose)
            self.zep.closeEventSummaries(eventFilter=eventsToClose)


if __name__ == "__main__":
    daemon = zeneventenrichment()
    daemon.run()

