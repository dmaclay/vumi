Forwarding SMSs from an SMPP bind
=================================

A simple use case for Vumi is to aggregate incoming SMSs and forward them via HTTP POST to a URL.

In this use case we are going to:

    1. Use a SMSC simulator for local development.
    2. Configure Vumi accept all incoming and outgoing messages on an SMPP bind.
    3. Setup a worker that forwards all incoming messages to a URL via HTTP POST.
    4. Setup Supervisord to manage all the different processes.
    
.. note::
    If you're using vagrant to setup a virtual machine some of these steps will already have been done for you.
    
.. note::
    Some basic understanding of AMQP is assumed.


Redis
-----

Redis is used for all situations where temporary information must be cached where:

    a. it will survive system shutdowns
    b. it can be shared between workers

One use of Redis is for mapping between smpp sequence_numbers and long term unique id's on the ESME and the SMSC.
The sequence_number parameter is a revolving set of integers used to pair outgoing async pdu's with their response, i.e. submit_sm & submit_sm_resp.
Both submit_sm and the corresponding submit_sm_resp will share a single sequence_number, however, for long term storage and future reference, it is necessary to link the id of the message stored on the SMSC (message_id in the submit_sm_resp) back to the id of the sent message.  As the submit_sm_resp pdu's are received, the original id is looked up on redis via the sequence_number and associated with the message_id in the response.

Followup pdu's from the SMSC (i.e. delivery reports) will reference the original message by the message_id held by the SMSC which was returned in the submit_sm_resp.

A second use of Redis is to cache sessions (i.e. for USSD) this means that in-progress sessions will be saved to disk (protecting against system shutdowns), and that a pool of generic workers may be used to handle sessions.  Each worker retrieves the session state from redis as it gets the next message for a given session, meaning that:

    a. single workers can easily handle multiple ongoing sessions
    b. the session messages don't have to be routed to the exact same worker each time for a given session


Installing the SMSC simulator
-----------------------------

Go to the `./utils` directory in the Vumi repository and run the bash script called `install_smpp_simulator.sh`. This will install the SMSC simulator from http://seleniumsoftware.com on your local machine. This simulator does exactly the same as a normal SMSC would do with the exception that it doesn't actually relay the messages to mobile networks.::

    $ cd ./utils
    $ ./install_smpp_simulator.sh
    
This will have installed the application in the `./utils/smppsim/SMPPSim` directory. 

By default the SMPP simulator tries to open port 88 for it's HTTP console, since you often need administrative rights to open ports lower than 1024 let's change that to 8080 instead.

Line 60 of `./utils/smppsim/SMPP/conf/smppsim.props` says::

    HTTP_PORT=88

Change this to::

    HTTP_PORT=8080

Another change we need to make is on line 83::

    ESME_TO_ESME=TRUE
    
Needs to be changed to, FALSE::

    ESME_TO_ESME=FALSE

Having this set to True sometimes causes the SMSC and Vumi to bounce messages back and forth without stopping.

.. note::
    The simulator is a Java application and we're assuming you have Java installed correctly.

Configuring Vumi
----------------

Vumi relies for a large part on AMQP for its routing capabilities. The AMQP specification says that messages are sent to an exchange. Together with the exchange type, the message's routing key and the queue's binding key determine where and how a message is finally delivered. Have a look at http://blog.springsource.com/2010/06/14/understanding-amqp-the-protocol-used-by-rabbitmq/ for a more detailed explanation.

Vumi, by default, is configured to make use of `direct` exchanges, that means that a message's routing key must exactly match a queue's binding key for it to be delivered to that queue. By default that is fine but sometimes different behaviour is required. In this example we're going to deviate from that behaviour.

We're assuming that all messages being sent back to an SMSC can be delivered by the SMSC to the number specified. This means that we're going to use a `topic` exchange instead of a direct exchange. A `topic` exchange allows for wildcard matching of routing keys.

Vumi's SMPP transport can be configured by a YAML file, `./config/example_smpp.yaml`. For this example, this is what our SMPP configuration looks like:

.. literalinclude:: ../../config/example_smpp.yaml

We've configured the details of the SMPP server but also we've told Vumi to send and receive messages via `topic` exchange called `vumi.topic`.

Configure an SMPP Transport
---------------------------

To get the desired behaviour we need to subclass the standard SMPP transport
that Vumi ships with since we want to publish to a `topic` exchange.

.. literalinclude:: ../../vumi/workers/smpp/topic_transport.py

Configure a Worker
------------------

Now that we've got a Vumi transport setup that accepts incoming messages over an SMPP bind let's setup a worker to forward the messages to a URL via HTTP POST.

.. literalinclude:: ../../vumi/workers/smpp/topic_worker.py

Supervisord!
------------

Let's use Supervisord to ensure all the different parts keep running.
Here is the configuration file `supervisord.example.conf`:

.. literalinclude:: ../../supervisord.example.conf

Ensure you're in your python `virtualenv` and start it with the following command::

    $ supervisord -c supervisord.example.conf

You'll be able to see the HTTP management console at http://localhost:9010/ or at the command line with::

    $ supervisorctl -c supervisord.example.conf

Let's give it a try:
--------------------

1. Go to http://localhost:8080 and send an SMS to Vumi via "Inject an MO message".
2. Type a message, it doesn't matter what `destination_addr` you chose, since it's a topical exchange Vumi will route all incoming message to the `TopicSmppWorker` which will HTTP POST to the URL provided.
