import base64
import re
import subprocess
import urllib.parse

import requests
from requests.structures import CaseInsensitiveDict

from django.conf import settings

pw = urllib.parse.quote_plus(settings.ODOO_CREDS["pw"])
usr = urllib.parse.quote_plus(settings.ODOO_CREDS["usr"])
url = settings.ODOO_CREDS["url"]


def retrieve_odoo_invoice(invoice_odoo_id, uuid):
    res = requests.get(url + "/web/login")
    csrf_token = re.findall(r":\ \"(.*\,)", str(res.content))[0].split(",")[0].replace('"', "")

    headers = CaseInsensitiveDict()
    headers[
        "User-Agent"
    ] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0"
    headers[
        "Accept"
    ] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    headers["Accept-Language"] = "en-US,en;q=0.5"
    headers["Accept-Encoding"] = "gzip, deflate, br"
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers["Origin"] = url
    headers["DNT"] = "1"
    headers["Connection"] = "keep-alive"
    headers["Referer"] = url + "/web/login"
    headers["Cookie"] = "website_lang=en_US;"
    headers["Upgrade-Insecure-Requests"] = "1"
    headers["Sec-Fetch-Dest"] = "document"
    headers["Sec-Fetch-Mode"] = "navigate"
    headers["Sec-Fetch-Site"] = "same-origin"
    headers["Sec-Fetch-User"] = "?1"
    # print(headers)

    data = f"csrf_token={csrf_token}&login={usr}&password={pw}&redirect="
    print(data)
    resp = requests.post(url + "/web/login", headers=headers, data=data)
    print(resp.status_code)
    print(resp.content)
    print(resp.headers)
    # session_id = resp.headers["Set-Cookie"].split(";")[0].split("=")[1]
    session_id = "0f94267ea7912c23e964bf528dc46326d0fd7707"
    print(session_id)

    # curl 'https://staging.amtech.co.nz/report/pdf/account.report_invoice/357049' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Connection: keep-alive' -H 'Cookie: session_id=783f19a4cb1a12c69966b614441a0b5c2bae704e; _BEAMER_USER_ID_CkAnkUkX19260=51215f67-20d9-4ebc-8db1-aa38450f0efc; _BEAMER_FIRST_VISIT_CkAnkUkX19260=2021-12-20T23:07:55.932Z; _BEAMER_DATE_CkAnkUkX19260=2021-12-12T19:37:32.000Z; website_lang=en_US; planner_website_last_page=Welcome0' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'TE: trailers' -o test.pdf"
    command = "curl 'https://staging.amtech.co.nz/report/pdf/account.report_invoice/{invoice_odoo_id}' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0' \
		-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'\
		-H 'Accept-Language: en-US,en;q=0.5' \
		-H 'Accept-Encoding: gzip, deflate, br' \
		-H 'Connection: keep-alive' \
		-H 'Cookie: session_id={session_id}; website_lang=en_US; planner_website_last_page=Welcome0' \
		-H 'Upgrade-Insecure-Requests: 1' \
		-H 'Sec-Fetch-Dest: document' \
		-H 'Sec-Fetch-Mode: navigate' \
		-H 'Sec-Fetch-Site: none' \
		-H 'Sec-Fetch-User: ?1' \
		-H 'TE: trailers' \
		-o test.pdf".format(
        invoice_odoo_id=invoice_odoo_id, session_id=session_id
    )
    # command = f"curl -o {settings.MEDIA_DOCUMENT_ROOT}{uuid} '{url}/report/pdf/account.report_invoice/{invoice_odoo_id}' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Connection: keep-alive' -H 'Cookie: session_id={session_id}; website_lang=en_US; planner_website_last_page=Welcome0; fileToken=1646693220079' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Cache-Control: max-age=0'"
    print(command)
    subprocess.run(
        command,
        shell=True,
    )


def retrieve_invoice_from_cache(client, invoice_id, invoice_uuid):
    ba64 = client.search_read(
        "ir.attachment",
        [
            ("res_model", "=", "account.invoice"),
            ("res_id", "=", invoice_id),
        ],
        ["datas", "name"],
    )
    if len(ba64) > 0:
        data_ba64 = ba64[0]["datas"]
        data = base64.b64decode(data_ba64)
        f = open(settings.MEDIA_DOCUMENT_ROOT + invoice_uuid, "wb")
        f.write(data)
        f.close()

        return True
    else:
        return False
