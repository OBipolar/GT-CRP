# Server:
* SetupServer
    * Check IPv6 or IPv4
    * Bind to port 
    * 3-way handshake  to start new connection 
        * Add sender thread
        * Add receiver thread
* Receiver (keep-alive)
    * Close if timeout exceed
    * Try checksum 
        * NACK
        * Empty ACK
        * Data and ACK (piggy-backing) 
        * Data 
        * Fin
    * If checksum failed, resend 
* Sender 
    * Check sendingqueue and nackqueue 
        * Pop from sendingQueue
        * Push to NACK_queue 
        * Send 

# Client 
* ConnectTo 