# **SIMPLE TORRENT-LIKE APPLICATION**

## **Objective**
Build a **Simple Torrent-like Application(STA)** with the protocols defined by each group, using 
the TCP/IP protocol stack and must support    **multi-direction data transfering (MDDT)**

## **Contributors
- Cao Ngọc Lâm - 2252419
- Nguyễn Châu Hoàng Long - 2252444  
- Trịnh Anh Minh - 2252493
- Hồ Khánh Nam - 2252500


## **Application Description**
- The application includes the two types of hosts: tracker and node.
- centralized tracker keeps track of multiple nodes and stores what pieces of files.
- Through tracker protocol, a node informs the server as to what files are contained in its local
repository but does not actually transmit file data to the server.
- When a node requires a file that does not belong to its repository, a request is sent to the
tracker.
- **MDDT**: The client can download multiple files from multiple source nodes at once,
simultaneously. 

## **Getting started**

### **Prerequisites**
- Make sure you alread have installed Python on your system.
- Otherwise following this guide to fulfill it: ![how-to-install-python-on-windows]{https://www.geeksforgeeks.org/how-to-install-python-on-windows/}

### **Running the application
1. Clone the repository and navigate the project directory
```bash
   git clone https://github.com/nhatkhangcs/231-computer-network-assignment1.git
   ```
2. Connect local devices in a public wireless LAN.
3. Each devices conduct to download the external packages used throughout implementation in the *requirement.txt* file following the command:
```bash
   pip install -r requrirement . txt
   ```
4. Make sure to configure the IP and port that the tracker bind to and ensure that the IP and port that other nodes connect to matches that tracker IP and port, also configures the IP that the upload socket of each node bind to in the Torrent-like network so that it can be reached from other clients for fetching files
5. One device run as tracker in folder tracker
```bash
   python tracker.py
   ```
6. Other devices run as nodes in folder node
```bash
   python node.py
   ```
**NOTE:** When tracker listening connection from nodes, if failed, temporarily turning off your firewall and antivirus software,then try again.

## **Tracker command-shell interpreter**


## **Node command-shell interpreter**
 

## **Contributing**
For contribution actions, please fork the repository and create a pull request. Our team will verify it before merging to our project

## **License**
This project is licensed under the HCMUT license.

You are welcome to adjust this template to fit the structure and needs of your project.