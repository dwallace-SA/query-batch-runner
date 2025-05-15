from argparse import ArgumentParser
from io import StringIO
import json
import shutil
import subprocess
import csv
import getpass
from urllib.parse import quote
from pathlib import Path
from utils import Spinner

## Initialize and assign default values.
# Input and output folders are hard coded currently, could be configurable if desirable.
query_directory = Path("./queries-to-run")
output_directory = Path("./results")
completed_directory = Path("./completed-queries")
config_file = Path("config.json")
total_elapsed = 0
cat_in = ''
repo_in = ''

## Function to remove "#/" from URL copied from webview.
def cleanupEndpoint(input: str):
    return input.replace("#/", "").removesuffix("/")

## Create necessary files if they did not exist / first time running the script

if not config_file.exists():
    try:
        print("\nConfig file initial setup\n") # Debugging only
        user_init=''
        endpoint_init = ''

        user_prompt = input("Would you like to set a default AllegroGraph username? (Y/N): ")
        if user_prompt.upper() == "Y":
            user_init = input("Username: ")
        
        endpoint_prompt = input("Would you like to set a default AllegroGraph endpoint to target? (Y/N): ")
        if endpoint_prompt.upper() == "Y":
            endpoint_init = cleanupEndpoint(input("Endpoint: "))
        
        config_string = f'"username":"{user_init}","endpoint":"{endpoint_init}"'
        config_file.write_text('{' + config_string + '}',encoding="utf-8")
    except KeyboardInterrupt:
        exit(1)

if not query_directory.exists():
    query_directory.mkdir(exist_ok=True)

    print("\nFirst time running this script, necessary directories created! Place queries to be run in the 'queries-to-run' folder.")
    print("See available options and arguments with 'query-batch-runner.py [-h or --help]'")
        
    quit()
if not output_directory.exists():
    output_directory.mkdir(exist_ok=True)

## Command line arguments.
arguments = ArgumentParser(description="SPARQL Query Batch Runner - Using curl and simple authentication, executes all SPARQL queries in a directory.",\
                        #    epilog="***RECOMMEND AGAINST USE ON UNENCRYPTED OR INSECURE (PUBLIC) NETWORKS! Your AllegroGraph credentials could be compromised via interception due to the nature of simple authentication.***"
                           )
arguments.add_argument("-c", "--config", action="store_true",help="View current configuration details.")
arguments.add_argument("-e", "--endpoint", action="store_true", help="Change the saved AllegroGraph endpoint URL.")
arguments.add_argument("-m", "--move", action="store_true", default="store_false", help="Moves each query file into 'completed-queries' directory if successful.")
arguments.add_argument("-rq", "--resetqueries", action="store_true", default="store_false", help="Moves all queries out of completed-queries directory back into the queries-to-run directory, then quits.")
arguments.add_argument("-u", "--user", action="store_true", help="Change stored AllegroGraph username.")

args = arguments.parse_args()



try: ## Try block - Reads in old auth, makes necessary changes based on arguments provided, writes back to config.json.
    with open('config.json', "r") as oldauth:
        newauth = json.load(oldauth)
    if args.resetqueries == True:
        print("\nResetting queries - Moving all .rq files from `./completed-queries` back into the `./queries-to-run` directory.")
        for file in Path('./completed-queries').iterdir():
            if file.is_file():
                shutil.move(file, f'./queries-to-run/{file.name}')
                print(f'Moved {file.name}')
        quit()

    if args.move == True:
        print(f"Successful queries will be moved to {completed_directory.absolute()}")
        completed_directory.mkdir(exist_ok=True)

    if args.config == True:
        print(f"""
              Current configured options:
              Username: {"[Not set]" if newauth['username'] == '' else newauth['username']}
              Endpoint: {"[Not set]" if newauth['endpoint'] == '' else f'{newauth['endpoint']}'}
            """)
        quit()

    if args.endpoint == True:
        print(f"Set new allegrograph endpoint.")
        # Read in and clean up endpoint, removing /# if included.
        endpoint_in = cleanupEndpoint(input(f"Old endpoint: {newauth['endpoint']}\nNew endpoint: "))
        # Write endpoint to config file.
        newauth['endpoint'] = endpoint_in

    if args.user == True:
        newauth['username'] = input(f'\nCurrent username: {newauth['username']}\nSet new username: ')
        
    with open('config.json', 'w') as auth:
        auth.write(json.dumps(newauth))

except KeyboardInterrupt:
    exit(1)

