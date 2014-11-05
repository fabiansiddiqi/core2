#!/usr/bin/env python
# pylint: disable=relative-import

import BaseHTTPServer
import re
import logging
from agent_coordinator import AgentCoordinator
from agent_coordinator_poller import AgentCoordinatorPoller


logging.basicConfig(format='%(asctime)s %(message)s')
logger = logging.getLogger('tap_server')
logger.setLevel(logging.INFO)


PORT = 6789
MAX_DICT_SIZE = 5000
ROUTE_COMMIT = r'/commit/([a-zA-Z0-9]+)$'
ROUTE_STATUS = r'/status/?$'
ROUTE_ADD_BUILDER = r'/add_builder/?$'


coordinator = None


class GetBuildHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # pylint: disable=invalid-name
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        if re.match(ROUTE_COMMIT, self.path):
            commit = re.match(ROUTE_COMMIT, self.path).group(1)
            if coordinator.has_commit(commit):
                build_status = coordinator.get_build_status(commit)
                status = build_status if build_status else 'No status'
                self.wfile.write('Commit status: %s\n' % status.last_output)
            else:
                coordinator.add_to_queue(commit)
                self.wfile.write('Added commit %s to the queue\n' % commit)
        elif re.match(ROUTE_STATUS, self.path):
            self.wfile.write('Status: %s\n' % coordinator.get_status())
        elif re.match(ROUTE_ADD_BUILDER, self.path):
            builder = coordinator.add_agent()
            self.wfile.write('Added builder %s\n' % builder.agent_id
                             if builder else 'Max number of builders already reached')


if __name__ == '__main__':
    coordinator = AgentCoordinator()
    coordinator.add_existing_repos()
    poller = AgentCoordinatorPoller(coordinator)
    poller.start()
    try:
        server = BaseHTTPServer.HTTPServer(('', PORT), GetBuildHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()
        poller.stop()
