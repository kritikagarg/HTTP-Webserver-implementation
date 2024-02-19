# HTTP Web Server Implementation in Python

This repository contains a Python-based implementation of a standard-compliant HTTP web server. The development of this server is guided by a thorough understanding of the Hypertext Transfer Protocol (HTTP) and aims to demonstrate protocol conformance as per the relevant RFCs (Request for Comments).

## Features

Our web server showcases a comprehensive range of HTTP functionalities, including:

- **HTTP Methods:** Support for a complete set of HTTP methods.
- **Status Codes and Headers:** Implementation of various HTTP status codes and headers.
- **MIME Types:** Handling of multiple MIME types.
- **Access Log:** Detailed access logs for monitoring server requests and responses.
- **Conditionals and Redirections:** Efficient handling of conditional requests and redirections.
- **Connection Management:** Support for long-lived and pipelined connections.
- **Encoding and Content Negotiation:** Capabilities for content encoding and negotiation.
- **Partial Content:** Handling requests for partial content delivery.
- **Authentication and Authorization:** Robust mechanisms for user authentication and resource authorization.
- **Unsafe Methods and CGI:** Implementation of unsafe methods and server-side execution using Common Gateway Interface (CGI).

## Deployment

The server is containerized using Docker, enabling easy deployment and testing on remote machines. This approach ensures a consistent environment for all users, facilitating testing and scalability.
