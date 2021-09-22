#!/usr/bin/env python3

import argparse
import json
import subprocess  # nosec

parser = argparse.ArgumentParser()
parser.add_argument("name", type=str, help="function name")
parser.add_argument(
    "--project",
    type=str,
    help="the project where the function will be deployed",
    required=True,
)
parser.add_argument(
    "--invoker", type=str, help="invoker authorisation", action="append"
)
args = parser.parse_known_args()

# Default function deploy params
FUNCTION_PARAMS = {
    "max-instances": 1,
    "memory": "128MB",
    "region": "europe-west1",
}


def deploy_function(args, deploy_params):
    # Compose function deploy command
    deploy_cmd = ["gcloud", "functions", "deploy", "{}".format(args[0].name)]

    # Append command line params
    for arg in vars(args[0]):
        if arg not in ["invoker", "name"]:
            deploy_cmd.append("--{}={}".format(arg, getattr(args[0], arg)))

    for param in args[1]:
        deploy_cmd.append("{}".format(param))

    # Add security level if HTTP trigger
    if "--trigger-http" in args[1]:
        deploy_cmd.append("--security-level=secure-always")

    # Append default params (only if not specified before)
    for key in deploy_params:
        found = False
        for param in deploy_cmd:
            if key in param:
                found = True

        if not found:
            cmd = "--{}".format(key)
            if deploy_params[key]:
                cmd += "={}".format(deploy_params[key])
            deploy_cmd.append(cmd)

    print(deploy_cmd)
    retval = subprocess.run(
        deploy_cmd, shell=False, stderr=subprocess.PIPE, timeout=300  # nosec
    )
    print(retval)
    return retval.returncode


def deploy_invoker_iam(invokers, region):
    invoker_list = []

    for invoker in invokers:
        for user in invoker.split(","):
            invoker_list.append(user)

    invoker = {
        "bindings": [
            {"role": "roles/cloudfunctions.invoker", "members": list(set(invoker_list))}
        ]
    }

    with open("iam_file.json", "w") as iam_file:
        iam_file.write(json.dumps(invoker))

    auth_cmd = [
        "gcloud",
        "functions",
        "set-iam-policy",
        "{}".format(args[0].name),
        "--project={}".format(args[0].project),
        "--region={}".format(region),
        "iam_file.json",
    ]

    print(auth_cmd)
    print(invoker)

    retval = subprocess.run(
        auth_cmd, shell=False, stderr=subprocess.PIPE, timeout=300  # nosec
    )
    print(retval)
    return retval.returncode


def get_function_params(func_parms):
    # Merge function deploy params with the params specified with the source

    function_params = func_parms
    try:
        with open("deploy.json") as deploy_file:
            deploy_config = json.load(deploy_file)

            for k in deploy_config:
                function_params[k] = deploy_config[k]
    except FileNotFoundError:
        print("No deploy.json found")

    return function_params


def get_region(args, function_params):

    if function_params["region"]:
        region = function_params["region"]

    for param in args[1]:
        if "region" in param:
            region = param.partition("=")[2]

    return region


def main():
    function_params = get_function_params(FUNCTION_PARAMS)

    # Deploy function
    retval = deploy_function(args, function_params)
    if retval:
        return retval

    # Create invoker IAM (if specified)
    if args[0].invoker:
        retval = deploy_invoker_iam(args[0].invoker, get_region(args, function_params))
        if retval:
            return retval

    return 0


if __name__ == "__main__":
    exit(main())
