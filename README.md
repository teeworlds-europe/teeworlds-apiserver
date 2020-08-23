# teeworlds-apiserver

This project doesn't provide any functionality visible to players by itself.
Instead it's supposed to be used as a programming interface for writing external
console based plugins. It's designed to work with vanilla Teeworlds edition.

## Configuration

Configuration should be passed in environment variables:

- `APISERVER_WS_HOST` - websocket bind address
- `APISERVER_WS_PORT` - websocket port
- `APISERVER_WEB_HOST` - commands endpoint bind address
- `APISERVER_WEB_PORT` - commands endpoint port
- `APISERVER_ECON_HOST` - Teeworlds external console address
- `APISERVER_ECON_PORT` - Teeworlds external console port
- `APISERVER_ECON_PASSWORD` - Teeworlds external console password

## Features

- Submit external console commands via HTTP API
- Listen for server events via websocket
- Automatically reconnect to external console after connection error

## Notes

- `webrequest` has been choosen over native `aiohttp` websockets support, due
  to problems with handling abruptly closed connections.
  See https://github.com/aio-libs/aiohttp/issues/2309 for details
- Player names with colons can't be parsed properly. This is a known limitation
  of Teeworlds external console. Please submit issue to this project, if you
  have an idea how to reliably solve this problem without sacrificing too much
  performance.
- API and websocket aren't protected in any way. They shouldn't be exposed
  directly to internet, unless you implement authorization on reverse proxy,
  e.g.: HTTP basic authentication in Nginx or Apache HTTPD.