##### Read in config.json to get any pre-defined variables. Prompt for any missing information.. #####
with open('config.json', 'r') as auth:
    keys = json.load(auth)
try:

    endpoint = keys['endpoint'] if keys['endpoint'] != "" else cleanupEndpoint(input("Endpoint to target: "))

    print(f"Current endpoint: {endpoint}")

    print("\nAllegroGraph login credentials:")

    user = input("Enter username: ") if keys['username'] == '' else keys['username']
    print(f"Username: {user}")
    pw = quote(getpass.getpass("Password: "))
except KeyboardInterrupt:
    exit(1)


# Add user and password to URL
no_prefix = endpoint.removeprefix('https://')
full_url = f'https://{user}:{pw}@{no_prefix}'


##### Read in all queries in the ./queries-to-run directory
# Then generate a name for the output file based on their filename, and execute query
# with success or failure message for each.

successes = 0
total_queries = 0
skipped = 0

for query_file in query_directory.glob("*.rq"):
    skip_query = False

    with query_file.open("r", encoding="utf-8") as f:
        query_text = f.read()
    
    if query_text.upper().__contains__("CONSTRUCT {"):
        file_ext = "ttl"
        acceptType = "Accept:text/turtle"
    elif query_text.upper().__contains__("DELETE {") or query_text.upper().__contains__("INSERT {"):
        skip_query = True
    else:
        file_ext = "csv"
        acceptType = "Accept:text/csv,"

    query_name = query_file.stem
    output_file = output_directory / f"{query_name}.{file_ext}"

    print(f"\nCurrent query name: {query_name}")

    if not skip_query:
        total_queries += 1

        curl_to_execute = [
            "curl", 
            "-H", acceptType,
            "-H", "Content-Type: application/sparql-query",
             "--data-binary", f'@{query_file}',
            # "--data", f"{query_text}",
            full_url
        ]
           
        spinner = Spinner(f"Running query {query_name}")
        spinner.start()
        try: 
            response = subprocess.run(curl_to_execute, capture_output=True, text=True)
        except KeyboardInterrupt:
            print("\n✖️ Interrupted.")
            spinner.stop()
            exit(1)
        elapsed = spinner.elapsedTime()
        total_elapsed += elapsed
        spinner.stop()

        # Checks for various common failures and notifies user if encountered.
        # Saves results to a CSV or TTL file depending on determination between SELECT or CONSTRUCT query
        #  can easily change to any other format supported by allegrograph.
        
        if (response.stdout.startswith("Invalid username/password combination.")):
            print("\n❌ Invalid username/password combination.")
            quit()
        elif(response.stdout == ''):
            print(f'❌ No content in response! Probably caused by incomplete configuration, check endpoint.')
            quit()
        elif(response.stdout.startswith("No catalog ")):
            print(f"❌ Invalid catalog: Catalog not found.")
            quit()
        elif(response.stdout.startswith("Unable to open triple-store")):
            print(f"❌ Invalid repository name: Does not exist.")
            quit()
        elif (response.stdout.startswith("MALFORMED QUERY")):
            print(f"❌ MALFORMED QUERY  |  Query duration: {elapsed:.1f}s")
        elif (response.stdout.startswith("No suitable response format available")):
            print(f"❌ No valid response type - Incorrectly identified CONSTRUCT or SELECT\nQuery duration: {elapsed:.1f}s")

        else:
            print(f"✅ Success! {query_name} completed in {elapsed:.1f}s")
            successes += 1
            if args.move == True: 
                shutil.move(query_file, f"./completed-queries/{query_name}.rq")

        if response.returncode == 0:
            # print(response.stdout+"\n\n"+response.stderr) ## DEBUGGING
            if acceptType == "Accept:text/csv,":
                output_file.write_text(response.stdout, encoding='utf-8')
            else:
                with output_file.open("w", encoding="utf-8") as f:
                    f.write(response.stdout)
            print(f"Results saved: {output_file.name}\n")
        else:
            print(f"FAILED curl command for: {query_file.name}:")
            print(response.stderr)
    else:
        print(f"🚫 Query skipped, this script currently does not allow automated INSERT or DELETE (This can be easily enabled when necessary)")
        skipped += 1

print(f"\n✔️ Queries completed, see output files for details.\n   Total execution time: {total_elapsed:.1f}s\n   📈 Queries run: {total_queries} | ✅ Successful: {successes} | ❌ Failed: {total_queries - successes - skipped} | 🚫 Skipped: {skipped}")


