[![CodeFactor](https://www.codefactor.io/repository/github/vwt-digital/cloudbuilder-import-common/badge)](https://www.codefactor.io/repository/github/vwt-digital/cloudbuilder-import-common)

# Import Common
In programming, it often happens that we want to reuse code. But how will we go about doing this in cloud functions?
That's where `import_common.py` comes in.

## Arguments
Our `import_common.py` has a few **optional** arguments that we can use in case our file structure differs 
from the standard (as shown in examples bellow).

| Field               | Description                                                                              | Default                                                                                                                                                                        | Required |
| :------------------ | :--------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------: |
| --function-path     | The path of the cloud function.                                                          | `.`                                                                                                                                                                            | No       |
| --common-path       | The path of the common folder. Relative to `{remote_clone_path}` when using --remote-uri | `../common`                                                                                                                                                                    | No       |
| --common-package    | The base package used in the common code.                                                | `functions.common`                                                                                                                                                             | No       |
| --function-package  | The base package used by the cloud function.                                             | --common-package (`functions.common`) where the common directory name (`common`) is replaced by the functions directory name (`some_function`). E.g. `functions.some_function` | No       |
| --remote-uri        | The URI of the remote to clone.                                                          | None                                                                                                                                                                           | No       |
| --remote-clone-path | The path to clone the remote files to.                                                   | `../remotes`                                                                                                                                                                   | No       |
| --remote-branch     | The branch of the remote to clone.                                                       | master                                                                                                                                                                         | No       |

## Local Common Functions
In our cloud function repositories we structure code in the follow way:
```
my_repository
└───functions
    ├───common
    │   └───common_objects.py
    ├───some_cloud_function
    │   ├───main.py
    │   ├───deploy.json
    │   └───requirements.txt
    └───another_cloud_function
        ├───main.py
        ├───deploy.json
        └───requirements.txt
```

In this example you can see we have 2 functions: 'some_cloud_function', and 'another_cloud_function'.
If these functions share functionality, it can be a good idea to abstract that functionality 
away into a common folder. Here we put some object(s) (`common_objects.py`) that both functions 
use in the common folder, which when deployed correctly can be used by both functions.

In order to import this common folder onto the cloud correctly we will use `import_common.py` in our `cloudbuild.yaml`.

To deploy the two functions we could use these example steps in our `cloudbuild.yaml`:
```yaml
# Deploys some_cloud_function
- name: 'eu.gcr.io/{cloudbuilders}/cloudbuilder-function-deploy'
  id: 'Deploy some_cloud_function'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      import_common.py
      function_deploy.py ${PROJECT_ID}-some-cloud-function
  dir: 'my_repository/functions/some_cloud_function'

# Deploys another_cloud_function
- name: 'eu.gcr.io/{cloudbuilders}/cloudbuilder-function-deploy'
  id: 'Deploy another_cloud_function'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      import_common.py
      function_deploy.py ${PROJECT_ID}-another-cloud-function
  dir: 'my_repository/functions/another_cloud_function'
```

Here you can see that we first import the common functionality before 
deploying the function to the cloud with `function_deploy.py`.  This will make sure that 
the cloud has access to our common code when deploying, and not to mention it allows us to use the common code
in both functions!

Behind the scenes we actually copy the contents of the common folder into the folder of the function 
with a simple "treecopy". After some much-needed [preprocessing](#python-imports).

## Remote Common Functions
So now that we can reuse local cloud functions let's see how we can reuse them remote.

### Library
If we have **a lot** of code that might as well be put into a library, we should consider making a 
library or module. This can easily be done by creating a `setup.py` in the library/module and importing 
the git repo in the `requirements.in` file of our function.

### Submodule
If we want to reuse code from another repository, and let us have access to that code locally as well, 
we can use a [git submodule](https://github.blog/2016-02-01-working-with-submodules/) together with the 
[Local Common Functions](#local-common-functions) method (since we now have our files "locally").

### import_common.py
We will assume we want to go the `import_common.py` route, because we only need to import one common
function for example.

We will use the following setup:
```
my_repository
└───functions
    └───some_cloud_function
        ├───main.py
        ├───deploy.json
        └───requirements.txt


my_remote_repository
└───functions
    ├───common
    │   └───common_objects.py
    ├───uncommon
    │   └───uncommon_objects.py
    └───another_cloud_function
            ├───main.py
            ├───deploy.json
            └───requirements.txt
```

In this case our common function is locked away in another repository, but fear not, we can use
the [`--remote-*`](#arguments) arguments to make our lives easier.

A `cloudbuilder.yaml` step to deploy 'some_cloud_function' might look something like this:
```yaml
# Deploys some_cloud_function
- name: 'eu.gcr.io/{cloudbuilders}/cloudbuilder-function-deploy'
  id: 'Deploy some_cloud_function'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      import_common.py \
      --remote-uri https://example.com/me/my_repository.git \
      --common-path functions/common
      
      function_deploy.py ${PROJECT_ID}-some-cloud-function
  dir: 'my_repository/functions/some_cloud_function'
```

Sounds good, but what if we want to spice it up a bit. For that same function we also want to import the
`uncommon` files from the `develop` branch.

Let's do it:
```yaml
# Deploys some_cloud_function
- name: 'eu.gcr.io/{cloudbuilders}/cloudbuilder-function-deploy'
  id: 'Deploy some_cloud_function'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      import_common.py \
      --remote-uri https://example.com/me/my_repository.git \
      --branch develop \
      --common-path functions/uncommon \
      --common-package functions.uncommon
      
      import_common.py \
      --remote-uri https://example.com/me/my_repository.git \
      --common-path functions/common
      
      function_deploy.py ${PROJECT_ID}-some-cloud-function
  dir: 'my_repository/functions/some_cloud_function'

```
If the `--remote-*` arguments sound complicated, you can just consider them pulling remote code to a folder, and
then `--common-path` being relative to that folder.

## Python Imports
Now you might think: won't my function's imports be all wrong after the common folder's contents
are copied into it? This is where the preprocessing comes in. The `import_common.py` will first scan all
the function's code and tries to correct the imports.

It does this by replacing all `--common-package` text to `--function-package` text (**only** in the import lines).

E.g.
`my_repository/functions/some_cloud_function/main.py`
```python
from functions.common.common_objects import CommonObject
import functions.common


def main():
    common = CommonObject()

```

Will become:
```python
from functions.some_cloud_function.common_objects import CommonObject
import functions.some_cloud_function


def main():
    common = CommonObject()

```