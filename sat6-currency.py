#!/usr/bin/python

import argparse
import json
import requests
import sys
import getpass
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


parser = argparse.ArgumentParser(description="Satellite 6 version of 'spacewalk-report system-currency'")
parser.add_argument("-a", "--advanced", action="store_true", default=False, help="Use this flag if you want to divide security errata by severity. Note: this will reduce performance if this script significantly.")
parser.add_argument("-n", "--server", type=str.lower, required=True, help="Satellite server (defaults to localhost)", default='localhost')
parser.add_argument("-u", "--username", type=str, required=True, help="Username to access Satellite")
parser.add_argument("-p", "--password", type=str, required=False, help="Password to access Satellite. The user will be asked interactively if password is not provided.")
parser.add_argument("-s", "--search", type=str, required=False, help="Search string for host.( like ?search=lifecycle_environment=Test", default=(''))

args = parser.parse_args()

# Satellite specific parameters
url = "https://" + args.server
api = url + "/api/"
katello_api = url + "/katello/api/v2"
post_headers = {'content-type': 'application/json'}
ssl_verify=True

if args.password is None:
    args.password = getpass.getpass()

def get_with_json(location, json_data):
    """
    Performs a GET and passes the data to the url location
    """
    try:
        result = requests.get(location,
                            data=json_data,
                            auth=(args.username, args.password),
                            verify=ssl_verify,
                            headers=post_headers)

    except requests.ConnectionError, e:
        print sys.argv[0] + " Couldn't connect to the API, check connection or url"
        print e
        sys.exit(1)
    return result.json()

def simple_currency():

    # Print headline
    print "system_id,org_name,name,security,bug,enhancement,score,content_view,content_view_ publish_date,lifecycle_environment,subscription_os_release,os_release,arch,subscription_status,comment"

    # Get all hosts (alter if you have more than 10000 hosts)
    hosts = get_with_json(api + "hosts" + args.search, json.dumps({"per_page": "10000"}))["results"]

    # Multiply factors
    factor_sec = 8
    factor_bug = 2
    factor_enh = 1

    for host in hosts:
        # Check if host is registered with subscription-manager (unregistered hosts lack these values and are skipped)
        if "content_facet_attributes" in host and host["content_facet_attributes"]["errata_counts"]:

            # Get each number of different kinds of erratas
            errata_count_sec = host["content_facet_attributes"]["errata_counts"]["security"]
            errata_count_bug = host["content_facet_attributes"]["errata_counts"]["bugfix"]
            errata_count_enh = host["content_facet_attributes"]["errata_counts"]["enhancement"]
            content_view_name = host["content_facet_attributes"]["content_view"]["name"]
            content_view_id = host["content_facet_attributes"]["content_view"]["id"]
            lifecycle_environment = host["content_facet_attributes"]["lifecycle_environment"]["name"]
            lifecycle_environment_id = host["content_facet_attributes"]["lifecycle_environment"]["id"]
            subscription_os_release= host["subscription_facet_attributes"]["release_version"]
            arch = host["architecture_name"]
            subscription_status = host["subscription_status"]
            os_release = host["operatingsystem_name"]

            content_view = get_with_json(katello_api + "/content_views/" + str(content_view_id) + "/content_view_versions?environment_id=" + str(lifecycle_environment_id), json.dumps({"per_page": "10000"}))["results"]

            cv_date = content_view[0]["created_at"]
            if errata_count_sec is None or errata_count_bug is None or errata_count_enh is None:
                score = 0
            else:
            # Calculate weighted score
                score = errata_count_sec * factor_sec + errata_count_bug * factor_bug + errata_count_enh * factor_enh

            # Print result
            print str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + "," + str(errata_count_sec) + "," + str(errata_count_bug) + "," + str(errata_count_enh) + "," + str(score) + "," + str(content_view_name) + "," + str(cv_date) + "," + str(lifecycle_environment) + "," + str(subscription_os_release) + "," + str(os_release) + "," + str(arch) + "," + str(subscription_status) + "," + str(host["comment"])

def advanced_currency():

    # Print headline
    print "system_id,org_name,name,critical,important,moderate,low,bug,enhancement,score,content_view,content_view_ publish_date,lifecycle_environment,subscription_os_release,os_release,arch,subscription_status,comment"

    # Get all hosts (if you have more than 10000 hosts, this method will take too long itme)
    hosts = get_with_json(api + "hosts" + args.search, json.dumps({"per_page": "10000"}))["results"]

    # Multiply factors according to "spacewalk-report system-currency"
    factor_cri = 32
    factor_imp = 16
    factor_mod = 8
    factor_low = 4
    factor_bug = 2
    factor_enh = 1

    for host in hosts:

        # Get all errata for each host
        erratas = get_with_json(api + "hosts/" + str(host["id"]) + "/errata", json.dumps({"per_page": "10000"}))

        # Check if host is registered with subscription-manager (unregistered hosts lack these values and are skipped)
        if "results" in erratas:

            errata_count_cri = 0
            errata_count_imp = 0
            errata_count_mod = 0
            errata_count_low = 0
            errata_count_enh = 0
            errata_count_bug = 0

            # Check if host have any errrata at all
            if "total" in erratas:
                content_view_name = host["content_facet_attributes"]["content_view"]["name"]
                content_view_id = host["content_facet_attributes"]["content_view"]["id"]
                lifecycle_environment = host["content_facet_attributes"]["lifecycle_environment"]["name"]
                lifecycle_environment_id = host["content_facet_attributes"]["lifecycle_environment"]["id"]
                subscription_os_release= host["subscription_facet_attributes"]["release_version"]
                arch = host["architecture_name"]
                subscription_status = host["subscription_status"]
                os_release = host["operatingsystem_name"]

                content_view = get_with_json(katello_api + "/content_views/" + str(content_view_id) + "/content_view_versions?environment_id=" + str(lifecycle_environment_id), json.dumps({"per_page": "10000"}))["results"]

                cv_date = content_view[0]["created_at"]

                # Go through each errata
                for errata in erratas["results"]:

                    # If it is a security errata, check the severity
                    if errata["type"] == "security":
                        if errata["severity"] == "Critical": errata_count_cri += 1
                        if errata["severity"] == "Important": errata_count_imp += 1
                        if errata["severity"] == "Moderate": errata_count_mod += 1
                        if errata["severity"] == "Low": errata_count_low += 1

                    if errata["type"] == "enhancement": errata_count_enh += 1
                    if errata["type"] == "bugfix": errata_count_bug += 1

            # Calculate weighted score
            score = factor_cri * errata_count_cri + factor_imp * errata_count_imp + factor_mod * errata_count_mod + factor_low * errata_count_low + factor_bug * errata_count_bug + factor_enh * errata_count_enh

            # Print result
            print str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + "," + str(errata_count_cri) + "," + str(errata_count_imp) + "," + str(errata_count_mod) + "," + str(errata_count_low) + "," + str(errata_count_bug) + "," + str(errata_count_enh) + "," + str(score) + "," + str(content_view_name) + "," + str(cv_date) + "," + str(lifecycle_environment) + "," + str(subscription_os_release) + "," + str(os_release) + "," + str(arch) + "," + str(subscription_status) + "," + str(host["comment"])


if __name__ == "__main__":

    if args.advanced:
        advanced_currency()
    else:
        simple_currency()
