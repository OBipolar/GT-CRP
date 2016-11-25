GT-CRP
    A Protocol for Reliable Communication
    CS-3251 Sockets Programming Assignment 2
    Last Updated 11/25/2016

Authors:
    Shaohui Xu (902987595) shaohuixu13@gmail.com
    DU Xinnan (903266560) xinnan@gatech.edu

File strcuture:
    CRP.py:
            Main file of protocol, including both sender and recevier code
    crpPacket.py:
            crpPacket and util functions, used to support CRP.py
    FTA-client.py:
            FTA client with connect, get F, post F, window W and disconnect features
    FTA-server.py:
            FTA server with window W and terminate features
    CRP_ShaohuiXu_XinnanDu.pdf:
            Original CRP protocol descriptions
    Sample.txt:
            Sample output from both FTA-client.py and FTA-server.py

Notes on compiling and running of program:
    The extra packet of netaddr needs to be installed, please run (pip install netaddr beforehand)
    Run the server first：
        python FTA-server.py <Self Port>
    Then run the client code:
        python FTA-client.py <Server address> <Server Port>
