import sys
import uuid
import stratus

PROMPT = "Method to call: "
CLI_NAME = str(uuid.uuid4())

def main():
    # Create the client
    client = stratus.client()
    # Connect to the cluster
    client.connect(host=sys.argv[1], name=CLI_NAME)
    # Ask function to call
    line = raw_input(PROMPT)
    while line != "exit":
        line = line.split()
        print client.call(*line).result()
        line = raw_input(PROMPT)

if __name__ == '__main__':
    main()
