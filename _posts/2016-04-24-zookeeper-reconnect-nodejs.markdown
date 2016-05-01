---
layout: post
title:  "Zookeeper client reconnect - design pattern and node.js example"
date:   2016-04-24
categories: personal
---
Imagine that you would like to create a Zookeeper client that is always connected
and automatically reconnects in case of connectivity loss.

What you would basically like to avoid is the need to restart your service in case
it loses connectivity to the Zookeeper.

The Zookeeper client, by definition, reconnects in case of disconnect. Nevertheless,
it does not reconnect on session loss. Let's try to explain why this is Zookeeper's
default modus-operandi and how we can adapt it to an automatic reconnect use-case.

## Why doesn't Zookeeper client reconnect after session expiry?
One of the main use-cases for Zookeeper is leader election. Imagine that there is
a server that is elected to be the worker of a certain queue. How is it elected to
be the leader of that task? It tries to create an ephemeral node in Zookeeper, if
the node doesn't exist yet and the creation operation succeeds, it means that
there is no other server that was elected and that this server is the leader.
If the server loses connectivity it wouldn't like to block other servers from
taking over and becoming the leaders. So it determines a session timeout - a maximum
allowed time for being disconnected. If the server is disconnected from Zookeeper
for a longer period of time, the session expires and all the ephemeral node disappear -
allowing another server to become the leader.

When the client loses the session, Zookeeper also deletes all the watches of
that client, so when reconnecting, the client needs to renew all its watches.
Thus, losing the session is considered pretty catastrophic and the service needs
to take special action in order to recover, i.e. re-initialize the client and the
watches.

## How can we overcome this?
Here we present a pattern to create a wrapper for the Zookeeper client that
automatically re-initializes the client on expiry. The wrapper still emits an
expiry events that needs to be handled by the user of the wrapper.

Example in Coffeescript:
```coffeescript
zookeeper = require 'node-zookeeper-client'
EventEmitter = require 'eventemitter3'

class Zookeeper extends EventEmitter
  module.exports = Zookeeper

  constructor: (@connectionString, @options)->
    @connected = false
    @reconnect = true

    @_initClient()

  _initClient: =>
    @client = zookeeper.createClient @connectionString, @options
    @client.connect()

    console.log 'Connecting to Zookeeper'

    @client.on 'connected', =>
      console.log 'Connected to Zookeeper'
      @connected = true
      @emit 'connected', @client

    @client.on 'disconnected', (err)=>
      console.log 'Disconnected from Zookeeper'
      @connected = false
      @emit 'disconnected', err

    @client.on 'connectedReadOnly', =>
      console.log 'Connected to Zookeeper read only'

    @client.on 'expired', =>
      console.log 'Zookeeper session expired'
      @emit 'expired'
      @_initClient() if @reconnect

    @client.on 'authenticationFailed', =>
      console.log 'Zookeeper authentication failed'
      @emit 'authenticationFailed'

  close: ()=>
    if @connected
      @client.close()
```
