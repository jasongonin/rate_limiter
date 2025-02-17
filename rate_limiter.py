# rate_limiter.py

import os
import time
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests

class RateLimitedProxyService(threading.Thread):
    def __init__(self, host="localhost", port=8080, rate_limit_per_sec=1.0, remote_destination=None):
        """
        Initialize the proxy service with configurable parameters.

        :param host: Hostname or IP address to bind the proxy server (default: "localhost").
        :param port: Port number to expose the proxy service (default: 8080).
        :param rate_limit_per_sec: Maximum number of calls allowed per second per source IP (default: 1.0).
        :param remote_destination: URL of the remote destination to forward requests to.
                                   If None, it will use the REMOTE_DESTINATION environment variable.
        """
        super().__init__()
        self.host = host
        self.port = port
        self.rate_limit_per_sec = rate_limit_per_sec
        self.remote_destination = remote_destination or os.getenv("REMOTE_DESTINATION", "http://example.com")
        self.running = True

    def run(self):
        """Start the proxy server in a separate thread."""
        server_address = (self.host, self.port)
        httpd = HTTPServer(server_address, self._create_request_handler())
        print(f"Starting proxy service on {self.host}:{self.port}...")
        while self.running:
            httpd.handle_request()
        print("Proxy service stopped.")

    def stop(self):
        """Stop the proxy service."""
        self.running = False

    def _create_request_handler(self):
        """
        Create a custom request handler with access to the rate limit and remote destination.
        """
        # Capture the instance variables in a closure
        rate_limit_per_sec = self.rate_limit_per_sec
        remote_destination = self.remote_destination

        class CustomRequestHandler(BaseHTTPRequestHandler):
            # Global state for rate limiting
            rate_limit_cache = defaultdict(list)

            def do_GET(self):
                """Handle incoming GET requests."""
                client_ip = self.client_address[0]
                current_time = time.time()

                # Enforce rate limiting
                if not self._is_within_rate_limit(client_ip, current_time, rate_limit_per_sec):
                    self.send_response(429)  # Too Many Requests
                    self.end_headers()
                    self.wfile.write(b"Rate limit exceeded. Please try again later.")
                    return

                # Forward the request to the remote destination
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                remote_url = f"{remote_destination}{parsed_url.path}"
                try:
                    response = requests.get(remote_url, params=query_params, timeout=5)
                    self.send_response(response.status_code)
                    for header, value in response.headers.items():
                        self.send_header(header, value)
                    self.end_headers()
                    self.wfile.write(response.content)
                except requests.RequestException as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"Error forwarding request: {str(e)}".encode())

            @staticmethod
            def _is_within_rate_limit(client_ip, current_time, rate_limit_per_sec):
                """Check if the client IP is within the allowed rate limit."""
                # Remove outdated timestamps
                CustomRequestHandler.rate_limit_cache[client_ip] = [
                    t for t in CustomRequestHandler.rate_limit_cache[client_ip] if current_time - t < 1.0
                ]

                # Check if the number of calls exceeds the rate limit
                if len(CustomRequestHandler.rate_limit_cache[client_ip]) >= rate_limit_per_sec:
                    return False

                # Add the current timestamp to the cache
                CustomRequestHandler.rate_limit_cache[client_ip].append(current_time)
                return True

        return CustomRequestHandler


def start_proxy_service(host="localhost", port=8080, rate_limit_per_sec=1.0, remote_destination=None):
    """
    Start the proxy service with configurable parameters.

    :param host: Hostname or IP address to bind the proxy server (default: "localhost").
    :param port: Port number to expose the proxy service (default: 8080).
    :param rate_limit_per_sec: Maximum number of calls allowed per second per source IP (default: 1.0).
    :param remote_destination: URL of the remote destination to forward requests to.
                               If None, it will use the REMOTE_DESTINATION environment variable.
    :return: The running proxy service instance.
    """
    proxy_service = RateLimitedProxyService(host, port, rate_limit_per_sec, remote_destination)
    proxy_service.daemon = True
    proxy_service.start()
    return proxy_service