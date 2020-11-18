import subprocess
import os
import socket, ssl
from os.path import isfile
from ast import literal_eval
import json

class Clientlib:
    def __init__(self, base_file_path, settings):
        self.base_file_path = base_file_path
        self.settings = settings

    def getRGSversion(self):
        p = subprocess.Popen([self.settings.get("RGS_Location"), "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, er = p.communicate()
        version = (out+er).split()[(out+er).split().index('Version')+1]
        return version

    def readConfigFile(self, config_file_name):
        filelocation = self.base_file_path + '/' + config_file_name
        # filelocation = os.path.dirname(os.path.abspath(application_path)) + '/LabConnect.conf'
        if not isfile(filelocation):
            return False
        
        with open(filelocation, 'r') as f:
            for line in f:
                line = line.strip()
                if (not line.startswith('#')) and line:
                    try:
                        (key,val) = line.split(':\t',1)
                    except:
                        try:
                            (key,val) = line.split(None,1)
                            key = key[:-1]
                        except:
                            key = line
                            key = key.strip()
                            key = key[:-1]
                            val = ''
                    self.settings[key] = val
            f.close()

        #insert default settings for all not specified
        if not self.settings.get("Host_Addr"):
            self.settings["Host_Addr"] = 'localhost'
        if not self.settings.get("Client_Port"):
            self.settings["Client_Port"] = 18181
        if not self.settings.get("SSL_Cert"):
            self.settings["SSL_Cert"] = None
        if not self.settings.get("Command"):
            if self.settings.get("Command-Win"):
                self.settings["Command"] = settings.get("Command-Win")
            elif self.settings.get("Command-Lin"):
                self.settings["Command"] = settings.get("Command-Lin")
            else:
                self.settings["Command"] = None
        if not self.settings.get("RGS_Options"):
            self.settings["RGS_Options"] = False
        if not self.settings.get("RGS_Location"):
            self.settings["RGS_Location"] = None
        if (not self.settings.get("Net_Domain")) or (self.settings.get("Net_Domain")=='None'):
            self.settings["Net_Domain"] = ""
        if not self.settings.get("RGS_Version"):
            self.settings["RGS_Version"] = 'False'
        if not self.settings.get("RGS_Hide"):
            self.settings["RGS_Hide"] = 'True'
        
        return True

    def getPools(self, user, password, host, port, retry=0):
        print("getting pools")
        # add the version check into the pool request. 
        if self.settings.get("RGS_Version") == True:
            content = json.dumps(['prv', user, password, getRGSversion()]) + '\r\n'
        else:
            content = json.dumps(['pr', user, password]) + '\r\n'
        # read message and save connection socket
        print(content)
        s_wrapped = self.send_message(content, host, port)
        pools = self.read_response(s_wrapped, lambda: self.getPools(user, password, host, port, retry+1))
        print(pools)
        poolsliterals = pools.split('\n')
        poolset = set()
        for literal in poolsliterals:
            if literal:
                poolset.add(literal_eval(literal))
        return poolset

    def getMachine(self, user, password, pool, host, port, retry=0):
        if pool == '' or pool is None:
            return ''
        content = json.dumps(['mr', user, password, pool]) + '\r\n'
        s_wrapped = self.send_message(content, host, port)
        return self.read_response(s_wrapped, lambda: self.getMachine(user,password,pool,host,retry+1))

    def send_message(self, message, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("host: ", host)
        print('port: ', port)
        s.connect((host, port))
        print('heree')
        if (self.settings.get("SSL_Cert") is None) or (self.settings.get("SSL_Cert") == 'None'):
            s_wrapped = s
        else:
            ssl_cert = self.base_file_path + "/" + self.settings.get("SSL_Cert")
            print(ssl_cert)
            s_wrapped = ssl.wrap_socket(s, cert_reqs=ssl.CERT_REQUIRED, ca_certs=ssl_cert, ssl_version=ssl.PROTOCOL_SSLv23)
        
        s_wrapped.sendall(message.encode())
        return s_wrapped

    def read_response(self, sock, callback):
        response = ""
        while True:
            chunk = sock.recv(1024).decode()
            response += chunk
            if chunk == '':
                break
        if response.startswith("Err:"):
            if (response == "Err:RETRY") and (retry < 6):
                sleep(retry)
                return callback()
            else:
                raise ServerError(response)
        return response
