# Linux Client

Install on every monitored linux host

### Installation
Prerequisites: Golang and OSQueryi  

For convenience, an install script has been provided that compiles the client, sets configuration variables, and creates, starts, and enables a systemd service for the client. Simply run `bash install.sh` (must run as sudo/root)  

To run or install manually:
* Compile the client with `go build ./...`
* Copy `.env.example` to `.env` and replace values
* Run as `./boombox-client`. Note that for most remedations to be effective, the client must be run as root  

If desired, you can later set the client up as a systemd service:
* Copy `boombox-client` to `/usr/local/sbin/`
* Copy `.env` to `/etc/boombox/boombox-client.env`
* Copy `boombox-client.service` to `/etc/systemd/system/`
* Run `systemctl daemon-reload`
* Start/Enable the service as `boombox-client`

### Source Files

The boombox-client Go module is broken up as follows:  
* `api.go`: Functions to send requests to the Boombox server API  
* `http.go`: Utility functions used by `api.go`  
* `main.go`: Main polling loop, executes queries and remediations  
* `models.go`: Structs for JSON marshalling and unmarshalling for API interractions