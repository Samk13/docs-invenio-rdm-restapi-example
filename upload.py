import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
# Create via https://127.0.0.1:5000/account/settings/applications/tokens/new/
COMMUNITY_ID = os.environ.get("COMMUNITY_ID")
api = os.environ.get("API_URL")
token = os.environ.get("API_TOKEN")

# Define a list of records you want to upload:
# ('<record metadata json>.json', ['<datafile1>', '<datafile2>'])
records = [
    (
        "record.json",
        [
            "1911.00295.pdf",
        ],
    )
]


#
# HTTP Headers used during requests
#
h = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}
fh = {
    "Accept": "application/json",
    "Content-Type": "application/octet-stream",
    "Authorization": f"Bearer {token}",
}

#
# Add community request body
#
add_comm_body = {
    "receiver": {"community": COMMUNITY_ID},
    "type": "community-submission",
}

#
# Upload and publish all records.
#
for datafile, files in records:
    # Load the record metadata JSON file.
    with open(datafile, encoding="utf-8") as fp:
        data = json.load(fp)

    # Create the record
    # note: "verify=False" is so that we can connect to 127.0.0.1 with a
    # self-signed certificate. You should not do this in production.
    r = requests.post(
        f"{api}/api/records", data=json.dumps(data), headers=h, verify=False, timeout=60
    )
    assert r.status_code == 201, f"Failed to create record (code: {r.status_code})"
    links = r.json()["links"]
    rec_id = r.json()["id"]

    # Upload files
    for f in files:
        # Initiate the file
        data = json.dumps([{"key": f}])
        r = requests.post(
            links["files"], data=data, headers=h, verify=False, timeout=60
        )
        assert (
            r.status_code == 201
        ), f"Failed to create file {f} (code: {r.status_code})"
        file_links = r.json()["entries"][0]["links"]

        # Upload file content by streaming the data
        with open(f, "rb") as fp:
            r = requests.put(
                file_links["content"], data=fp, headers=fh, verify=False, timeout=60
            )
        assert (
            r.status_code == 200
        ), f"Failed to upload file contet {f} (code: {r.status_code})"

        # Commit the file.
        r = requests.post(file_links["commit"], headers=h, verify=False, timeout=60)
        assert (
            r.status_code == 200
        ), f"Failed to commit file {f} (code: {r.status_code})"

    # Publish the record directlly will not work unless you submit to a community
    # r = requests.post(links["publish"], headers=h, verify=False)
    # assert r.status_code == 202, f"Failed to publish record (code: {r.status_code})"

    # Select a community for the draft
    r = requests.put(
        f"{api}/api/records/{rec_id}/draft/review",
        data=json.dumps(add_comm_body),
        headers=h,
        verify=False,
        timeout=60,
    )
    assert (
        r.status_code == 200 or 201
    ), f"Failed to submit draft to community (code: {r.status_code})"

    # Add draft to community
    submit_for_review_body = {
        "payload": {"content": "Thank you in advance for the review!", "format": "html"}
    }
    # Submit draft to community for review
    r = requests.post(
        f"{api}/api/records/{rec_id}/draft/actions/submit-review",
        data=json.dumps(submit_for_review_body),
        headers=h,
        verify=False,
        timeout=60,
    )
    assert (
        r.status_code == 200 or 201
    ), f"Failed to submit draf to community (code: {r.status_code})"

    request_id = r.json()["id"]
    # Accept draft to community
    accept_draft_body = {"payload": {"content": "You are in!", "format": "html"}}

    # Accept draft to community
    r = requests.post(
        f"{api}/api/requests/{request_id}/actions/accept",
        data=json.dumps(accept_draft_body),
        headers=h,
        verify=False,
        timeout=60,
    )
    assert (
        r.status_code == 200 or 201
    ), f"Failed to publish draf to community (code: {r.status_code})"
