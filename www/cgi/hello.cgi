#!/bin/sh
# Minimal CGI script: echoes the query string and request method.
printf 'Content-Type: text/plain\n\n'
printf 'method=%s\n' "$REQUEST_METHOD"
printf 'query=%s\n' "$QUERY_STRING"
