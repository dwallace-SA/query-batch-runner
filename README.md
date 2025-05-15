# query-batch-runner
Runs a batch of SPARQL queries from a directory against a designated endpoint, using basic HTTP authentication.

# Setup Instructions
To get started, just run `python query-batch-runner.py`

On the initial run of the script, required folders and a configuration file will be created. All configuration can be completed by following prompts.

Command line arguments `-h` or `--help` will display the help text and command line options, a version of which is also included below (The script help command will always have the most up-to-date documentation):

```
options:
  -h, --help           show this help message and exit
  -c, --config         View current configuration details.
  -e, --endpoint       Change the saved AllegroGraph endpoint URL.
  -m, --move           Moves each query file into 'completed-queries' directory if successful.
  -rq, --resetqueries  Moves all queries out of completed-queries directory back into the queries-to-run directory,
                       then quits.
  -u, --user           Change stored AllegroGraph username.
```
