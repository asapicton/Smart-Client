import socket
import sys
import re
import ssl
from socket import *

def parse_URI(URI):
    """
    Purpose: Parses a URI and splits it into its components. Called inititally
    using stdin and also after a redirect from the Location header
    """

    uriPattern = r'^(https?://)?([^/]+)(/.*)?$'
    match = re.match(uriPattern, URI)
    if match:
        protocol = match.group(1) or "https://"
        website = match.group(2)
        path = match.group(3) or '/'
        return website, path

def get_request_msg(path, website):
    """
    Purpose: Formulates a request message using the specified path and website
    to be used to connect to a socket
    """
    path = path.replace('\r', '')
    reqMsg = f"GET {path} HTTP/1.1\r\nHost: {website}\r\n\r\n"
    return reqMsg

def connect80(website, reqHeader):
    """
    Purpose: Uses formulated request header to make a socket connection via
    port 80. Receives a response and returns it
    """
    port = 80
    s = socket(AF_INET, SOCK_STREAM)
    s.connect((website, port))
    s.send(reqHeader.encode())
    data = s.recv(10000)
    return data

def connect443(website, reqHeader, checkh2):
    """
    Purpose: Uses formulated request header to make a socket connection via 
    port 443. Receives a response and returns it. If we are connecting to 
    check if the web server supports h2, then returns a bool
    """
    context = ssl.create_default_context()
    if(checkh2):
        context.set_alpn_protocols(['http/1.1', 'h2'])
    conn = context.wrap_socket(socket(AF_INET), server_hostname=website)
    conn.connect((website, 443))
    conn.send(reqHeader.encode())
    data = conn.recv(1024)
    if(checkh2):
        protocols = conn.selected_alpn_protocol()
        if protocols is None:
            return "no"
        elif "h2" in protocols:
            return "yes"
        else:
            return "no"
    return data


def getCookies(headers):
    """
    Purpose: Searches headers of the web server's response and outputs
    information about each cookie, name, domain, expire time
    """
    cookiesFound = False
    print("2. List of Cookies:")
    for header in headers[1:]:
        if(header[0:11].lower() == "set-cookie:"):
            cookiesFound = True
            cookieInfo = header[12:]
            cookieInfo = cookieInfo.split("; ")
            print("cookie name: " + cookieInfo[0].split("=")[0] + ", ", end="")
            for cookies in cookieInfo:
                cookie = cookies.split("=")
                if cookie[0].lower() == "expires":
                    print("expires time: " + cookie[1] + ", ", end="")    
                elif cookie[0].lower() == "domain":
                    hello = 0
                    print("domain name: " + cookie[1], end="")
            print("")
    if cookiesFound == False:
        print("none")

def getStdin(argv):
    """
    Purpose: Gets and returns user input into stdin
    """
    if len(sys.argv) < 2:
        sys.exit()
    else:
        stdin = sys.argv[1]
        return stdin

def getLocation(headers):
    """
    Purpose: Finds and returns the location header for use in redirection
    """
    for header in headers:
        if(header[0:8] == "Location"):
            location = header[10:]
            return location

def getStatusCode(headers):
    """
    Purpose: Finds and returns the status code header
    """
    statusCode = headers[0].split(" ")[1]
    return statusCode

def redirectRec(headers):
    """
    Purpose: When a redirection code is seen, recursively connect via port
    443 until base case when status code is 200 - OK
    """
    statusCode = getStatusCode(headers)
    if(statusCode == "200" or statusCode == "401" or statusCode == "403"):
        if(statusCode == "200"):
            print("1. Password-protected: no")
        else:
            print("1. Password-protected: yes")
        getCookies(headers) # Prints cookies for final destination
        return
    else: 
        location = getLocation(headers)
        statusCode = getStatusCode(headers)
        website, path = parse_URI(location)
        reqHeader = get_request_msg(path, website)
        print("-----trying on port 443-----")
        data = connect443(website, reqHeader, False)
        data = data.decode()
        print(data + "\n")
        headers = data.split("\r\n")
        redirectRec(headers)
def main():
    stdin = getStdin(sys.argv)
    website, path = parse_URI(stdin)
    reqHeader = get_request_msg(path, website)
    data = connect80(website, reqHeader)
    data = data.decode()
    
    # parses data into header and body
    headers, body = data.split("\r\n\r\n", 1)
    print("---original connection to port 80 header---")
    print(headers + "\n")
    #print("\n")
    headers = headers.split("\r\n")

    h2 = connect443(website, reqHeader, True) # determines if supports h2

    statusCode = getStatusCode(headers)
    if(statusCode == "200"):
        print("1. Password-protected: no")
        getCookies(headers)
    elif(statusCode == "302" or statusCode == "301" or statusCode == "308"):
        redirectRec(headers)
    elif(statusCode == "403" or statusCode == "401"):
        print("1. Password-protected: yes")
        getCookies(headers)
    print("3. Supports http2: " + h2)
if __name__ == "__main__":
    main()
