# mqtt-logger

A Dockerized MQTT client that saves MQTT topic changes to rotated log files.

I originally created this simple script to log messages from ESPHome nodes but I expect it has many other uses so I'm putting it out there.

## mqtt-logger.py

The main script can be run outside of Docker but was intended to run inside a container. Use it how you need it.

Running the script with no arguments will cause it to look for a configuration file in /config/configuration.yaml, which will probably fail. Use the '--config' option to set an explicit path to a configuration.

## Docker

Clone the repository and run the "build" script to build your own image. You can change the build script to customize the build command however you'd like.

I've included a simple docker-compose file that shows how I use the image in my setup. I've excluded all the other services I use for clarity.

## Limitations

1. Only TCP connections are supported. No websockets.
1. Only non-encrypted connections are supported. No SSL/TLS.

