# AuthorList
Basic IceCube AuthorList tool.

## Environment

Set up the working environment using `setupenv.sh`.
This creates a python virtualenv in `env`, which you can
activate by doing `. env/bin/activate`.

## Updating the AuthorList

1. Run the edit script with `python edit.py`.  See help for options.

2. Commit changes to the `output.json` file and push to github.

3. Wait for docker image to build - usually 1 minute.

4. Delete old k8s pod.

5. Check that new k8s pod is running and website is reachable.
