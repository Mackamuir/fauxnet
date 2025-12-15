from time import sleep
import random
import requests
import subprocess
import yaml
import sys
import netifaces

def getUserAgent(filePath='./UserAgents.txt'):
    try: 
        with open(filePath, 'r') as UserAgentsFile: 
            userAgents = [UserAgent.strip() for UserAgent in UserAgentsFile]
        return random.choice(userAgents)
    except (FileNotFoundError, IndexError) as e:
        print(f"Error getting user agent: {e}. Using a default user agent.")
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

def runCommand(commandList):
    try:
        process = subprocess.Popen(
            commandList,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in process.stdout:
            print(line, end="")
        process.wait()
        return process.returncode == 0
    except FileNotFoundError:
        print(f"Error: Command not found. Please ensure '{commandList[0]}' is installed.")
        return False
    except Exception as e:
        print(f"An error occurred while running command: {e}")
        return False


def browse(target):
    try:
        response = requests.get(f"http://{target}", headers={"User-Agent": getUserAgent()})
        return response
    except:
        pass

def ping(target):
    pingCmd = ["ping", "-c", "4", target]
    runCommand(pingCmd)

def portScan(target):
    runCommand(["nmap", "--dns-servers", "8.8.8.8", "-sS", "-sV", "-O", "-A", "-p", "1-1000", target])

def httpEnum(target):
    runCommand(["nmap", "--dns-servers", "8.8.8.8", "--script", "http-enum", target])

def httpSpider(target):
    runCommand(["wget", "--spider", "--recursive", f"http://{target}"])

def smbEnum(target):
    runCommand(["nmap", "--dns-servers", "8.8.8.8", "--script", "smb-enum-all", "-p", "445", target])
    

def parseConfigItems(items):
    if not items:
        return [], []

    keys = []
    probabilities = []
    hasWeights = any(isinstance(item, dict) for item in items)
    
    if hasWeights:
        for item in items:
            if isinstance(item, dict):
                key, weight = next(iter(item.items()))
                keys.append(key.lower())
                probabilities.append(float(weight))
            else:
                keys.append(item.lower())
                probabilities.append(0.0) # Will be updated later
        
        # Calculate remaining probability for unweighted items
        totalAssignedProbabilities = sum(p for p in probabilities if p > 0)
        unweightedCount = probabilities.count(0.0)
        
        if totalAssignedProbabilities > 100:
            print("Error: Total assigned probabilities exceed 100%. Normalizing...")
            totalAssignedProbabilities = 100
        
        remainingProbabilities = 100 - totalAssignedProbabilities
        
        if unweightedCount > 0:
            uniformProbabilites = remainingProbabilities / unweightedCount
            probabilities = [p if p > 0 else uniformProbabilites for p in probabilities]
    else:
        # Append our keys
        for item in items:
            keys.append(item.lower())
        # All items are unweighted, so assign equal probability
        probabilities = [100.0 / len(items)] * len(items)

    totalProbability = sum(probabilities)
    if totalProbability > 0:
        probabilities = [p / totalProbability for p in probabilities]
    return keys, probabilities


if __name__ == "__main__":
    try:
        with open("/opt/fauxnet/core/community/config.yaml", "r") as configFile:
            config = yaml.safe_load(configFile)
    except FileNotFoundError:
        sys.exit("Fatal! Configuration file './opt/fauxnet/core/community/config.yaml' not found.")
    except yaml.YAMLError as e:
        sys.exit(f"Fatal! Error parsing YAML configuration: {e}")


    if not config.get("Enable", False):
        sys.exit("Community is disabled in the configuration, exiting.")

    # Parse sleep from config
    sleepConfig = config.get("Sleep", {})
    minSleep = sleepConfig.get("Min", 30)
    maxSleep = sleepConfig.get("Max", 120)

    if minSleep > maxSleep:
        print("Warning: Minimum sleep time is greater than maximum. Resetting to defaults.")
        minSleep = 30
        maxSleep = 120
    
    doSleep = all(key in sleepConfig for key in ["Min", "Max"])

    targetsConfig = config.get("Targets")
    if not targetsConfig:
        sys.exit("Fatal! No Targets found in configuration.")
    targetKeys, targetProbs = parseConfigItems(targetsConfig)

    actionsConfig = config.get("Actions")
    if actionsConfig:
        actionKeys, actionProbs = parseConfigItems(actionsConfig)
        print("Configured Actions:")
        print(*actionKeys, sep='\n')
    else:
        print("Warn! No Actions found in configuration. Using following actions:")
        actionKeys = ["browse", "ping", "portscan", "httpenum", "smbenum"]
        print(*actionKeys, sep='\n')
        actionProbs = None

    actionsMap = {
        "browse": browse,
        "ping": ping,
        "portscan": portScan,
        "httpenum": httpEnum,
        "httpspider": httpSpider,
        "smbenum": smbEnum
    }


    while True:
        # Renew DHCP Address
        print("Info: Changing MAC address to renew IP from DHCP.")
        mac = f"02:00:00:{random.randint(0, 255):02x}:{random.randint(0, 255):02x}:{random.randint(0, 255):02x}"
        print("Info: New MAC address: " + mac)
        subprocess.run(["dhclient", "-r"], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
        subprocess.run(["ip", "link", "set", "dev", "eth0", "address", mac])
        sleep(5)
        subprocess.run("dhclient", stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
        try:
            ipv4_address = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
            print(f"New IP: {ipv4_address}")
        except ValueError:
            print("Error: 'eth0' interface not found. Cannot retrieve IP address.")
        except Exception as e:
            print(f"An error occurred while getting IP address: {e}")

        # Pick something to do
        targetToHit = random.choices(targetKeys, weights=targetProbs, k=1)[0]
        actionToRun = random.choices(actionKeys, weights=actionProbs, k=1)[0]

        print(f"Running '{actionToRun}' on target: {targetToHit}")

        actionFunction = actionsMap.get(actionToRun)
        if actionFunction:
            actionFunction(targetToHit)
        else:
            print(f"Error: Unknown action '{actionToRun}'.")
            
        # Sleep for a random duration
        if doSleep:
            sleepTime = random.randint(minSleep, maxSleep)
            print(f"Task completed. Sleeping for {sleepTime} seconds...")
            sleep(sleepTime)
        else:
            print("Task completed. Continuing...")